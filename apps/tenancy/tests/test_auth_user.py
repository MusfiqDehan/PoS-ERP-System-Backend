"""Tests for auth serialization and login guards."""

import pytest
from django.utils import timezone

from apps.tenancy.models import User
from apps.tenancy.services import AuthService, PlatformPermissionService


@pytest.mark.django_db
def test_auth_serialize_user_no_django_flags(public_schema):
    user = User.objects.create_superadmin(email="admin@test.com", password="TestPass1!")
    payload = AuthService.serialize_user(user)
    assert "is_staff" not in payload
    assert "is_superuser" not in payload
    assert "superadmin" in payload["platform_roles"]


@pytest.mark.django_db
def test_platform_is_superadmin_via_role(public_schema):
    user = User.objects.create_user(email="plain@test.com", password="TestPass1!")
    assert PlatformPermissionService.is_superadmin(user) is False

    admin = User.objects.create_superadmin(
        email="admin@test.com", password="TestPass1!"
    )
    assert PlatformPermissionService.is_superadmin(admin) is True


@pytest.mark.django_db
def test_inactive_user_cannot_login(tenant, tenant_domain, tenant_user):
    from django_tenants.utils import schema_context

    with schema_context(tenant.schema_name):
        tenant_user.is_active = False
        tenant_user.save(update_fields=["is_active"])
    with pytest.raises(PermissionError, match="inactive"):
        AuthService.login(
            email="user@test.com",
            password="TestPass1!",
            domain="test-tenant.localhost",
        )


@pytest.mark.django_db
def test_deleted_user_cannot_login(tenant, tenant_domain, tenant_user):
    from django_tenants.utils import schema_context

    with schema_context(tenant.schema_name):
        tenant_user.is_deleted = True
        tenant_user.deleted_at = timezone.now()
        tenant_user.save(update_fields=["is_deleted", "deleted_at"])
    with pytest.raises(ValueError, match="Invalid credentials"):
        AuthService.login(
            email="user@test.com",
            password="TestPass1!",
            domain="test-tenant.localhost",
        )
