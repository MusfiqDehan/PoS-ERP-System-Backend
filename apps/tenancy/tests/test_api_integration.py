"""API integration tests for auth and access flows."""

import importlib

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import override_settings
from django_tenants.utils import schema_context
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.access.models import Role, RolePermission, UserRole

User = get_user_model()
TEST_MIDDLEWARE = importlib.import_module("config.settings.test").MIDDLEWARE


@pytest.fixture
def platform_superadmin(public_schema):
    return User.objects.create_superadmin(
        email="platform@test.com",
        password="TestPass1!",
    )


@pytest.mark.django_db
def test_auth_login_me_refresh_flow(tenant, tenant_domain, tenant_user):
    client = APIClient()
    login_response = client.post(
        "/api/v1/tenancy/auth/login/",
        {
            "email": "user@test.com",
            "password": "TestPass1!",
            "domain": "test-tenant.localhost",
        },
        format="json",
        HTTP_HOST="localhost",
    )
    assert login_response.status_code == 200
    assert login_response.data["success"] is True
    access = login_response.data["data"]["access"]
    refresh = login_response.data["data"]["refresh"]

    token = AccessToken(access)
    assert token["tenant_schema"] == "test_tenant"

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    me_response = client.get(
        "/api/v1/tenancy/me/",
        HTTP_HOST="localhost",
    )
    assert me_response.status_code == 200
    assert me_response.data["data"]["email"] == "user@test.com"

    refresh_client = APIClient()
    refresh_response = refresh_client.post(
        "/api/v1/tenancy/auth/refresh/",
        {"refresh": refresh},
        format="json",
        HTTP_HOST="localhost",
    )
    assert refresh_response.status_code == 200
    assert "access" in refresh_response.data["data"]


@pytest.mark.django_db
def test_unauthenticated_me_returns_401(tenant, tenant_domain):
    client = APIClient()
    response = client.get("/api/v1/tenancy/me/", HTTP_HOST="test-tenant.localhost")
    assert response.status_code == 401
    assert response.data["success"] is False


@pytest.mark.django_db
def test_access_my_permissions(tenant, tenant_domain, tenant_schema, tenant_user):
    with schema_context(tenant.schema_name):
        connection.set_tenant(tenant)
        role = Role.objects.create(name="Permissions Manager", slug="perm_mgr")
        RolePermission.objects.create(
            role=role, feature_key="permissions", permission_level="full"
        )
        UserRole.objects.create(
            user_id=tenant_user.id,
            user_email=tenant_user.email,
            role=role,
        )
        refresh = RefreshToken.for_user(tenant_user)
        refresh["tenant_schema"] = tenant.schema_name
        access = str(refresh.access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    response = client.get("/api/v1/access/me/", HTTP_HOST="localhost")
    assert response.status_code == 200
    assert response.data["success"] is True
    assert response.data["data"]["permissions"]["permissions"] == "full"


@pytest.mark.django_db
def test_access_roles_forbidden_without_permission(tenant, tenant_domain, tenant_user):
    with schema_context(tenant.schema_name):
        refresh = RefreshToken.for_user(tenant_user)
        refresh["tenant_schema"] = tenant.schema_name
        access = str(refresh.access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    response = client.get("/api/v1/access/roles/", HTTP_HOST="localhost")
    assert response.status_code == 403
    assert response.data["success"] is False


@pytest.mark.django_db
def test_tenant_user_cannot_access_platform_owner_me(
    tenant, tenant_domain, tenant_user
):
    from django_tenants.utils import schema_context

    with schema_context(tenant.schema_name):
        refresh = RefreshToken.for_user(tenant_user)
        refresh["tenant_schema"] = tenant.schema_name
        access = str(refresh.access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    response = client.get("/api/v1/platform-owner/me/", HTTP_HOST="localhost")
    assert response.status_code in (401, 403)


@pytest.mark.django_db
@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
def test_platform_superadmin_cannot_access_tenant_me(
    tenant, tenant_domain, platform_superadmin
):
    client = APIClient()
    login = client.post(
        "/api/v1/platform-owner/auth/login/",
        {"email": "platform@test.com", "password": "TestPass1!"},
        format="json",
        HTTP_HOST="localhost",
    )
    access = login.data["data"]["access"]
    response = client.get(
        "/api/v1/tenancy/me/",
        HTTP_AUTHORIZATION=f"Bearer {access}",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code in (401, 403)
