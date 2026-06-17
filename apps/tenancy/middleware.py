"""
Tenant resolution middleware for hostless API clients (e.g. mobile apps).

Authenticated requests read tenant_schema from the signed JWT.
Unauthenticated public endpoints may use X-Tenant-Schema or X-Tenant-Subdomain.
"""

from django_tenants.middleware.main import TenantMainMiddleware
from django_tenants.utils import get_public_schema_name

from shared.cache.helpers import DOMAIN_TTL, domain_schema_key, get_cached_value

from apps.tenancy.models import Domain


def _derive_schema_from_subdomain(subdomain: str) -> str:
    return (subdomain or "").strip().lower().replace("-", "_")


class MobileAwareTenantMainMiddleware(TenantMainMiddleware):
    """TenantMainMiddleware that also honours JWT/header tenant hints."""

    def _schema_from_token(self, request):
        auth = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth.startswith("Bearer "):
            return None
        raw = auth.split(" ", 1)[1].strip()
        if not raw:
            return None
        try:
            from rest_framework_simplejwt.tokens import AccessToken

            token = AccessToken(raw)
        except Exception:
            return None
        return token.get("tenant_schema") or None

    def _schema_from_header(self, request):
        schema = (request.META.get("HTTP_X_TENANT_SCHEMA") or "").strip().lower()
        if schema:
            return schema
        subdomain = (request.META.get("HTTP_X_TENANT_SUBDOMAIN") or "").strip().lower()
        if subdomain:
            return _derive_schema_from_subdomain(subdomain)
        return None

    def _hint_schema(self, request):
        return self._schema_from_token(request) or self._schema_from_header(request)

    def _domain_for_schema(self, schema: str) -> str | None:
        return get_cached_value(
            domain_schema_key(schema),
            DOMAIN_TTL,
            lambda: (
                Domain.objects.filter(tenant__schema_name=schema)
                .order_by("-is_primary", "id")
                .values_list("domain", flat=True)
                .first()
            ),
        )

    def hostname_from_request(self, request):
        schema = self._hint_schema(request)
        if schema and schema != get_public_schema_name():
            domain = self._domain_for_schema(schema)
            if domain:
                return domain
        return super().hostname_from_request(request)
