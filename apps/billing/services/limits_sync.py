"""Compute effective tenant limits and features from active subscriptions."""

from __future__ import annotations

from dataclasses import dataclass, field

from django_tenants.utils import get_public_schema_name, schema_context

from apps.billing.models import (
    TenantProductSubscription,
)

ACTIVE_STATUSES = {
    TenantProductSubscription.STATUS_TRIAL,
    TenantProductSubscription.STATUS_ACTIVE,
    TenantProductSubscription.STATUS_PAST_DUE,
}


@dataclass
class EffectiveLimits:
    max_branches: int = 0
    max_users: int = 0
    max_custom_roles: int = 0
    max_admins: int = 0
    max_staff: int = 0
    per_role_limits: dict[str, int] = field(default_factory=dict)
    feature_keys: set[str] = field(default_factory=set)


def _max_or_unlimited(current: int, new: int) -> int:
    if new == 0 or current == 0:
        return max(current, new)
    return max(current, new)


def get_active_subscriptions(tenant) -> list[TenantProductSubscription]:
    if tenant is None:
        return []
    with schema_context(get_public_schema_name()):
        return list(
            TenantProductSubscription.objects.filter(
                tenant=tenant,
                status__in=ACTIVE_STATUSES,
            )
            .select_related("package", "software_product")
            .prefetch_related(
                "package__package_features__feature",
                "package__role_limits",
            )
        )


def compute_effective_limits(tenant) -> EffectiveLimits:
    result = EffectiveLimits()
    for sub in get_active_subscriptions(tenant):
        pkg = sub.package
        result.max_branches = _max_or_unlimited(result.max_branches, pkg.max_branches)
        result.max_users = _max_or_unlimited(result.max_users, pkg.max_users)
        result.max_custom_roles = _max_or_unlimited(
            result.max_custom_roles, pkg.max_custom_roles
        )
        result.max_admins = _max_or_unlimited(result.max_admins, pkg.max_admins)
        result.max_staff = _max_or_unlimited(result.max_staff, pkg.max_staff)
        for pf in pkg.package_features.all():
            result.feature_keys.add(pf.feature.key)
        for rl in pkg.role_limits.all():
            current = result.per_role_limits.get(rl.role_slug, 0)
            result.per_role_limits[rl.role_slug] = _max_or_unlimited(
                current, rl.max_users
            )
    return result


def sync_tenant_denormalized_limits(tenant) -> list[str]:
    """Copy effective limits onto Tenant row for fast reads."""
    if tenant is None:
        return []
    limits = compute_effective_limits(tenant)
    updated: list[str] = []
    mapping = {
        "max_branches": limits.max_branches,
        "max_users": limits.max_users,
    }
    for attr, value in mapping.items():
        if getattr(tenant, attr, None) != value:
            setattr(tenant, attr, value)
            updated.append(attr)
    if updated:
        tenant.save(update_fields=[*updated, "updated_at"])
    return updated


def get_effective_feature_keys(tenant) -> set[str]:
    limits = compute_effective_limits(tenant)
    return set(limits.feature_keys)


def get_per_role_limit(tenant, role_slug: str) -> int:
    limits = compute_effective_limits(tenant)
    return limits.per_role_limits.get(role_slug, 0)
