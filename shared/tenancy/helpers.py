from __future__ import annotations

from uuid import UUID

from apps.access.models import UserRole
from shared.responses.error_codes import ErrorCode
from shared.responses.exceptions import DomainAPIException


def user_has_tenant_admin_role(user) -> bool:
    if not (user and user.is_authenticated):
        return False
    return UserRole.objects.filter(user_id=user.id, role__slug="admin").exists()


def is_tenant_admin_user(user) -> bool:
    return user_has_tenant_admin_role(user)


def get_user_branch_scope_ids(user):
    """Return branch IDs the user may access, or None if unrestricted.

    - None: tenant admin or user without branch-assigned roles
    - []: user has role assignment(s) but no branch on any UserRole
    - [uuid, ...]: union of non-null UserRole.branch_id values
    """
    if not (user and user.is_authenticated):
        return None
    if is_tenant_admin_user(user):
        return None

    branch_ids = list(
        UserRole.objects.filter(
            user_id=user.id,
            branch_id__isnull=False,
        )
        .values_list("branch_id", flat=True)
        .distinct()
    )
    if branch_ids:
        return branch_ids

    return None


def get_branch_manager_scope_ids(user):
    """Deprecated alias for ``get_user_branch_scope_ids``."""
    return get_user_branch_scope_ids(user)


def assert_user_branch_access(user, branch_id) -> None:
    """Raise DomainAPIException when user cannot access the given branch."""
    scope_ids = get_user_branch_scope_ids(user)
    if scope_ids is None:
        return
    try:
        branch_uuid = branch_id if isinstance(branch_id, UUID) else UUID(str(branch_id))
    except (TypeError, ValueError) as exc:
        raise DomainAPIException(
            error_code=ErrorCode.VALIDATION_ERROR,
            user_message="Invalid branch identifier.",
            status_code=400,
        ) from exc
    if not scope_ids or branch_uuid not in scope_ids:
        raise DomainAPIException(
            error_code=ErrorCode.PERMISSION_DENIED,
            user_message="You do not have access to this branch.",
            status_code=403,
        )


def resolve_branch_filter_id(user, branch_filter_id):
    """Return explicit branch filter or auto-select sole assigned branch."""
    if branch_filter_id not in (None, "", "all"):
        return branch_filter_id
    scope_ids = get_user_branch_scope_ids(user)
    if scope_ids and len(scope_ids) == 1:
        return str(scope_ids[0])
    return branch_filter_id


def apply_branch_scope(queryset, user, branch_field: str = "branch_id"):
    scope_ids = get_user_branch_scope_ids(user)
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
            branch_id_value = UUID(branch_id)
    except (TypeError, ValueError):
        return queryset.none()
    return queryset.filter(**{branch_field: branch_id_value})


def scope_users_by_branch_access(queryset, user, branch_filter_id=None):
    """Filter tenant users by branch scope or optional admin branch filter."""
    scope_ids = get_user_branch_scope_ids(user)
    if scope_ids is None:
        if is_tenant_admin_user(user) and branch_filter_id not in (None, "", "all"):
            try:
                branch_uuid = UUID(str(branch_filter_id))
            except (TypeError, ValueError):
                return queryset.none()
            user_ids = UserRole.objects.filter(branch_id=branch_uuid).values_list(
                "user_id", flat=True
            )
            return queryset.filter(id__in=user_ids).distinct()
        return queryset
    if not scope_ids:
        return queryset.none()
    user_ids = UserRole.objects.filter(branch_id__in=scope_ids).values_list(
        "user_id", flat=True
    )
    return queryset.filter(id__in=user_ids).distinct()


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
