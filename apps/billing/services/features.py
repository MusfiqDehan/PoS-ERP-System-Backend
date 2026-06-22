"""Resolve enabled tenant features from subscriptions and platform overrides."""

from __future__ import annotations

from apps.billing.services.limits_sync import get_effective_feature_keys
from apps.tenancy.models import Tenant


def _parse_override_entry(value) -> tuple[bool | None, bool]:
    """Return (enabled, force_enable). enabled None means inherit from package."""
    if isinstance(value, dict):
        enabled = value.get("enabled")
        force_enable = bool(value.get("force_enable"))
        if enabled is None:
            return None, force_enable
        return bool(enabled), force_enable
    if isinstance(value, bool):
        return value, False
    return None, False


def resolve_tenant_feature_keys(tenant: Tenant) -> set[str]:
    subscribed = get_effective_feature_keys(tenant)
    overrides = tenant.features if isinstance(tenant.features, dict) else {}
    result = set(subscribed)

    for key, raw in overrides.items():
        enabled, force_enable = _parse_override_entry(raw)
        if force_enable or enabled is True:
            result.add(key)
        elif enabled is False:
            result.discard(key)

    return result
