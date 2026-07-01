from __future__ import annotations

from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import connection, transaction

from apps.access.models import Role, UserRole
from shared.cache.helpers import invalidate_user_permissions
from shared.tenancy.helpers import is_tenant_admin_user

User = get_user_model()


class TenantUserService:
    @staticmethod
    def queryset():
        user_ids = UserRole.objects.values_list("user_id", flat=True).distinct()
        return User.objects.filter(is_active=True, id__in=user_ids).order_by(
            "full_name", "email"
        )

    @staticmethod
    def get_tenant_user(user_id):
        user = User.objects.filter(pk=user_id).first()
        if user is None:
            return None
        if not UserRole.objects.filter(user_id=user.id).exists():
            return None
        return user

    @staticmethod
    def _count_active_admins(exclude_user_id=None) -> int:
        qs = UserRole.objects.filter(
            role__slug="admin",
            user_id__in=User.objects.filter(
                is_active=True, is_deleted=False
            ).values_list("id", flat=True),
        )
        if exclude_user_id:
            qs = qs.exclude(user_id=exclude_user_id)
        return qs.values("user_id").distinct().count()

    @classmethod
    def replace_roles(
        cls,
        *,
        actor,
        user,
        assignments: list[dict],
    ) -> list[dict]:
        normalized: list[tuple[str, str | None]] = []
        seen: set[tuple[str, str | None]] = set()
        for entry in assignments:
            role_slug = (entry.get("role_slug") or "").strip().lower()
            if not role_slug:
                raise ValueError("Each assignment requires role_slug.")
            branch_id = entry.get("branch_id")
            branch_key = str(branch_id) if branch_id not in (None, "") else None
            key = (role_slug, branch_key)
            if key in seen:
                continue
            seen.add(key)
            normalized.append(key)

        if not normalized:
            raise ValueError("At least one role assignment is required.")

        role_slugs = [slug for slug, _ in normalized]
        if "admin" in role_slugs and not is_tenant_admin_user(actor):
            raise PermissionError("Only tenant admins can assign the admin role.")

        roles = {r.slug: r for r in Role.objects.filter(slug__in=role_slugs)}
        if len(roles) != len(set(role_slugs)):
            raise ValueError("One or more role slugs are invalid.")

        branches: dict[str, object] = {}
        for _, branch_key in normalized:
            if branch_key is None:
                continue
            if branch_key in branches:
                continue
            from apps.branch.models import Branch

            try:
                branch_uuid = UUID(branch_key)
            except (TypeError, ValueError) as exc:
                raise ValueError("Invalid branch_id in assignment.") from exc
            branch = Branch.objects.filter(pk=branch_uuid).first()
            if branch is None:
                raise ValueError("Branch not found.")
            branches[branch_key] = branch

        is_self = actor.id == user.id
        had_admin = UserRole.objects.filter(
            user_id=user.id, role__slug="admin"
        ).exists()
        will_have_admin = "admin" in role_slugs
        if is_self and had_admin and not will_have_admin:
            if cls._count_active_admins(exclude_user_id=user.id) == 0:
                raise ValueError("Cannot remove the last admin role.")

        actor_email = getattr(actor, "email", "") or ""
        with transaction.atomic():
            UserRole.objects.filter(user_id=user.id).delete()
            for role_slug, branch_key in normalized:
                branch = branches.get(branch_key) if branch_key else None
                UserRole.objects.create(
                    user_id=user.id,
                    user_email=user.email or "",
                    role=roles[role_slug],
                    branch=branch,
                    assigned_by_email=actor_email,
                )

        invalidate_user_permissions(connection.schema_name, user.id)
        return cls._role_assignments_for_user(user)

    @classmethod
    def deactivate(cls, *, actor, user) -> None:
        del actor
        is_admin = UserRole.objects.filter(user_id=user.id, role__slug="admin").exists()
        if is_admin and cls._count_active_admins(exclude_user_id=user.id) == 0:
            raise ValueError("Cannot deactivate the last active tenant admin.")

        user.is_active = False
        user.save(update_fields=["is_active", "updated_at"])
        invalidate_user_permissions(connection.schema_name, user.id)

    @staticmethod
    def _role_assignments_for_user(user) -> list[dict]:
        rows = UserRole.objects.filter(user_id=user.id).select_related("role", "branch")
        return [
            {
                "role_slug": row.role.slug,
                "role_name": row.role.name,
                "branch_id": str(row.branch_id) if row.branch_id else None,
                "branch_name": row.branch.name if row.branch_id else None,
                "assigned_at": row.created_at,
            }
            for row in rows
        ]

    @classmethod
    def serialize_user(cls, user) -> dict:
        return {
            "id": str(user.id),
            "email": user.email,
            "phone": user.phone,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "email_verified": user.email_verified,
            "role_assignments": cls._role_assignments_for_user(user),
            "role_slugs": [
                a["role_slug"] for a in cls._role_assignments_for_user(user)
            ],
            "last_login": user.last_login,
            "created_at": user.created_at,
        }
