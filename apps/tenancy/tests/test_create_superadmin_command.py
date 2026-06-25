"""Tests for create_superadmin management command bootstrap."""

import importlib

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import override_settings
from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework.test import APIClient

from apps.platform_owner.services.auth import PlatformAuthService
from apps.tenancy.models import PlatformUserRole, Tenant

User = get_user_model()
TEST_MIDDLEWARE = importlib.import_module("config.settings.test").MIDDLEWARE

BOOTSTRAP_EMAIL = "bootstrap-superadmin@test.com"
BOOTSTRAP_PASSWORD = "BootstrapPass1!"


@pytest.fixture
def superadmin_env(monkeypatch):
    monkeypatch.setenv("SUPERADMIN_EMAIL", BOOTSTRAP_EMAIL)
    monkeypatch.setenv("SUPERADMIN_PASSWORD", BOOTSTRAP_PASSWORD)
    monkeypatch.setenv("SUPERADMIN_SCHEMA", get_public_schema_name())


@pytest.mark.django_db
def test_create_superadmin_from_env_creates_platform_user(
    public_schema, superadmin_env
):
    call_command("create_superadmin")

    with schema_context(get_public_schema_name()):
        user = User.objects.get(email__iexact=BOOTSTRAP_EMAIL)
        assert user.tenant_id is None
        assert user.password_set_at is not None
        assert PlatformUserRole.objects.filter(
            user=user, role__slug="superadmin"
        ).exists()


@pytest.mark.django_db
def test_create_superadmin_bootstrap_user_can_platform_login(
    public_schema, superadmin_env
):
    call_command("create_superadmin")

    tokens = PlatformAuthService.login(
        email=BOOTSTRAP_EMAIL,
        password=BOOTSTRAP_PASSWORD,
    )
    assert tokens.access
    assert tokens.refresh


@pytest.mark.django_db
@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
def test_create_superadmin_bootstrap_user_can_platform_login_api(
    public_schema, superadmin_env
):
    call_command("create_superadmin")

    client = APIClient()
    response = client.post(
        "/api/v1/platform-owner/auth/login/",
        {"email": BOOTSTRAP_EMAIL, "password": BOOTSTRAP_PASSWORD},
        format="json",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 200
    assert response.data["data"]["access"]


@pytest.mark.django_db
def test_create_superadmin_idempotent_does_not_break_platform_user(
    public_schema, superadmin_env
):
    call_command("create_superadmin")
    call_command("create_superadmin")

    with schema_context(get_public_schema_name()):
        user = User.objects.get(email__iexact=BOOTSTRAP_EMAIL)
        assert user.tenant_id is None

    tokens = PlatformAuthService.login(
        email=BOOTSTRAP_EMAIL,
        password=BOOTSTRAP_PASSWORD,
    )
    assert tokens.access


@pytest.mark.django_db
def test_create_superadmin_ignores_public_tenant_row_for_user_fk(
    public_schema, superadmin_env
):
    Tenant.objects.create(
        schema_name=get_public_schema_name(),
        name="Public Placeholder",
        slug="public-placeholder",
        code="PUBLIC",
        status="active",
    )

    call_command("create_superadmin")

    with schema_context(get_public_schema_name()):
        user = User.objects.get(email__iexact=BOOTSTRAP_EMAIL)
        assert user.tenant_id is None

    tokens = PlatformAuthService.login(
        email=BOOTSTRAP_EMAIL,
        password=BOOTSTRAP_PASSWORD,
    )
    assert tokens.access
