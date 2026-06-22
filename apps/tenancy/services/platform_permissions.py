from __future__ import annotations

from apps.tenancy.constants import PLATFORM_MODULES
from apps.tenancy.models import (
    PERMISSION_HIERARCHY,
    PlatformRolePermission,
    PlatformUserRole,
)
from shared.cache.helpers import (
    PLATFORM_PERMISSION_TTL,
    get_cached_value,
    platform_permission_map_key,
)


class PlatformPermissionService:
    @staticmethod
    def is_superadmin(user) -> bool:
        if not (user and user.is_authenticated):
            return False
        return PlatformUserRole.objects.filter(
            user=user, role__slug="superadmin"
        ).exists()

    @staticmethod
    def _compute_permission_map(user) -> dict[str, str]:
        role_ids = list(
            PlatformUserRole.objects.filter(user=user).values_list("role_id", flat=True)
        )
        if not role_ids:
            return {}
        aggregate: dict[str, str] = {}
        for module_key, level in PlatformRolePermission.objects.filter(
            role_id__in=role_ids
        ).values_list("module_key", "permission_level"):
            current = aggregate.get(module_key)
            if current is None or PERMISSION_HIERARCHY.get(
                level, 0
            ) > PERMISSION_HIERARCHY.get(current, 0):
                aggregate[module_key] = level
        return aggregate

    @classmethod
    def get_permission_map(cls, user) -> dict[str, str]:
        if not (user and user.is_authenticated):
            return {}
        if cls.is_superadmin(user):
            return {module: "full" for module in PLATFORM_MODULES}
        return get_cached_value(
            platform_permission_map_key(user.id),
            PLATFORM_PERMISSION_TTL,
            lambda: cls._compute_permission_map(user),
        )

    @classmethod
    def get_permission_level(cls, user, module_key: str) -> str:
        if not (user and user.is_authenticated):
            return "none"
        if cls.is_superadmin(user):
            return "full"
        return cls.get_permission_map(user).get(module_key, "none")

    @classmethod
    def user_can(cls, user, module_key: str, required_level: str = "view") -> bool:
        actual = cls.get_permission_level(user, module_key)
        return PERMISSION_HIERARCHY.get(actual, 0) >= PERMISSION_HIERARCHY.get(
            required_level, 0
        )
