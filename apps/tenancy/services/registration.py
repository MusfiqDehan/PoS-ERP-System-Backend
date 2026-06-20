from __future__ import annotations

import re
from datetime import timedelta
from urllib.parse import quote

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from django_tenants.utils import get_public_schema_name, schema_context

from apps.tenancy.feature_registry import TENANT_REGISTRY
from apps.tenancy.models import Domain, Invitation, PlatformSettings, Tenant
from apps.tenancy.services.email import EmailService
from apps.tenancy.services.features import set_tenant_features

SUBDOMAIN_RE = re.compile(r"^(?!-)[a-z0-9-]{3,63}(?<!-)$")


def normalize_subdomain(value: str) -> str:
    return (value or "").strip().lower()


def resolve_base_domain(request=None) -> str:
    explicit = getattr(settings, "TENANT_BASE_DOMAIN", "") or ""
    explicit = explicit.strip().lower()
    if explicit:
        return explicit
    if request is None:
        return "localhost"
    host = request.get_host().split(":")[0].strip().lower()
    if host in {"localhost", "127.0.0.1"}:
        return "localhost"
    parts = host.split(".")
    if len(parts) > 2:
        return ".".join(parts[1:])
    return host


def full_domain_for_subdomain(subdomain: str, request=None) -> str:
    base_domain = resolve_base_domain(request)
    subdomain = normalize_subdomain(subdomain)
    if base_domain in {"localhost", "127.0.0.1"}:
        return f"{subdomain}.localhost"
    return f"{subdomain}.{base_domain}"


def derive_schema_name(subdomain: str) -> str:
    return normalize_subdomain(subdomain).replace("-", "_")


def build_frontend_url(
    path_suffix: str, *, subdomain: str = "", domain: str = ""
) -> str:
    path = f"/{path_suffix.lstrip('/')}"
    configured_base = (
        getattr(settings, "TENANT_FRONTEND_BASE_DOMAIN", "").strip().lower()
    )
    if subdomain and configured_base:
        host = (
            f"{subdomain}.localhost"
            if configured_base in {"localhost", "127.0.0.1"}
            else f"{subdomain}.{configured_base}"
        )
        scheme = (
            getattr(settings, "TENANT_FRONTEND_SCHEME", "http").strip().lower()
            or "http"
        )
        port = getattr(settings, "TENANT_FRONTEND_PORT", "").strip()
        netloc = host if not port else f"{host}:{port}"
        return f"{scheme}://{netloc}{path}"
    if domain:
        scheme = (
            getattr(settings, "TENANT_FRONTEND_SCHEME", "http").strip().lower()
            or "http"
        )
        return f"{scheme}://{domain}{path}"
    base = getattr(settings, "PUBLIC_FRONTEND_URL", "") or getattr(
        settings, "FRONTEND_BASE_URL", ""
    )
    if base:
        return f"{base.rstrip('/')}{path}"
    return path


def default_feature_keys() -> list[str]:
    keys: list[str] = []
    for group in TENANT_REGISTRY:
        for item in group.get("children", []):
            keys.append(item["key"])
    return keys


