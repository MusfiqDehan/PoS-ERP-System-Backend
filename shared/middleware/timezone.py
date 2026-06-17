"""
TimezoneMiddleware — activates the correct IANA timezone for every request.

Priority chain (highest to lowest):
  1. Tenant.timezone       — per-tenant override (tenant schema)
  2. PlatformSettings.default_timezone — platform global default (public schema)
  3. settings.TIME_ZONE    — code-level fallback (Asia/Dhaka)
"""

from __future__ import annotations

import logging
import zoneinfo

from django.conf import settings
from django.db import connection
from django.utils import timezone
from django_tenants.utils import get_public_schema_name

from shared.cache.helpers import TIMEZONE_TTL, get_cached_value, timezone_key

logger = logging.getLogger(__name__)


class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tz_name = self._resolve_timezone()
        try:
            tz = zoneinfo.ZoneInfo(tz_name)
        except (zoneinfo.ZoneInfoNotFoundError, KeyError):
            logger.warning(
                "TimezoneMiddleware: unknown timezone %r, falling back to %s",
                tz_name,
                settings.TIME_ZONE,
            )
            try:
                tz = zoneinfo.ZoneInfo(settings.TIME_ZONE)
            except (zoneinfo.ZoneInfoNotFoundError, KeyError):
                tz = zoneinfo.ZoneInfo("UTC")

        timezone.activate(tz)
        try:
            response = self.get_response(request)
        finally:
            timezone.deactivate()
        return response

    def _resolve_timezone(self) -> str:
        tenant = getattr(connection, "tenant", None)
        if tenant is None:
            return self._platform_default()

        schema_name = getattr(tenant, "schema_name", None)
        if not schema_name or schema_name == get_public_schema_name():
            return self._platform_default()

        return get_cached_value(
            timezone_key(schema_name),
            TIMEZONE_TTL,
            lambda: self._compute_timezone(tenant),
        )

    def _compute_timezone(self, tenant) -> str:
        tz_name = getattr(tenant, "timezone", None)
        if tz_name:
            return tz_name
        return self._platform_default()

    @staticmethod
    def _platform_default() -> str:
        try:
            from django_tenants.utils import schema_context

            with schema_context(get_public_schema_name()):
                from shared.cache.helpers import get_platform_settings_cached

                settings_row = get_platform_settings_cached()
                if settings_row and settings_row.get("default_timezone"):
                    return settings_row["default_timezone"]
        except Exception:
            pass
        return settings.TIME_ZONE
