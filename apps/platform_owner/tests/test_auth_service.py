"""Tests for PlatformAuthService."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken

from apps.platform_owner.services.auth import PlatformAuthService

User = get_user_model()


@pytest.mark.django_db
def test_platform_login_token_has_platform_user_claim(public_schema, platform_superadmin):
    tokens = PlatformAuthService.login(
        email="platform@test.com",
        password="TestPass1!",
    )
    access = AccessToken(tokens.access)
    assert access["platform_user"] is True
    assert "tenant_schema" not in access


@pytest.mark.django_db
def test_platform_login_rejects_tenant_user(public_schema, tenant_user):
    with pytest.raises(ValueError):
        PlatformAuthService.login(email="user@test.com", password="TestPass1!")


@pytest.mark.django_db
def test_platform_login_rejects_user_without_role(public_schema):
    user = User.objects.create_user(
        email="norole@test.com",
        password="TestPass1!",
        tenant=None,
        email_verified=True,
    )
    user.password_set_at = user.created_at
    user.save(update_fields=["password_set_at"])
    with pytest.raises(PermissionError):
        PlatformAuthService.login(email="norole@test.com", password="TestPass1!")


@pytest.mark.django_db
def test_platform_login_rejects_pending_invite_stub(public_schema):
    user = User.objects.create(email="pending@test.com", tenant=None)
    user.set_unusable_password()
    user.save()
    with pytest.raises(ValueError):
        PlatformAuthService.login(email="pending@test.com", password="anything")
