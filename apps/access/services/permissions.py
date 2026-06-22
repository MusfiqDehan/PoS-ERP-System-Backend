"""Helpers for resolving tenant-scoped permissions."""

from __future__ import annotations

from django.db import connection
from django_tenants.utils import get_public_schema_name

from apps.access.models import RolePermission, UserRole
from apps.tenancy.models import PERMISSION_HIERARCHY
from apps.tenancy.services import tenant_has_feature
from shared.cache.helpers import PERMISSION_TTL, get_cached_value, permission_map_key
from shared.tenancy.helpers import is_tenant_admin_user


def is_in_tenant_schema() -> bool:
    return connection.schema_name != get_public_schema_name()


def get_user_role_ids(user) -> list:
    if not (user and user.is_authenticated):
        return []
    return list(
        UserRole.objects.filter(user_id=user.id).values_list("role_id", flat=True)
    )


def _compute_user_permission_map(user) -> dict[str, str]:
    role_ids = get_user_role_ids(user)
    if not role_ids:
        return {}
    aggregate: dict[str, str] = {}
    for perm in RolePermission.objects.filter(role_id__in=role_ids).values(
        "feature_key", "permission_level"
    ):
        key = perm["feature_key"]
        level = perm["permission_level"]
        current = aggregate.get(key)
        if current is None or PERMISSION_HIERARCHY.get(
            level, 0
        ) > PERMISSION_HIERARCHY.get(current, 0):
            aggregate[key] = level
    return aggregate


def get_user_permission_map(user) -> dict[str, str]:
    if not (user and user.is_authenticated):
        return {}
    if is_tenant_admin_user(user):
        return {}
    return get_cached_value(
        permission_map_key(connection.schema_name, user.id),
        PERMISSION_TTL,
        lambda: _compute_user_permission_map(user),
    )


def get_user_permission_level(user, feature_key: str) -> str:
    if not (user and user.is_authenticated):
        return "none"
    if is_tenant_admin_user(user):
        return "full"
    return get_user_permission_map(user).get(feature_key, "none")


def user_can(user, feature_key: str, required_level: str = "view") -> bool:
    if not is_in_tenant_schema():
        return False
    tenant = _resolve_current_tenant() or getattr(user, "tenant", None)
    if tenant is None:
        return False
    if not tenant_has_feature(tenant, feature_key):
        return False
    actual = get_user_permission_level(user, feature_key)
    return PERMISSION_HIERARCHY.get(actual, 0) >= PERMISSION_HIERARCHY.get(
        required_level, 0
    )


def _resolve_current_tenant():
    from apps.tenancy.models import Tenant

    if not is_in_tenant_schema():
        return None
    tenant = getattr(connection, "tenant", None)
    if tenant is not None:
        return tenant
    return Tenant.objects.filter(schema_name=connection.schema_name).first()
