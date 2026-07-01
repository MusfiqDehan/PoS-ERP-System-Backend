"""Tests for generalized branch scope helpers."""

import pytest
from django.db import connection
from django_tenants.utils import schema_context

from apps.access.models import Role, UserRole
from apps.branch.models import Branch
from shared.responses.error_codes import ErrorCode
from shared.responses.exceptions import DomainAPIException
from shared.tenancy.helpers import (
    assert_user_branch_access,
    get_branch_manager_scope_ids,
    get_user_branch_scope_ids,
)


@pytest.mark.django_db
def test_admin_has_unrestricted_scope(tenant, tenant_schema):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    with schema_context(tenant.schema_name):
        connection.set_tenant(tenant)
        admin_role = Role.objects.create(name="Admin", slug="admin", is_system=True)
        user = User.objects.create_user(email="admin@scope.test", password="TestPass1!")
        UserRole.objects.create(user_id=user.id, user_email=user.email, role=admin_role)
        assert get_user_branch_scope_ids(user) is None


@pytest.mark.django_db
def test_cashier_with_branch_is_scoped(tenant, tenant_schema):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    with schema_context(tenant.schema_name):
        connection.set_tenant(tenant)
        branch = Branch.objects.create(name="Cashier Branch", code="CB")
        role = Role.objects.create(name="Cashier", slug="cashier", is_system=True)
        user = User.objects.create_user(email="cashier@scope.test", password="TestPass1!")
        UserRole.objects.create(
            user_id=user.id,
            user_email=user.email,
            role=role,
            branch=branch,
        )
        assert get_user_branch_scope_ids(user) == [branch.id]


@pytest.mark.django_db
def test_user_without_branch_assignment_is_unrestricted(tenant, tenant_schema):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    with schema_context(tenant.schema_name):
        connection.set_tenant(tenant)
        role = Role.objects.create(name="Manager", slug="manager", is_system=True)
        user = User.objects.create_user(email="mgr@scope.test", password="TestPass1!")
        UserRole.objects.create(user_id=user.id, user_email=user.email, role=role)
        assert get_user_branch_scope_ids(user) is None


@pytest.mark.django_db
def test_branch_manager_alias_matches_user_scope(tenant, tenant_schema):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    with schema_context(tenant.schema_name):
        connection.set_tenant(tenant)
        branch = Branch.objects.create(name="BM Branch", code="BM")
        role = Role.objects.create(
            name="Branch Manager", slug="branch_manager", is_system=True
        )
        user = User.objects.create_user(email="bm@scope.test", password="TestPass1!")
        UserRole.objects.create(
            user_id=user.id,
            user_email=user.email,
            role=role,
            branch=branch,
        )
        assert get_branch_manager_scope_ids(user) == [branch.id]
        assert get_user_branch_scope_ids(user) == [branch.id]


@pytest.mark.django_db
def test_assert_user_branch_access_denies_foreign_branch(tenant, tenant_schema):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    with schema_context(tenant.schema_name):
        connection.set_tenant(tenant)
        branch_a = Branch.objects.create(name="A", code="A")
        branch_b = Branch.objects.create(name="B", code="B")
        role = Role.objects.create(name="Cashier", slug="cashier", is_system=True)
        user = User.objects.create_user(email="c@scope.test", password="TestPass1!")
        UserRole.objects.create(
            user_id=user.id,
            user_email=user.email,
            role=role,
            branch=branch_a,
        )
        with pytest.raises(DomainAPIException) as exc_info:
            assert_user_branch_access(user, branch_b.id)
        assert exc_info.value.error_code == str(ErrorCode.PERMISSION_DENIED)
        assert exc_info.value.status_code == 403


@pytest.mark.django_db
def test_assert_user_branch_access_allows_own_branch(tenant, tenant_schema):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    with schema_context(tenant.schema_name):
        connection.set_tenant(tenant)
        branch = Branch.objects.create(name="Own", code="OWN")
        role = Role.objects.create(name="Cashier", slug="cashier", is_system=True)
        user = User.objects.create_user(email="own@scope.test", password="TestPass1!")
        UserRole.objects.create(
            user_id=user.id,
            user_email=user.email,
            role=role,
            branch=branch,
        )
        assert_user_branch_access(user, branch.id)
