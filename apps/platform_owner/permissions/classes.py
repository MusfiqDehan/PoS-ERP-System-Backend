"""DRF permission classes for platform owner endpoints (public schema)."""

from rest_framework.permissions import BasePermission

from apps.tenancy.models import PlatformUserRole
from apps.tenancy.permissions import is_public_schema_request


def _token_has_tenant_schema(request) -> bool:
    auth = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth.startswith("Bearer "):
        return False
    raw = auth.split(" ", 1)[1].strip()
    if not raw:
        return False
    try:
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken(raw)
    except Exception:
        return False
    return bool(token.get("tenant_schema"))


class IsPlatformUser(BasePermission):
    """Authenticated platform user on the public schema (invite-only team)."""

    def has_permission(self, request, view):
        if not is_public_schema_request(request):
            return False
        user = request.user
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if _token_has_tenant_schema(request):
            return False
        if getattr(user, "tenant_id", None) is not None:
            return False
        if not user.is_active or getattr(user, "is_deleted", False):
            return False
        return PlatformUserRole.objects.filter(user=user).exists()
