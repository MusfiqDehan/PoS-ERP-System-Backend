"""Middleware routing tests for public vs tenant URLconfs."""

import importlib

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import override_settings
from django.urls import resolve
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

User = get_user_model()
TEST_MIDDLEWARE = importlib.import_module("config.settings.test").MIDDLEWARE


@pytest.mark.django_db
@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
def test_tenant_login_ignores_empty_bearer_header(tenant, tenant_domain, tenant_user):
    client = APIClient()
    response = client.post(
        "/api/v1/tenancy/auth/login/",
        {
            "email": "user@test.com",
            "password": "WrongPass1!",
            "domain": "test-tenant.localhost",
        },
        format="json",
        HTTP_HOST="test-tenant.localhost",
        HTTP_AUTHORIZATION="Bearer ",
    )
    assert response.status_code == 401
    assert response.data["error_code"] == "INVALID_CREDENTIALS"
    assert response.data["message"] == "Invalid credentials."


@pytest.mark.django_db
@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
def test_tenant_host_login_uses_public_urlconf(tenant, tenant_domain, tenant_user):
    client = APIClient()
    response = client.post(
        "/api/v1/tenancy/auth/login/",
        {
            "email": "user@test.com",
            "password": "TestPass1!",
            "domain": "test-tenant.localhost",
        },
        format="json",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 200
    assert response.data["data"]["tenant"]["schema_name"] == "test_tenant"


@pytest.mark.django_db
@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
def test_tenant_host_password_change_stays_on_tenant_urlconf(
    tenant, tenant_domain, tenant_user
):
    client = APIClient()
    login = client.post(
        "/api/v1/tenancy/auth/login/",
        {
            "email": "user@test.com",
            "password": "TestPass1!",
            "domain": "test-tenant.localhost",
        },
        format="json",
        HTTP_HOST="test-tenant.localhost",
    )
    access = login.data["data"]["access"]
    response = client.post(
        "/api/v1/tenancy/password/change/",
        {
            "current_password": "TestPass1!",
            "new_password": "NewPass2!",
        },
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {access}",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 200
    match = resolve("/api/v1/tenancy/password/change/")
    assert match.url_name == "password-change"


@pytest.mark.django_db
@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
def test_platform_owner_path_uses_public_urlconf_on_tenant_host(
    tenant, tenant_domain, platform_superadmin
):
    client = APIClient()
    response = client.post(
        "/api/v1/platform-owner/auth/login/",
        {"email": "platform@test.com", "password": "TestPass1!"},
        format="json",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 200
    assert response.data["data"]["access"]


@pytest.mark.django_db
@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
def test_tenant_me_rejects_platform_jwt(tenant, tenant_domain, platform_superadmin):
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


@pytest.mark.django_db
@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
def test_jwt_tenant_schema_routes_hostless_client(tenant, tenant_domain, tenant_user):
    client = APIClient()
    login = client.post(
        "/api/v1/tenancy/auth/login/",
        {
            "email": "user@test.com",
            "password": "TestPass1!",
            "domain": "test-tenant.localhost",
        },
        format="json",
        HTTP_HOST="localhost",
    )
    assert login.status_code == 200
    access = login.data["data"]["access"]
    token = AccessToken(access)
    assert token["tenant_schema"] == "test_tenant"

    me = client.get(
        "/api/v1/tenancy/me/",
        HTTP_AUTHORIZATION=f"Bearer {access}",
        HTTP_HOST="localhost",
    )
    assert me.status_code == 200
    assert me.data["data"]["email"] == "user@test.com"


@pytest.mark.django_db
@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
def test_x_tenant_subdomain_header_resolves_tenant(tenant, tenant_domain, tenant_user):
    from django_tenants.utils import schema_context

    with schema_context(tenant.schema_name):
        refresh = RefreshToken.for_user(tenant_user)
        refresh["tenant_schema"] = tenant.schema_name
        access = str(refresh.access_token)

    client = APIClient()
    response = client.get(
        "/api/v1/tenancy/me/",
        HTTP_AUTHORIZATION=f"Bearer {access}",
        HTTP_HOST="localhost",
        HTTP_X_TENANT_SUBDOMAIN="test-tenant",
    )
    assert response.status_code == 200
    assert response.data["data"]["email"] == "user@test.com"
    assert connection.schema_name == tenant.schema_name


@pytest.fixture
def platform_superadmin(public_schema):
    return User.objects.create_superadmin(
        email="platform@test.com",
        password="TestPass1!",
    )
