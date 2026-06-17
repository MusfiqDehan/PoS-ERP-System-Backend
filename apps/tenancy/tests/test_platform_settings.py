"""Tests for PlatformSettings singleton."""

import pytest

from apps.tenancy.models import PlatformSettings


@pytest.mark.django_db
def test_platform_settings_get_solo_creates_row(public_schema):
    assert PlatformSettings.objects.count() == 0
    settings_row = PlatformSettings.get_solo()
    assert settings_row.default_timezone == "Asia/Dhaka"
    assert PlatformSettings.objects.count() == 1


@pytest.mark.django_db
def test_platform_settings_get_solo_returns_existing(public_schema):
    original = PlatformSettings.objects.create(default_timezone="UTC")
    settings_row = PlatformSettings.get_solo()
    assert settings_row.id == original.id
