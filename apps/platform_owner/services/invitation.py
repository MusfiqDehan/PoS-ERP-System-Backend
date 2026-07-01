from __future__ import annotations

from urllib.parse import quote

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, schema_context

from apps.tenancy.models import Invitation, PlatformRole, PlatformUserRole
from apps.tenancy.services.email import EmailService
from apps.tenancy.services.invitation import InvitationService
from apps.tenancy.services.platform_permissions import PlatformPermissionService
from apps.tenancy.services.registration import build_platform_frontend_url

from apps.platform_owner.services.auth import PlatformAuthService

User = get_user_model()


def _platform_invite_url(raw_token: str) -> str:
    path = f"/accept-platform-invite?token={quote(raw_token)}"
    return build_platform_frontend_url(path)


class PlatformInvitationService:
    @staticmethod
    def _can_assign_role(inviter, role_slug: str) -> bool:
        if role_slug == "superadmin":
            return PlatformPermissionService.is_superadmin(inviter)
        return PlatformPermissionService.user_can(
            inviter, "platform.platform_users", "edit"
        )

    @classmethod
    def issue(
        cls,
        *,
        inviter,
        email: str,
        full_name: str,
        role_slug: str,
    ) -> Invitation:
        email = email.strip().lower()
        if not cls._can_assign_role(inviter, role_slug):
            raise PermissionError("You cannot invite users with this role.")

        with schema_context(get_public_schema_name()):
            role = PlatformRole.objects.filter(slug=role_slug).first()
            if role is None:
                raise ValueError("Invalid platform role.")

            with transaction.atomic():
                user = User.objects.filter(
                    email__iexact=email, tenant__isnull=True
                ).first()
                if user is None:
                    user = User(email=email, full_name=full_name or "", tenant=None)
                    user.set_unusable_password()
                    user.save()
                elif (
                    user.password_set_at is not None
                    and PlatformUserRole.objects.filter(user=user).exists()
                ):
                    raise ValueError("User already has platform access.")

                pending = Invitation.objects.filter(
                    token_type=Invitation.TOKEN_TYPE_PLATFORM_INVITE,
                    email=email,
                    used_at__isnull=True,
                    expires_at__gt=timezone.now(),
                ).exists()
                if pending:
                    raise ValueError(
                        "A pending invitation already exists for this email."
                    )

                raw_token, invitation = Invitation.issue_token(
                    token_type=Invitation.TOKEN_TYPE_PLATFORM_INVITE,
                    email=email,
                    invitee_full_name=full_name,
                    subdomain="",
                    company_name="Sortorium Platform",
                    invited_by_email=getattr(inviter, "email", "") or "",
                    ttl_minutes=72 * 60,
                    platform_role=role,
                )

        invite_url = _platform_invite_url(raw_token)
        EmailService.enqueue_platform_invite(
            to_email=email,
            invitee_full_name=full_name,
            role_name=role.name,
            invitation_url=invite_url,
            expires_at=invitation.expires_at,
        )
        return invitation

    @staticmethod
    def validate(raw_token: str) -> Invitation | None:
        invitation = InvitationService.validate_token(raw_token)
        if invitation is None:
            return None
        if invitation.token_type != Invitation.TOKEN_TYPE_PLATFORM_INVITE:
            return None
        return invitation

    @staticmethod
    def serialize(invitation: Invitation) -> dict:
        role_slug = ""
        role_name = ""
        if invitation.platform_role_id:
            role_slug = invitation.platform_role.slug
            role_name = invitation.platform_role.name
        return {
            "token_type": invitation.token_type,
            "email": invitation.email,
            "full_name": invitation.invitee_full_name,
            "role_slug": role_slug,
            "role_name": role_name,
            "expires_at": invitation.expires_at,
        }

    @classmethod
    def accept(cls, *, raw_token: str, password: str) -> dict:
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters.")

        with transaction.atomic():
            invitation = Invitation.from_raw_token(raw_token, for_update=True)
            if (
                invitation is None
                or invitation.token_type != Invitation.TOKEN_TYPE_PLATFORM_INVITE
            ):
                raise ValueError("Invalid or expired token.")
            if invitation.used_at is not None:
                raise ValueError("Invitation already used.")
            if invitation.is_expired:
                raise ValueError("Invalid or expired token.")
            if invitation.platform_role_id is None:
                raise ValueError("Invitation is missing a platform role.")

            setup_time = timezone.now()
            with schema_context(get_public_schema_name()):
                user = User.objects.filter(
                    email__iexact=invitation.email, tenant__isnull=True
                ).first()
                if user is None:
                    user = User(
                        email=invitation.email.lower().strip(),
                        full_name=invitation.invitee_full_name,
                        tenant=None,
                    )
                user.set_password(password)
                user.email_verified = True
                user.password_set_at = setup_time
                user.is_active = True
                if invitation.invitee_full_name and not user.full_name:
                    user.full_name = invitation.invitee_full_name
                user.save()

                PlatformUserRole.objects.get_or_create(
                    user=user,
                    role_id=invitation.platform_role_id,
                    defaults={"assigned_by": None},
                )

            invitation.used_at = setup_time
            invitation.save(update_fields=["used_at"])

        tokens = PlatformAuthService.tokens_for_user(user)
        return {
            **tokens,
            "user": PlatformAuthService.serialize_user(user),
        }

    @staticmethod
    def revoke(invitation_id) -> None:
        with schema_context(get_public_schema_name()):
            invitation = Invitation.objects.filter(
                pk=invitation_id,
                token_type=Invitation.TOKEN_TYPE_PLATFORM_INVITE,
                used_at__isnull=True,
            ).first()
            if invitation is None:
                raise ValueError("Invitation not found.")
            invitation.used_at = timezone.now()
            invitation.save(update_fields=["used_at"])

    @staticmethod
    def list_queryset():
        return (
            Invitation.objects.filter(token_type=Invitation.TOKEN_TYPE_PLATFORM_INVITE)
            .select_related("platform_role")
            .order_by("-created_at")
        )
