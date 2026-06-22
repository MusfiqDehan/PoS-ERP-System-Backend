"""Reusable helpers for enforcing tenant subscription limits.

Limits are derived from active ``TenantProductSubscription`` rows via
``apps.billing.services.limits_sync``. A limit value of ``0`` means unlimited.
"""

from django.db import connection

from apps.billing.services.limits_sync import compute_effective_limits


def get_tenant_limit(limit_attr):
    """Return the configured limit for the active tenant, or 0 (unlimited)."""
    tenant = getattr(connection, "tenant", None)
    if tenant is None:
        return 0

    limits = compute_effective_limits(tenant)
    attr_map = {
        "max_branches": limits.max_branches,
        "max_users": limits.max_users,
        "max_custom_roles": limits.max_custom_roles,
        "max_admins": limits.max_admins,
        "max_staff": limits.max_staff,
    }
    return attr_map.get(limit_attr, getattr(tenant, limit_attr, 0) or 0)


def _limit_exceeded_payload(*, detail, limit_type, limit, current):
    """Standard payload returned when a tenant plan limit is exceeded."""
    return {
        "detail": detail,
        "code": "LIMIT_EXCEEDED",
        "limit_type": limit_type,
        "limit": limit,
        "current": current,
        "upgrade_action": "upgrade_plan",
        "upgrade_path": "/settings",
    }


def total_capacity_exceeded(queryset, limit_attr, *, limit_type):
    """Check tenant-wide capacity for a queryset.

    Returns a standard limit payload dict or ``None``.
    """
    limit = get_tenant_limit(limit_attr)
    if not limit:
        return None

    current = queryset.count()
    if current >= limit:
        return _limit_exceeded_payload(
            detail=(
                "You have reached the maximum number allowed by your current "
                "plan. Please upgrade to add more."
            ),
            limit_type=limit_type,
            limit=limit,
            current=current,
        )
    return None


def branch_capacity_exceeded(queryset, branch_id, limit_attr, *, limit_type=None):
    """Check whether adding one row to ``branch_id`` would exceed the limit.

    ``queryset`` must be filterable by ``branch_id``. Returns a dict describing
    the breach (suitable for a 403 body) or ``None`` when within limits.
    """
    limit = get_tenant_limit(limit_attr)
    if not limit or branch_id is None:
        return None

    current = queryset.filter(branch_id=branch_id).count()
    if current >= limit:
        return _limit_exceeded_payload(
            detail=(
                "You have reached the maximum number allowed by your current "
                "plan for this branch. Please upgrade to add more."
            ),
            limit_type=limit_type or limit_attr,
            limit=limit,
            current=current,
        )
    return None


def user_capacity_exceeded(*, limit_type="users"):
    """Check tenant-wide active user count against max_users."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return total_capacity_exceeded(
        User.objects.filter(is_active=True), "max_users", limit_type=limit_type
    )


def custom_role_capacity_exceeded(*, limit_type="custom_roles"):
    from apps.access.models import Role

    limit = get_tenant_limit("max_custom_roles")
    if not limit:
        return None
    current = Role.objects.filter(is_system=False).count()
    if current >= limit:
        return _limit_exceeded_payload(
            detail="Custom role limit reached for your current plan.",
            limit_type=limit_type,
            limit=limit,
            current=current,
        )
    return None


def role_assignment_capacity_exceeded(role_slug: str):
    from apps.access.models import UserRole

    limits = compute_effective_limits(getattr(connection, "tenant", None))
    if role_slug == "admin":
        limit = limits.max_admins
        current = UserRole.objects.filter(role__slug="admin").count()
        limit_type = "admins"
    elif role_slug in limits.per_role_limits:
        limit = limits.per_role_limits[role_slug]
        current = UserRole.objects.filter(role__slug=role_slug).count()
        limit_type = f"role:{role_slug}"
    elif role_slug in {"manager", "cashier", "branch_manager"}:
        limit = limits.max_staff
        current = UserRole.objects.filter(
            role__slug__in={"manager", "cashier", "branch_manager"}
        ).count()
        limit_type = "staff"
    else:
        return None

    if not limit:
        return None
    if current >= limit:
        return _limit_exceeded_payload(
            detail="Role assignment limit reached for your current plan.",
            limit_type=limit_type,
            limit=limit,
            current=current,
        )
    return None
