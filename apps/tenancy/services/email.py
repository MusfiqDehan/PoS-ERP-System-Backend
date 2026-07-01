from __future__ import annotations

from django.conf import settings
from django.template.loader import render_to_string

from apps.tenancy.models import EmailQueue


def _json_safe_context(context: dict) -> dict:
    safe: dict = {}
    for key, value in context.items():
        if hasattr(value, "isoformat"):
            safe[key] = value.isoformat()
        else:
            safe[key] = value
    return safe


class EmailService:
    @staticmethod
    def enqueue(
        *,
        tenant,
        to_email: str,
        purpose: str,
        subject: str,
        template_name: str,
        context: dict,
        fallback_text: str,
    ) -> EmailQueue:
        html_body = render_to_string(template_name, context)
        return EmailQueue.objects.create(
            tenant=tenant,
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            text_body=fallback_text,
            purpose=purpose,
            context=_json_safe_context(context),
        )

    @classmethod
    def enqueue_verification(
        cls,
        *,
        to_email: str,
        company_name: str,
        subdomain: str,
        verification_url: str,
        expires_at,
    ) -> EmailQueue:
        return cls.enqueue(
            tenant=None,
            to_email=to_email,
            purpose=EmailQueue.PURPOSE_VERIFICATION,
            subject="Verify your tenant registration",
            template_name="tenancy/emails/verification_email.html",
            context={
                "company_name": company_name,
                "subdomain": subdomain,
                "verification_url": verification_url,
                "expires_at": expires_at,
            },
            fallback_text=f"Verify your registration by visiting {verification_url}",
        )

    @classmethod
    def enqueue_invitation(
        cls,
        *,
        tenant,
        to_email: str,
        company_name: str,
        subdomain: str,
        invitation_url: str,
        expires_at,
    ) -> EmailQueue:
        return cls.enqueue(
            tenant=tenant,
            to_email=to_email,
            purpose=EmailQueue.PURPOSE_INVITATION,
            subject="You have been invited to a tenant workspace",
            template_name="tenancy/emails/invitation_email.html",
            context={
                "company_name": company_name,
                "subdomain": subdomain,
                "invitation_url": invitation_url,
                "expires_at": expires_at,
            },
            fallback_text=f"Accept your invitation by visiting {invitation_url}",
        )

    @classmethod
    def enqueue_platform_invite(
        cls,
        *,
        to_email: str,
        invitee_full_name: str,
        role_name: str,
        invitation_url: str,
        expires_at,
    ) -> EmailQueue:
        sign_in_base = (
            getattr(settings, "PUBLIC_FRONTEND_URL", "").strip()
            or getattr(settings, "FRONTEND_BASE_URL", "").strip()
            or "https://sortorium.com"
        )
        sign_in_url = f"{sign_in_base.rstrip('/')}/signin"
        return cls.enqueue(
            tenant=None,
            to_email=to_email,
            purpose=EmailQueue.PURPOSE_PLATFORM_INVITE,
            subject="You have been invited to the Sortorium platform team",
            template_name="tenancy/emails/platform_invitation_email.html",
            context={
                "invitation_url": invitation_url,
                "expires_at": expires_at,
                "invitee_full_name": invitee_full_name,
                "role_name": role_name,
                "sign_in_url": sign_in_url,
            },
            fallback_text=f"Accept your platform invitation by visiting {invitation_url}",
        )

    @classmethod
    def enqueue_platform_password_reset(
        cls,
        *,
        to_email: str,
        reset_url: str,
        expires_at,
    ) -> EmailQueue:
        return cls.enqueue(
            tenant=None,
            to_email=to_email,
            purpose=EmailQueue.PURPOSE_PASSWORD_RESET,
            subject="Reset your Sortorium platform password",
            template_name="tenancy/emails/platform_password_reset_email.html",
            context={
                "reset_url": reset_url,
                "expires_at": expires_at,
            },
            fallback_text=f"Reset your platform password using {reset_url}",
        )

    @classmethod
    def enqueue_password_reset(
        cls,
        *,
        tenant,
        to_email: str,
        company_name: str,
        reset_url: str,
        expires_at,
    ) -> EmailQueue:
        return cls.enqueue(
            tenant=tenant,
            to_email=to_email,
            purpose=EmailQueue.PURPOSE_PASSWORD_RESET,
            subject="Reset your tenant password",
            template_name="tenancy/emails/password_reset_email.html",
            context={
                "company_name": company_name,
                "reset_url": reset_url,
                "expires_at": expires_at,
            },
            fallback_text=f"Reset your password using {reset_url}",
        )
