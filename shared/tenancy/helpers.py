from __future__ import annotations

from apps.access.models import UserRole


def is_tenant_admin_user(user) -> bool:
    return bool(user and user.is_authenticated and (user.is_superuser or user.is_staff))


def get_branch_manager_scope_ids(user):
    """Return branch IDs managed by branch_manager role assignments."""
    if not (user and user.is_authenticated):
        return None
    if is_tenant_admin_user(user):
        return None

    branch_ids = list(
        UserRole.objects.filter(
            user_id=user.id,
            role__slug="branch_manager",
            branch_id__isnull=False,
        )
        .values_list("branch_id", flat=True)
        .distinct()
    )
    if not branch_ids:
        has_branch_manager = UserRole.objects.filter(
            user_id=user.id,
            role__slug="branch_manager",
        ).exists()
        return [] if has_branch_manager else None
    return branch_ids


def apply_branch_scope(queryset, user, branch_field: str = "branch_id"):
    scope_ids = get_branch_manager_scope_ids(user)
    if scope_ids is None:
        return queryset
    if not scope_ids:
        return queryset.none()
    return queryset.filter(**{f"{branch_field}__in": scope_ids})


def apply_branch_filter_for_tenant_admin(
    queryset,
    user,
    branch_id,
    branch_field: str = "branch_id",
):
    if not is_tenant_admin_user(user):
        return queryset
    if branch_id in (None, "", "all"):
        return queryset
    try:
        branch_id_value = branch_id
        if not isinstance(branch_id, str):
            branch_id_value = branch_id
        else:
            from uuid import UUID

            branch_id_value = UUID(branch_id)
    except (TypeError, ValueError):
        return queryset.none()
    return queryset.filter(**{branch_field: branch_id_value})


def scope_queryset_by_branch_access(
    queryset,
    user,
    branch_field: str = "branch_id",
    branch_filter_id=None,
):
    queryset = apply_branch_scope(queryset, user, branch_field=branch_field)
    return apply_branch_filter_for_tenant_admin(
        queryset,
        user,
        branch_filter_id,
        branch_field=branch_field,
    )
