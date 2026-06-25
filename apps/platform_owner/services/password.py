from __future__ import annotations

from django.contrib.auth import get_user_model
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, schema_context

from apps.tenancy.models import Invitation, PlatformUserRole
from apps.tenancy.services.email import EmailService
from apps.tenancy.services.invitation import InvitationService

from apps.platform_owner.services.invitation import _platform_console_subdomain

User = get_user_model()


class PlatformPasswordService:
    @staticmethod
    def request_reset(*, email: str) -> None:
        email = email.strip().lower()
        with schema_context(get_public_schema_name()):
            user = User.objects.filter(email__iexact=email, tenant__isnull=True).first()
            if user is None or user.password_set_at is None:
                return
            if not PlatformUserRole.objects.filter(user=user).exists():
                return

            raw_token, invitation = Invitation.issue_token(
                token_type=Invitation.TOKEN_TYPE_PASSWORD_RESET,
                email=email,
                invitee_full_name=user.full_name,
                subdomain=_platform_console_subdomain(),
                company_name="Sortorium Platform",
                ttl_minutes=30,
            )
        reset_url = InvitationService.build_token_url(invitation, raw_token)
        EmailService.enqueue_password_reset(
            tenant=None,
            to_email=email,
            company_name="Sortorium Platform",
            reset_url=reset_url,
            expires_at=invitation.expires_at,
        )

    @staticmethod
    def confirm_reset(*, raw_token: str, password: str) -> None:
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters.")

        invitation = Invitation.from_raw_token(raw_token, for_update=True)
        if invitation is None:
            raise ValueError("Invalid or expired token.")
        if invitation.token_type != Invitation.TOKEN_TYPE_PASSWORD_RESET:
            raise ValueError("Invalid or expired token.")
        if invitation.used_at is not None:
            raise ValueError("Invalid or expired token.")
        if invitation.is_expired:
            raise ValueError("Invalid or expired token.")
        if invitation.tenant_id is not None:
            raise ValueError("Invalid or expired token.")

        with schema_context(get_public_schema_name()):
            user = User.objects.filter(
                email__iexact=invitation.email, tenant__isnull=True
            ).first()
            if user is None:
                raise ValueError("User account not found.")
            user.set_password(password)
            user.password_set_at = timezone.now()
            user.save(update_fields=["password", "password_set_at"])

        invitation.used_at = timezone.now()
        invitation.save(update_fields=["used_at"])
