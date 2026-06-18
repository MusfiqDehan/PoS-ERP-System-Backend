from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.contrib.auth import get_user_model
from apps.tenancy.models import User as TenancyUser
from django.core.cache import cache
from django.utils import timezone
from django_tenants.utils import schema_context
from rest_framework_simplejwt.tokens import RefreshToken

from apps.tenancy.models import Domain, Tenant
from apps.tenancy.services.registration import full_domain_for_subdomain

User = get_user_model()


@dataclass
class AuthTokens:
    access: str
    refresh: str
    tenant: Tenant
    domain: str
    user: TenancyUser


class AuthService:
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_SECONDS = 15 * 60

    @staticmethod
    def resolve_domain(
        *, domain: str = "", subdomain: str = "", request=None
    ) -> Domain | None:
        domain_name = domain or full_domain_for_subdomain(subdomain, request=request)
        return (
            Domain.objects.filter(domain=domain_name).select_related("tenant").first()
        )

    @staticmethod
    def login(
        *,
        email: str,
        password: str,
        domain: str = "",
        subdomain: str = "",
        request=None,
    ) -> AuthTokens:
        domain_row = AuthService.resolve_domain(
            domain=domain, subdomain=subdomain, request=request
        )
        if domain_row is None:
            raise ValueError("Invalid tenant domain.")

        tenant = domain_row.tenant
        if not tenant.allows_user_entry():
            raise PermissionError("Tenant workspace is suspended.")

        email = email.strip().lower()
        cache_key = f"tenant_auth:{domain_row.domain}:{email}"
        failed_attempts = int(cache.get(cache_key, 0))
        if failed_attempts >= AuthService.MAX_FAILED_ATTEMPTS:
            raise PermissionError("Too many failed attempts. Try later.")

        with schema_context(tenant.schema_name):
            user = User.objects.filter(email__iexact=email).first()
            if user is None or not user.check_password(password):
                cache.set(
                    cache_key, failed_attempts + 1, timeout=AuthService.LOCKOUT_SECONDS
                )
                raise ValueError("Invalid credentials.")
            if not user.is_active or user.is_deleted:
                raise PermissionError("User account is inactive.")

            user.last_login = timezone.now()
            user.save(update_fields=["last_login"])

            refresh = RefreshToken.for_user(user)
            refresh["tenant_schema"] = tenant.schema_name
            refresh["tenant_name"] = tenant.name
            refresh["tenant_domain"] = domain_row.domain
            access = refresh.access_token
            access["tenant_schema"] = tenant.schema_name
            access["tenant_name"] = tenant.name
            access["tenant_domain"] = domain_row.domain

        cache.delete(cache_key)
        return AuthTokens(
            access=str(access),
            refresh=str(refresh),
            tenant=tenant,
            domain=domain_row.domain,
            user=user,
        )

    @staticmethod
    def refresh(refresh_token: str) -> dict[str, str]:
        refresh = RefreshToken(refresh_token)  # type: ignore[arg-type]
        access = refresh.access_token
        for claim in ("tenant_schema", "tenant_name", "tenant_domain"):
            if claim in refresh:
                access[claim] = refresh[claim]
        return {"access": str(access), "refresh": str(refresh)}

    @staticmethod
    def serialize_user(user: TenancyUser) -> dict[str, Any]:
        from apps.tenancy.models import PlatformUserRole

        platform_roles = list(
            PlatformUserRole.objects.filter(user=user).values_list(
                "role__slug", flat=True
            )
        )
        return {
            "id": str(user.id),
            "email": user.email,
            "phone": user.phone,
            "full_name": user.full_name,
            "platform_roles": platform_roles,
            "email_verified": user.email_verified,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        }
