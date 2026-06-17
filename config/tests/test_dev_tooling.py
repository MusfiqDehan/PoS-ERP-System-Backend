"""Integration tests for drf-spectacular, debug-toolbar, and silk wiring."""

from __future__ import annotations

import importlib
import json

import pytest
from django.test import Client, override_settings
from django.urls import clear_url_caches, resolve


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="config.public_urls")
def test_openapi_schema_endpoint_returns_document():
    client = Client()
    response = client.get("/api/v1/schema/", {"format": "json"})
    assert response.status_code == 200
    payload = json.loads(response.content.decode())
    assert "openapi" in payload


@pytest.mark.django_db
def test_openapi_schema_includes_public_tenancy_routes():
    client = Client()
    response = client.get("/api/v1/schema/", {"format": "json"})
    assert response.status_code == 200
    paths = json.loads(response.content.decode()).get("paths", {})
    for route in (
        "/api/v1/tenancy/register/",
        "/api/v1/tenancy/auth/login/",
        "/api/v1/tenancy/admin/tenants/",
    ):
        assert route in paths, f"missing public tenancy route: {route}"
    register_post = paths["/api/v1/tenancy/register/"]["post"]
    assert register_post.get("requestBody") is not None


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="config.public_urls")
def test_swagger_ui_endpoint_returns_ok():
    client = Client()
    response = client.get("/api/v1/docs/")
    assert response.status_code == 200


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="config.public_urls")
def test_redoc_endpoint_returns_ok():
    client = Client()
    response = client.get("/api/v1/redoc/")
    assert response.status_code == 200


def test_local_settings_include_dev_tooling_apps_and_middleware():
    local = importlib.import_module("config.settings.local")
    assert "debug_toolbar" in local.INSTALLED_APPS
    assert "silk" in local.INSTALLED_APPS
    middleware = local.MIDDLEWARE
    assert "debug_toolbar.middleware.DebugToolbarMiddleware" in middleware
    assert "silk.middleware.SilkyMiddleware" in middleware
    tenant_idx = middleware.index(
        "apps.tenancy.middleware.MobileAwareTenantMainMiddleware"
    )
    toolbar_idx = middleware.index("debug_toolbar.middleware.DebugToolbarMiddleware")
    silk_idx = middleware.index("silk.middleware.SilkyMiddleware")
    cors_idx = middleware.index("corsheaders.middleware.CorsMiddleware")
    assert tenant_idx < toolbar_idx < silk_idx < cors_idx


def test_local_settings_define_internal_ips_and_silk_auth_disabled():
    local = importlib.import_module("config.settings.local")
    assert "127.0.0.1" in local.INTERNAL_IPS
    assert local.SILKY_AUTHENTICATION is False
    assert local.SILKY_AUTHORISATION is False
    assert "debug_toolbar.panels.profiling.ProfilingPanel" in local.DEBUG_TOOLBAR_CONFIG[
        "DISABLE_PANELS"
    ]


def test_production_settings_exclude_dev_tooling():
    production = importlib.import_module("config.settings.production")
    assert "debug_toolbar" not in production.INSTALLED_APPS
    assert "silk" not in production.INSTALLED_APPS
    assert not any(
        "debug_toolbar" in middleware for middleware in production.MIDDLEWARE
    )
    assert not any("silk" in middleware for middleware in production.MIDDLEWARE)


def test_test_settings_exclude_dev_tooling():
    test_settings = importlib.import_module("config.settings.test")
    assert "debug_toolbar" not in test_settings.INSTALLED_APPS
    assert "silk" not in test_settings.INSTALLED_APPS


def _reload_public_urls():
    import config.public_urls as public_urls

    importlib.reload(public_urls)
    clear_url_caches()


@override_settings(
    DEBUG=True,
    ROOT_URLCONF="config.public_urls",
    INSTALLED_APPS=importlib.import_module("config.settings.local").INSTALLED_APPS,
)
def test_debug_toolbar_url_pattern_registered_when_debug_enabled():
    _reload_public_urls()
    match = resolve("/__debug__/render_panel/")
    assert match.url_name == "render_panel"
    assert match.namespace == "djdt"


@override_settings(DEBUG=True, ROOT_URLCONF="config.urls")
def test_debug_toolbar_url_pattern_registered_on_tenant_urlconf():
    import config.urls as tenant_urls

    importlib.reload(tenant_urls)
    clear_url_caches()
    match = resolve("/__debug__/render_panel/")
    assert match.namespace == "djdt"


@override_settings(
    DEBUG=True,
    ROOT_URLCONF="config.public_urls",
    INSTALLED_APPS=importlib.import_module("config.settings.local").INSTALLED_APPS,
)
def test_silk_url_pattern_registered_when_debug_enabled():
    _reload_public_urls()
    match = resolve("/silk/")
    assert match.namespace == "silk"


@pytest.mark.django_db
@override_settings(
    ROOT_URLCONF="config.urls",
    INSTALLED_APPS=importlib.import_module("config.settings.local").INSTALLED_APPS,
    MIDDLEWARE=[
        middleware
        for middleware in importlib.import_module("config.settings.local").MIDDLEWARE
        if "silk" not in middleware
    ],
)
def test_tenant_health_works_with_local_dev_middleware():
    client = Client()
    response = client.get("/api/v1/health/tenant/")
    assert response.status_code == 200
    assert response.json()["ok"] is True
