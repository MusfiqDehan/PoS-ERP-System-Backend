from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django_tenants.utils import schema_context

from apps.access.models import Role, UserRole
from apps.tenancy.models import Invitation
from apps.tenancy.services.registration import (
    TenantRegistrationService,
    full_domain_for_subdomain,
)

User = get_user_model()


class PasswordService:
    ALLOWED_SETUP_TYPES = {
        Invitation.TOKEN_TYPE_VERIFICATION,
        Invitation.TOKEN_TYPE_INVITATION,
        Invitation.TOKEN_TYPE_PASSWORD_RESET,
    }

    @staticmethod
    def setup_password(*, raw_token: str, password: str) -> dict:
        with transaction.atomic():
            invitation = Invitation.from_raw_token(raw_token, for_update=True)
            if invitation is None:
                raise ValueError("Invalid or expired token.")
            if invitation.used_at is not None:
                return PasswordService._success_payload(invitation, already_used=True)
            if invitation.is_expired:
                raise ValueError("Invalid or expired token.")
            if invitation.token_type not in PasswordService.ALLOWED_SETUP_TYPES:
                raise ValueError("Token type is not allowed for password setup.")

            tenant = invitation.tenant
            metadata = invitation.metadata or {}
            domain = metadata.get("domain") or full_domain_for_subdomain(
                invitation.subdomain
            )
            is_owner_setup = invitation.token_type in {
                Invitation.TOKEN_TYPE_VERIFICATION,
                Invitation.TOKEN_TYPE_INVITATION,
            }

            if tenant is None:
                if not is_owner_setup:
                    raise ValueError("Tenant context not found.")
                tenant, domain = TenantRegistrationService.create_tenant_with_domains(
                    company_name=invitation.company_name,
                    subdomain=invitation.subdomain,
                    owner_email=invitation.email.lower().strip(),
                    primary_domain=domain,
                    plan=metadata.get("plan", "free"),
                )
                invitation.tenant = tenant
                invitation.save(update_fields=["tenant"])
                TenantRegistrationService.bootstrap_tenant_schema(tenant)
            else:
                domain = (
                    tenant.domains.filter(is_primary=True)
                    .values_list("domain", flat=True)
                    .first()
                    or domain
                )

            email = invitation.email.lower().strip()
            setup_time = timezone.now()
            with schema_context(tenant.schema_name):
                user = User.objects.filter(email__iexact=email).first()
                if user is None:
                    if not is_owner_setup:
                        raise ValueError("User account not found.")
                    user = User.objects.create_user(
                        email=email,
                        password=password,
                        full_name=invitation.invitee_full_name,
                        email_verified=True,
                        password_set_at=setup_time,
                    )
                else:
                    user.set_password(password)
                    user.is_active = True
                    user.email_verified = True
                    user.password_set_at = setup_time
                    if invitation.invitee_full_name and not user.full_name:
                        user.full_name = invitation.invitee_full_name
                    user.save()

                if is_owner_setup:
                    admin_role = Role.objects.filter(slug="admin").first()
                    if admin_role:
                        UserRole.objects.get_or_create(
                            user_id=user.id,
                            role=admin_role,
                            defaults={"user_email": email},
                        )

            invitation.used_at = setup_time
            invitation.save(update_fields=["used_at"])

        return PasswordService._success_payload(invitation, domain=domain)

    @staticmethod
    def change_password(*, user, current_password: str, new_password: str) -> None:
        if not user.check_password(current_password):
            raise ValueError("Current password is incorrect.")
        if len(new_password) < 8:
            raise ValueError("New password must be at least 8 characters.")
        user.set_password(new_password)
        user.password_set_at = timezone.now()
        user.save(update_fields=["password", "password_set_at"])

    @staticmethod
    def _success_payload(
        invitation: Invitation, *, domain: str = "", already_used: bool = False
    ) -> dict:
        metadata = invitation.metadata or {}
        resolved_domain = (
            domain
            or metadata.get("domain")
            or full_domain_for_subdomain(invitation.subdomain)
        )
        from apps.tenancy.services.registration import build_frontend_url

        return {
            "message": (
                "Password was already configured successfully."
                if already_used
                else "Password configured successfully."
            ),
            "tenant_schema": invitation.tenant.schema_name if invitation.tenant else "",
            "tenant_domain": resolved_domain,
            "login_url": build_frontend_url(
                "/login",
                subdomain=invitation.subdomain,
                domain=resolved_domain,
            ),
        }
