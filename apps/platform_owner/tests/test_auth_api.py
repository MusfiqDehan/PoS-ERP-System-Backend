"""API integration tests for platform owner auth."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

User = get_user_model()


@pytest.mark.django_db
def test_no_register_route(public_schema):
    client = APIClient()
    response = client.post(
        "/api/v1/platform-owner/register/",
        {},
        format="json",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_platform_login_me_flow(public_schema, platform_superadmin):
    client = APIClient()
    login = client.post(
        "/api/v1/platform-owner/auth/login/",
        {"email": "platform@test.com", "password": "TestPass1!"},
        format="json",
        HTTP_HOST="localhost",
    )
    assert login.status_code == 200
    user_data = login.data["data"]["user"]
    assert "is_staff" not in user_data
    assert "is_superuser" not in user_data
    assert "superadmin" in user_data["platform_roles"]

    access = login.data["data"]["access"]
    token = AccessToken(access)
    assert token["platform_user"] is True

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    me = client.get("/api/v1/platform-owner/me/", HTTP_HOST="localhost")
    assert me.status_code == 200
    assert me.data["data"]["email"] == "platform@test.com"

    perms = client.get("/api/v1/platform-owner/me/permissions/", HTTP_HOST="localhost")
    assert perms.status_code == 200
    assert perms.data["data"]["permissions"]["platform.tenants"] == "full"


@pytest.mark.django_db
def test_tenant_token_rejected_on_platform_me(tenant, tenant_domain, tenant_user):
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
def test_platform_permissions_legacy_alias(public_schema, platform_auth_client):
    response = platform_auth_client.get(
        "/api/v1/tenancy/admin/me/platform-permissions/",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 200
    assert "permissions" in response.data["data"]
