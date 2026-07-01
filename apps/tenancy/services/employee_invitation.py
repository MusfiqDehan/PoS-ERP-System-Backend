from __future__ import annotations

from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, schema_context

from apps.access.models import Role, UserRole
from apps.tenancy.models import Domain, Invitation
from apps.tenancy.services.auth import AuthService
from apps.tenancy.services.email import EmailService
from apps.tenancy.services.invitation import InvitationService
from apps.tenancy.services.registration import full_domain_for_subdomain

from shared.tenancy.helpers import (
    get_user_branch_scope_ids,
    is_tenant_admin_user,
)

BRANCH_MANAGER_INVITE_ROLES = frozenset(
    {"cashier", "viewer", "warehouse_manager", "branch_manager"}
)
BRANCH_MANAGER_BLOCKED_ROLES = frozenset({"admin", "manager"})
ADMIN_ONLY_ROLE_SLUGS = frozenset({"admin"})

User = get_user_model()


class TenantInvitationService:
    @staticmethod
    def _inviter_is_branch_manager_only(inviter) -> bool:
        if is_tenant_admin_user(inviter):
            return False
        from apps.access.services.permissions import get_user_permission_level

        level = get_user_permission_level(inviter, "permissions")
        from apps.tenancy.models import PERMISSION_HIERARCHY

        if PERMISSION_HIERARCHY.get(level, 0) >= PERMISSION_HIERARCHY.get("edit", 0):
            return False
        return UserRole.objects.filter(
            user_id=inviter.id, role__slug="branch_manager"
        ).exists()

    @classmethod
    def _can_invite(
        cls,
        *,
        inviter,
        tenant,
        role_slug: str,
        branch_id: str | UUID | None,
    ) -> None:
        role_slug = role_slug.strip().lower()
        if role_slug in ADMIN_ONLY_ROLE_SLUGS and not is_tenant_admin_user(inviter):
            raise PermissionError(
                "Only tenant admins can invite users with the admin role."
            )

        branch_manager_only = cls._inviter_is_branch_manager_only(inviter)
        if branch_manager_only:
            if role_slug in BRANCH_MANAGER_BLOCKED_ROLES:
                raise PermissionError("You cannot invite users with this role.")
            if role_slug not in BRANCH_MANAGER_INVITE_ROLES:
                raise PermissionError("You cannot invite users with this role.")
            if branch_id is None:
                raise ValueError(
                    "branch_id is required for branch manager invitations."
                )
            scope_ids = get_user_branch_scope_ids(inviter)
            if not scope_ids:
                raise PermissionError(
                    "You do not have branch access to invite employees."
                )
            try:
                branch_uuid = UUID(str(branch_id))
            except (TypeError, ValueError) as exc:
                raise ValueError("Invalid branch_id.") from exc
            if branch_uuid not in scope_ids:
                raise PermissionError(
                    "You can only invite employees to branches you manage."
                )

        if role_slug == "branch_manager" and branch_id is None:
            raise ValueError("branch_id is required when inviting a branch manager.")

        with schema_context(tenant.schema_name):
            if not Role.objects.filter(slug=role_slug).exists():
                raise ValueError("Invalid tenant role.")
            if branch_id is not None:
                from apps.branch.models import Branch

                try:
                    branch_uuid = UUID(str(branch_id))
                except (TypeError, ValueError) as exc:
                    raise ValueError("Invalid branch_id.") from exc
                if not Branch.objects.filter(pk=branch_uuid).exists():
                    raise ValueError("Branch not found.")

    @classmethod
    def issue(
        cls,
        *,
        inviter,
        tenant,
        email: str,
        full_name: str,
        role_slug: str,
        branch_id: str | UUID | None = None,
    ) -> Invitation:
        email = email.strip().lower()
        role_slug = role_slug.strip().lower()
        cls._can_invite(
            inviter=inviter,
            tenant=tenant,
            role_slug=role_slug,
            branch_id=branch_id,
        )

        with schema_context(get_public_schema_name()):
            primary_domain = Domain.objects.filter(
                tenant=tenant, is_primary=True
            ).values_list("domain", flat=True).first() or full_domain_for_subdomain(
                tenant.slug
            )
        branch_id_str = str(branch_id) if branch_id is not None else None

        with schema_context(tenant.schema_name):
            with transaction.atomic():
                user = User.objects.filter(email__iexact=email).first()
                if user is None:
                    user = User(email=email, full_name=full_name or "")
                    user.set_unusable_password()
                    user.save()
                elif (
                    user.password_set_at is not None
                    and UserRole.objects.filter(user_id=user.id).exists()
                ):
                    raise ValueError("User already has tenant access.")

        with schema_context(get_public_schema_name()):
            with transaction.atomic():
                pending = Invitation.objects.filter(
                    token_type=Invitation.TOKEN_TYPE_EMPLOYEE_INVITE,
                    tenant=tenant,
                    email=email,
                    used_at__isnull=True,
                    expires_at__gt=timezone.now(),
                ).exists()
                if pending:
                    raise ValueError(
                        "A pending invitation already exists for this email."
                    )

                raw_token, invitation = Invitation.issue_token(
                    token_type=Invitation.TOKEN_TYPE_EMPLOYEE_INVITE,
                    tenant=tenant,
                    email=email,
                    invitee_full_name=full_name,
                    subdomain=tenant.slug,
                    company_name=tenant.name,
                    invited_by_email=getattr(inviter, "email", "") or "",
                    ttl_minutes=72 * 60,
                    metadata={
                        "role_slug": role_slug,
                        "branch_id": branch_id_str,
                        "domain": primary_domain,
                    },
                )

            invite_url = InvitationService.build_token_url(invitation, raw_token)
            EmailService.enqueue_invitation(
                tenant=tenant,
                to_email=email,
                company_name=tenant.name,
                subdomain=tenant.slug,
                invitation_url=invite_url,
                expires_at=invitation.expires_at,
            )
        return invitation

    @staticmethod
    def validate(raw_token: str) -> Invitation | None:
        with schema_context(get_public_schema_name()):
            invitation = InvitationService.validate_token(raw_token)
        if invitation is None:
            return None
        if invitation.token_type != Invitation.TOKEN_TYPE_EMPLOYEE_INVITE:
            return None
        return invitation

    @staticmethod
    def serialize(invitation: Invitation) -> dict:
        metadata = invitation.metadata or {}
        role_slug = metadata.get("role_slug", "")
        role_name = ""
        branch_id = metadata.get("branch_id")
        branch_name = ""
        tenant = invitation.tenant
        if tenant and role_slug:
            with schema_context(tenant.schema_name):
                role = Role.objects.filter(slug=role_slug).first()
                if role:
                    role_name = role.name
                if branch_id:
                    from apps.branch.models import Branch

                    branch = Branch.objects.filter(pk=branch_id).first()
                    if branch:
                        branch_name = branch.name
        return {
            "token_type": invitation.token_type,
            "email": invitation.email,
            "full_name": invitation.invitee_full_name,
            "role_slug": role_slug,
            "role_name": role_name,
            "branch_id": branch_id,
            "branch_name": branch_name,
            "company_name": invitation.company_name,
            "subdomain": invitation.subdomain,
            "expires_at": invitation.expires_at,
        }

    @classmethod
    def accept(cls, *, raw_token: str, password: str) -> dict:
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters.")

        with transaction.atomic():
            with schema_context(get_public_schema_name()):
                invitation = Invitation.from_raw_token(raw_token, for_update=True)
                if (
                    invitation is None
                    or invitation.token_type != Invitation.TOKEN_TYPE_EMPLOYEE_INVITE
                ):
                    raise ValueError("Invalid or expired token.")
                if invitation.used_at is not None:
                    raise ValueError("Invitation already used.")
                if invitation.is_expired:
                    raise ValueError("Invalid or expired token.")
                tenant = invitation.tenant
                if tenant is None:
                    raise ValueError("Tenant context not found.")
                metadata = invitation.metadata or {}
            role_slug = metadata.get("role_slug")
            if not role_slug:
                raise ValueError("Invitation is missing a role assignment.")

            branch_id = metadata.get("branch_id")
            domain = metadata.get("domain") or full_domain_for_subdomain(
                invitation.subdomain
            )
            setup_time = timezone.now()
            email = invitation.email.lower().strip()

            with schema_context(tenant.schema_name):
                role = Role.objects.filter(slug=role_slug).first()
                if role is None:
                    raise ValueError("Invitation role is no longer valid.")

                user = User.objects.filter(email__iexact=email).first()
                if user is None:
                    user = User(
                        email=email,
                        full_name=invitation.invitee_full_name,
                    )
                user.set_password(password)
                user.email_verified = True
                user.password_set_at = setup_time
                user.is_active = True
                if invitation.invitee_full_name and not user.full_name:
                    user.full_name = invitation.invitee_full_name
                user.save()

                branch = None
                if branch_id:
                    from apps.branch.models import Branch

                    branch = Branch.objects.filter(pk=branch_id).first()
                    if branch is None:
                        raise ValueError("Invitation branch is no longer valid.")

                UserRole.objects.get_or_create(
                    user_id=user.id,
                    role=role,
                    branch=branch,
                    defaults={
                        "user_email": email,
                        "assigned_by_email": invitation.invited_by_email or "",
                    },
                )

            with schema_context(get_public_schema_name()):
                invitation.used_at = setup_time
                invitation.save(update_fields=["used_at"])

        tokens = AuthService.tokens_for_tenant_user(
            user=user, tenant=tenant, domain=domain
        )
        with schema_context(tenant.schema_name):
            serialized_user = AuthService.serialize_user(user)
        return {
            **tokens,
            "user": serialized_user,
            "tenant_domain": domain,
        }

    @staticmethod
    def revoke(*, invitation_id, tenant) -> None:
        with schema_context(get_public_schema_name()):
            invitation = Invitation.objects.filter(
                pk=invitation_id,
                tenant=tenant,
                token_type=Invitation.TOKEN_TYPE_EMPLOYEE_INVITE,
                used_at__isnull=True,
            ).first()
            if invitation is None:
                raise ValueError("Invitation not found.")
            invitation.used_at = timezone.now()
            invitation.save(update_fields=["used_at"])

    @staticmethod
    def list_queryset(tenant, *, inviter=None):
        filtered_ids = None
        if inviter is not None:
            with schema_context(tenant.schema_name):
                if not is_tenant_admin_user(inviter):
                    from apps.access.services.permissions import (
                        get_user_permission_level,
                    )
                    from apps.tenancy.models import PERMISSION_HIERARCHY

                    level = get_user_permission_level(inviter, "permissions")
                    if PERMISSION_HIERARCHY.get(level, 0) < PERMISSION_HIERARCHY.get(
                        "edit", 0
                    ):
                        scope_ids = get_user_branch_scope_ids(inviter)
                        if not scope_ids:
                            filtered_ids = []
                        else:
                            scope_strs = {str(bid) for bid in scope_ids}
                            with schema_context(get_public_schema_name()):
                                filtered_ids = [
                                    inv.id
                                    for inv in Invitation.objects.filter(
                                        token_type=Invitation.TOKEN_TYPE_EMPLOYEE_INVITE,
                                        tenant=tenant,
                                    )
                                    if str((inv.metadata or {}).get("branch_id"))
                                    in scope_strs
                                ]

        with schema_context(get_public_schema_name()):
            qs = Invitation.objects.filter(
                token_type=Invitation.TOKEN_TYPE_EMPLOYEE_INVITE,
                tenant=tenant,
            ).order_by("-created_at")
            if filtered_ids is not None:
                return qs.filter(id__in=filtered_ids)
            return qs
