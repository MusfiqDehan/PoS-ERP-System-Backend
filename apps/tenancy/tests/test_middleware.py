"""Middleware routing tests for public vs tenant URLconfs."""

import importlib

import pytest
from django.test import override_settings
from django.urls import resolve
from rest_framework.test import APIClient

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
