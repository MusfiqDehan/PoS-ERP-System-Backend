from __future__ import annotations

from apps.tenancy.models import Tenant
from shared.cache.helpers import (
    TENANT_FEATURE_TTL,
    get_cached_value,
    invalidate_tenant_features,
    tenant_feature_key,
)


def _load_tenant_enabled_feature_keys(tenant: Tenant) -> set[str]:
    features = tenant.features if isinstance(tenant.features, dict) else {}
    return {key for key, enabled in features.items() if enabled}


def get_tenant_enabled_feature_keys(tenant: Tenant) -> set[str]:
    """Return enabled feature keys for a tenant (cached)."""
    return get_cached_value(
        tenant_feature_key(tenant.id),
        TENANT_FEATURE_TTL,
        lambda: _load_tenant_enabled_feature_keys(tenant),
    )


def tenant_has_feature(tenant, feature_key: str) -> bool:
    """Check whether a tenant currently has access to a given feature."""
    if tenant is None:
        return False
    return feature_key in get_tenant_enabled_feature_keys(tenant)


def set_tenant_features(tenant: Tenant, feature_keys: set[str] | list[str]) -> None:
    """Replace tenant.features with the given enabled keys."""
    tenant.features = {key: True for key in feature_keys}
    tenant.save(update_fields=["features", "updated_at"])
    invalidate_tenant_features(tenant.id)
