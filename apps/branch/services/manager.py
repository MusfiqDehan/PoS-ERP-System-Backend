from __future__ import annotations

from django.db import transaction

from apps.access.models import Role, UserRole
from apps.branch.models import Branch


class BranchManagerError(ValueError):
    pass


def validate_branch_manager_user(user, *, branch: Branch | None = None) -> None:
    if user is None:
        raise BranchManagerError("Manager user is required.")


@transaction.atomic
def assign_branch_manager(branch: Branch, user) -> Branch:
    validate_branch_manager_user(user, branch=branch)
    role = Role.objects.filter(slug="branch_manager", is_system=True).first()
    if role is None:
        raise BranchManagerError("branch_manager system role is not seeded.")

    UserRole.objects.filter(
        role=role,
        branch=branch,
    ).exclude(user_id=user.id).delete()

    UserRole.objects.update_or_create(
        user_id=user.id,
        role=role,
        defaults={
            "user_email": getattr(user, "email", "") or "",
            "branch": branch,
        },
    )
    branch.manager = user
    branch.save(update_fields=["manager", "updated_at"])
    return branch
