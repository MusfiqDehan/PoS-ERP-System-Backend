from __future__ import annotations

from urllib.parse import quote

from apps.tenancy.models import Invitation
from apps.tenancy.services.email import EmailService
from apps.tenancy.services.registration import (
    build_frontend_url,
    build_platform_frontend_url,
    full_domain_for_subdomain,
)


class InvitationService:
    TOKEN_PATHS = {
        Invitation.TOKEN_TYPE_VERIFICATION: "verify-email",
        Invitation.TOKEN_TYPE_INVITATION: "accept-invite",
        Invitation.TOKEN_TYPE_PASSWORD_RESET: "reset-password",
        Invitation.TOKEN_TYPE_PLATFORM_INVITE: "accept-platform-invite",
        Invitation.TOKEN_TYPE_EMPLOYEE_INVITE: "accept-employee-invite",
    }

    @staticmethod
    def _uses_platform_frontend_host(invitation: Invitation) -> bool:
        if invitation.token_type == Invitation.TOKEN_TYPE_PLATFORM_INVITE:
            return True
        return (
            invitation.token_type == Invitation.TOKEN_TYPE_PASSWORD_RESET
            and invitation.tenant_id is None
        )

    @classmethod
    def validate_token(cls, raw_token: str) -> Invitation | None:
        invitation = Invitation.from_raw_token(raw_token)
        if invitation is None or not invitation.is_usable:
            return None
        return invitation

    @classmethod
    def build_token_url(cls, invitation: Invitation, raw_token: str) -> str:
        path = cls.TOKEN_PATHS.get(invitation.token_type, "accept-invite")
        path_with_token = f"/{path}?token={quote(raw_token)}"
        if cls._uses_platform_frontend_host(invitation):
            return build_platform_frontend_url(path_with_token)
        metadata = invitation.metadata or {}
        domain = metadata.get("domain") or full_domain_for_subdomain(
            invitation.subdomain
        )
        return build_frontend_url(
            path_with_token,
            subdomain=invitation.subdomain,
            domain=domain,
        )

    @classmethod
    def serialize_invitation(cls, invitation: Invitation, raw_token: str) -> dict:
        metadata = invitation.metadata or {}
        domain = metadata.get("domain") or full_domain_for_subdomain(
            invitation.subdomain
        )
        return {
            "token_type": invitation.token_type,
            "email": invitation.email,
            "full_name": invitation.invitee_full_name,
            "company_name": invitation.company_name,
            "subdomain": invitation.subdomain,
            "tenant_domain": domain,
            "expires_at": invitation.expires_at,
            "password_setup_url": cls.build_token_url(invitation, raw_token),
        }

    @classmethod
    def issue_password_reset(
        cls,
        *,
        tenant,
        email: str,
        full_name: str,
        subdomain: str,
        domain: str,
    ) -> None:
        raw_token, invitation = Invitation.issue_token(
            token_type=Invitation.TOKEN_TYPE_PASSWORD_RESET,
            tenant=tenant,
            email=email,
            invitee_full_name=full_name,
            subdomain=subdomain,
            company_name=tenant.name,
            ttl_minutes=30,
            metadata={"domain": domain},
        )
        reset_url = cls.build_token_url(invitation, raw_token)
        EmailService.enqueue_password_reset(
            tenant=tenant,
            to_email=email,
            company_name=tenant.name,
            reset_url=reset_url,
            expires_at=invitation.expires_at,
        )
