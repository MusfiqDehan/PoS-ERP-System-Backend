"""Tests for branch manager assignment and scoping."""

import pytest
from django.db import connection
from django_tenants.utils import schema_context

from apps.access.models import Role, UserRole
from apps.branch.models import Branch
from apps.branch.services.manager import assign_branch_manager
from shared.tenancy.helpers import (
    get_branch_manager_scope_ids,
    scope_queryset_by_branch_access,
)


@pytest.mark.django_db
def test_assign_branch_manager_syncs_user_role_and_fk(tenant, tenant_schema):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    with schema_context(tenant.schema_name):
        connection.set_tenant(tenant)
        Role.objects.create(
            name="Branch Manager", slug="branch_manager", is_system=True
        )
        branch = Branch.objects.create(name="Main", code="MAIN")
        manager = User.objects.create_user(email="mgr@test.com", password="TestPass1!")

        assign_branch_manager(branch, manager)

        branch.refresh_from_db()
        assert branch.manager_id == manager.id
        assignment = UserRole.objects.get(
            user_id=manager.id, role__slug="branch_manager"
        )
        assert assignment.branch_id == branch.id


@pytest.mark.django_db
def test_branch_manager_scope_limits_queryset(tenant, tenant_schema):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    with schema_context(tenant.schema_name):
        connection.set_tenant(tenant)
        role = Role.objects.create(
            name="Branch Manager", slug="branch_manager", is_system=True
        )
        branch_a = Branch.objects.create(name="A", code="A")
        Branch.objects.create(name="B", code="B")
        user = User.objects.create_user(email="mgr@test.com", password="TestPass1!")
        UserRole.objects.create(
            user_id=user.id,
            user_email=user.email,
            role=role,
            branch=branch_a,
        )

        scoped = scope_queryset_by_branch_access(
            Branch.objects.all(), user, branch_field="id"
        )
        assert list(scoped.values_list("code", flat=True)) == ["A"]
        assert get_branch_manager_scope_ids(user) == [branch_a.id]
