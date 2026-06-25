"""Platform settings API tests."""

import pytest
from django.core.cache import cache

from apps.tenancy.models import PlatformSettings
from shared.cache.helpers import get_platform_settings_cached, platform_settings_key


@pytest.mark.django_db
def test_platform_settings_get_and_patch(public_schema, platform_auth_client):
    assert PlatformSettings.objects.count() == 0
    get_resp = platform_auth_client.get(
        "/api/v1/platform-owner/settings/",
        HTTP_HOST="localhost",
    )
    assert get_resp.status_code == 200
    assert PlatformSettings.objects.count() == 1

    patch_resp = platform_auth_client.patch(
        "/api/v1/platform-owner/settings/",
        {"default_timezone": "UTC"},
        format="json",
        HTTP_HOST="localhost",
    )
    assert patch_resp.status_code == 200
    assert patch_resp.data["data"]["default_timezone"] == "UTC"


@pytest.mark.django_db
def test_platform_settings_patch_invalidates_cache(public_schema, platform_auth_client):
    PlatformSettings.objects.create(default_timezone="Asia/Dhaka")
    cache.set(
        platform_settings_key(),
        {"default_timezone": "Asia/Dhaka"},
        timeout=300,
    )
    assert get_platform_settings_cached()["default_timezone"] == "Asia/Dhaka"

    response = platform_auth_client.patch(
        "/api/v1/platform-owner/settings/",
        {"default_timezone": "UTC"},
        format="json",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 200
    assert get_platform_settings_cached()["default_timezone"] == "UTC"