class TenantRegistrationService:
    @staticmethod
    def validate_subdomain(subdomain: str) -> str:
        normalized = normalize_subdomain(subdomain)
        if not SUBDOMAIN_RE.match(normalized):
            raise ValueError(
                "Subdomain must be 3-63 chars, lowercase letters/numbers/hyphens."
            )
        return normalized

    @staticmethod
    def subdomain_available(
        subdomain: str, *, request=None, allow_existing: bool = False
    ) -> bool:
        if allow_existing:
            return True
        domain_value = full_domain_for_subdomain(subdomain, request=request)
        with schema_context(get_public_schema_name()):
            if Domain.objects.filter(domain=domain_value).exists():
                return False
            pending = Invitation.objects.filter(
                token_type__in=[
                    Invitation.TOKEN_TYPE_VERIFICATION,
                    Invitation.TOKEN_TYPE_INVITATION,
                ],
                subdomain=normalize_subdomain(subdomain),
                used_at__isnull=True,
                expires_at__gt=timezone.now(),
            ).exists()
            return not pending

    @staticmethod
    def start_self_registration(
        *,
        subdomain: str,
        company_name: str,
        admin_email: str,
        admin_full_name: str = "",
        contact_phone: str = "",
        plan: str = "free",
        request=None,
    ) -> tuple[str, Invitation, str]:
        subdomain = TenantRegistrationService.validate_subdomain(subdomain)
        if not TenantRegistrationService.subdomain_available(
            subdomain, request=request
        ):
            raise ValueError(
                "This subdomain is already in use or has a pending invitation."
            )

        domain = full_domain_for_subdomain(subdomain, request=request)
        with transaction.atomic():
            raw_token, invitation = Invitation.issue_token(
                token_type=Invitation.TOKEN_TYPE_VERIFICATION,
                email=admin_email.strip().lower(),
                invitee_full_name=admin_full_name,
                subdomain=subdomain,
                company_name=company_name,
                ttl_minutes=120,
                metadata={
                    "domain": domain,
                    "plan": plan or "free",
                    "contact_phone": contact_phone,
                },
            )

        setup_url = build_frontend_url(
            f"/verify-email?token={quote(raw_token)}",
            subdomain=subdomain,
            domain=domain,
        )
        EmailService.enqueue_verification(
            to_email=admin_email,
            company_name=company_name,
            subdomain=subdomain,
            verification_url=setup_url,
            expires_at=invitation.expires_at,
        )
        return raw_token, invitation, domain

    @staticmethod
    def create_tenant_with_domains(
        *,
        company_name: str,
        subdomain: str,
        owner_email: str,
        primary_domain: str = "",
        custom_domain: str = "",
        max_users: int = 10,
        max_branches: int = 1,
        plan: str = "free",
    ) -> tuple[Tenant, str]:
        public_schema = get_public_schema_name()
        with schema_context(public_schema):
            platform_settings = PlatformSettings.objects.first()
            schema_name = derive_schema_name(subdomain)
            if Tenant.objects.filter(schema_name=schema_name).exists():
                raise ValueError(
                    "This subdomain conflicts with an existing tenant schema."
                )

            slug_candidate = slugify(company_name)[:45] or subdomain
            code_candidate = (subdomain.replace("-", "") or "tenant")[:40].upper()
            unique_suffix = 1
            final_slug = slug_candidate
            while Tenant.objects.filter(slug=final_slug).exists():
                unique_suffix += 1
                final_slug = f"{slug_candidate}-{unique_suffix}"

            final_code = code_candidate
            while Tenant.objects.filter(code=final_code).exists():
                unique_suffix += 1
                final_code = f"{code_candidate}{unique_suffix}"

            tenant = Tenant.objects.create(
                schema_name=schema_name,
                name=company_name,
                slug=final_slug,
                code=final_code,
                owner_email=owner_email,
                billing_email=owner_email,
                timezone=(
                    platform_settings.default_timezone
                    if platform_settings
                    else "Asia/Dhaka"
                ),
                locale=(
                    platform_settings.default_language if platform_settings else "en"
                ),
                plan=plan or "free",
                status="trial",
                is_trial=True,
                trial_ends_at=timezone.now() + timedelta(days=14),
                max_users=max_users,
                max_branches=max_branches,
                is_enabled=True,
            )
            set_tenant_features(tenant, default_feature_keys())

            domain = (
                (primary_domain or full_domain_for_subdomain(subdomain)).strip().lower()
            )
            if Domain.objects.filter(domain=domain).exists():
                raise ValueError("This subdomain is already in use.")
            Domain.objects.create(domain=domain, tenant=tenant, is_primary=True)

            if custom_domain:
                custom_domain = custom_domain.strip().lower()
                if not Domain.objects.filter(domain=custom_domain).exists():
                    Domain.objects.create(
                        domain=custom_domain, tenant=tenant, is_primary=False
                    )

        return tenant, domain

    @staticmethod
    def bootstrap_tenant_schema(tenant: Tenant) -> None:
        """Seed default Main Branch and tenant roles after schema creation."""
        with schema_context(tenant.schema_name):
            from apps.branch.models import Branch

            Branch.objects.get_or_create(
                code="MAIN",
                defaults={
                    "name": "Main Branch",
                    "is_headquarters": True,
                    "status": Branch.STATUS_ACTIVE,
                },
            )
            from django.core.management import call_command

            call_command("seed_tenant_roles")
