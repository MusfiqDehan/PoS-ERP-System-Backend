"""DRF permission classes for platform RBAC (public schema)."""

from django.db import connection
from django_tenants.utils import get_public_schema_name
from rest_framework.permissions import BasePermission

from apps.tenancy.constants import PLATFORM_MODULES
from apps.tenancy.models import PERMISSION_HIERARCHY
from apps.tenancy.services import PlatformPermissionService


def is_public_schema_request(request) -> bool:
    request_tenant = getattr(request, "tenant", None)
    request_schema = (
        getattr(request_tenant, "schema_name", None) or connection.schema_name
    )
    return request_schema == get_public_schema_name()


class IsPlatformSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return is_public_schema_request(
            request
        ) and PlatformPermissionService.is_superadmin(request.user)


class IsPlatformFeaturePermission(BasePermission):
    module_key = ""
    required_level = "view"

    @classmethod
    def require(cls, module_key: str, level: str = "view"):
        if module_key not in PLATFORM_MODULES:
            raise ValueError(f"Unknown platform module: {module_key}")
        if level not in PERMISSION_HIERARCHY:
            raise ValueError(f"Invalid level: {level}")

        class _Bound(cls):  # type: ignore[misc,valid-type]
            pass

        _Bound.module_key = module_key
        _Bound.required_level = level
        _Bound.__name__ = f"RequirePlatform_{module_key}_{level}"
        return _Bound

    def has_permission(self, request, view):
        if not is_public_schema_request(request):
            return False
        if not (request.user and request.user.is_authenticated):
            return False
        if PlatformPermissionService.is_superadmin(request.user):
            return True
        return PlatformPermissionService.user_can(
            request.user, self.module_key, self.required_level
        )
