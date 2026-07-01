"""DRF permission classes for tenant-scoped RBAC."""

from rest_framework.permissions import BasePermission

from apps.access.models import UserRole
from apps.access.services.permissions import get_user_permission_level, user_can
from shared.tenancy.helpers import is_tenant_admin_user
from apps.tenancy.models import PERMISSION_HIERARCHY

TENANCY_MANAGE_BRANDING = "tenancy.manage_branding"


class CanViewTenantUsers(BasePermission):
    """Tenant admins, permissions viewers, and branch managers may list users."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if is_tenant_admin_user(user):
            return True
        level = get_user_permission_level(user, "permissions")
        if PERMISSION_HIERARCHY.get(level, 0) >= PERMISSION_HIERARCHY.get("view", 0):
            return True
        return UserRole.objects.filter(
            user_id=user.id, role__slug="branch_manager"
        ).exists()


class CanManageEmployeeInvitations(BasePermission):
    """Tenant role admins and branch managers may manage employee invitations."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if IsRoleAdmin().has_permission(request, view):
            return True
        return UserRole.objects.filter(
            user_id=user.id, role__slug="branch_manager"
        ).exists()


class HasFeaturePermission(BasePermission):
    """Factory permission: requires (feature_key, required_level) on current tenant."""

    feature_key = ""
    required_level = "view"

    @classmethod
    def require(cls, feature_key: str, level: str = "view"):
        if level not in PERMISSION_HIERARCHY:
            raise ValueError(f"Invalid permission level: {level}")

        class _Bound(cls):  # type: ignore[misc,valid-type]
            pass

        _Bound.feature_key = feature_key
        _Bound.required_level = level
        _Bound.__name__ = f"HasFeature_{feature_key}_{level}"
        return _Bound

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return user_can(user, self.feature_key, self.required_level)


class IsRoleAdmin(BasePermission):
    """Allow tenant admins or users with permissions feature edit-level."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if is_tenant_admin_user(user):
            return True
        actual = get_user_permission_level(user, "permissions")
        return PERMISSION_HIERARCHY.get(actual, 0) >= PERMISSION_HIERARCHY.get(
            "edit", 0
        )


class CanManageTenantBranding(BasePermission):
    """Allow tenant admins or users with settings edit-level (tenancy.manage_branding)."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if is_tenant_admin_user(user):
            return True
        actual = get_user_permission_level(user, "settings")
        return PERMISSION_HIERARCHY.get(actual, 0) >= PERMISSION_HIERARCHY.get(
            "edit", 0
        )
