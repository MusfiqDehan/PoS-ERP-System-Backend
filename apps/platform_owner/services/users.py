from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction
from django_tenants.utils import get_public_schema_name, schema_context

from apps.tenancy.models import PlatformRole, PlatformUserRole
from apps.tenancy.services.platform_permissions import PlatformPermissionService

User = get_user_model()


class PlatformUserService:
    @staticmethod
    def queryset():
        user_ids = PlatformUserRole.objects.values_list("user_id", flat=True).distinct()
        return User.objects.filter(tenant__isnull=True, id__in=user_ids).order_by(
            "email"
        )

    @staticmethod
    def get_platform_user(user_id):
        with schema_context(get_public_schema_name()):
            user = User.objects.filter(pk=user_id, tenant__isnull=True).first()
            if user is None:
                return None
            if not PlatformUserRole.objects.filter(user=user).exists():
                return None
            return user

    @staticmethod
    def _count_active_superadmins(exclude_user_id=None) -> int:
        qs = PlatformUserRole.objects.filter(
            role__slug="superadmin",
            user__is_active=True,
            user__is_deleted=False,
            user__tenant__isnull=True,
        )
        if exclude_user_id:
            qs = qs.exclude(user_id=exclude_user_id)
        return qs.count()

    @classmethod
    def replace_roles(cls, *, actor, user, role_slugs: list[str]) -> list[str]:
        role_slugs = list(dict.fromkeys(role_slugs))
        if "superadmin" in role_slugs and not PlatformPermissionService.is_superadmin(
            actor
        ):
            raise PermissionError("Only superadmins can assign the superadmin role.")

        with schema_context(get_public_schema_name()):
            roles = list(PlatformRole.objects.filter(slug__in=role_slugs))
            if len(roles) != len(role_slugs):
                raise ValueError("One or more role slugs are invalid.")

            is_self = actor.id == user.id
            had_superadmin = PlatformUserRole.objects.filter(
                user=user, role__slug="superadmin"
            ).exists()
            will_have_superadmin = "superadmin" in role_slugs

            if is_self and had_superadmin and not will_have_superadmin:
                if cls._count_active_superadmins(exclude_user_id=user.id) == 0:
                    raise ValueError("Cannot remove the last superadmin role.")

            with transaction.atomic():
                PlatformUserRole.objects.filter(user=user).delete()
                for role in roles:
                    PlatformUserRole.objects.create(
                        user=user,
                        role=role,
                        assigned_by=actor,
                    )

            return list(
                PlatformUserRole.objects.filter(user=user).values_list(
                    "role__slug", flat=True
                )
            )

    @classmethod
    def deactivate(cls, *, actor, user) -> None:
        is_superadmin = PlatformUserRole.objects.filter(
            user=user, role__slug="superadmin"
        ).exists()
        if (
            is_superadmin
            and cls._count_active_superadmins(exclude_user_id=user.id) == 0
        ):
            raise ValueError("Cannot deactivate the last active superadmin.")

        user.is_active = False
        user.save(update_fields=["is_active", "updated_at"])

    @staticmethod
    def serialize_user(user) -> dict:
        roles = list(
            PlatformUserRole.objects.filter(user=user)
            .select_related("role")
            .order_by("role__name")
        )
        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "platform_roles": [r.role.slug for r in roles],
            "role_assignments": [
                {
                    "slug": r.role.slug,
                    "name": r.role.name,
                    "assigned_at": r.created_at,
                }
                for r in roles
            ],
            "last_login": user.last_login,
            "created_at": user.created_at,
        }
