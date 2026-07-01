"""Fixtures for tenant employee invitation and user management tests."""

import pytest
from django.contrib.auth import get_user_model
from django.db import connection

from apps.access.models import Role, RolePermission, UserRole
from apps.branch.models import Branch

User = get_user_model()


@pytest.fixture
def seeded_tenant_roles(tenant_schema):
    connection.set_tenant(tenant_schema)
    admin_role, _ = Role.objects.get_or_create(
        slug="admin",
        defaults={"name": "Admin", "is_system": True},
    )
    cashier_role, _ = Role.objects.get_or_create(
        slug="cashier",
        defaults={"name": "Cashier", "is_system": True},
    )
    manager_role, _ = Role.objects.get_or_create(
        slug="branch_manager",
        defaults={"name": "Branch Manager", "is_system": True},
    )
    for feature_key in ("permissions", "dashboard", "pos"):
        RolePermission.objects.get_or_create(
            role=admin_role,
            feature_key=feature_key,
            defaults={"permission_level": "full"},
        )
    return {
        "admin": admin_role,
        "cashier": cashier_role,
        "branch_manager": manager_role,
    }


@pytest.fixture
def tenant_admin_user(tenant_schema, tenant_domain, seeded_tenant_roles):
    connection.set_tenant(tenant_schema)
    user = User.objects.create_user(
        email="admin@tenant.test",
        password="TestPass1!",
        full_name="Tenant Admin",
    )
    UserRole.objects.create(
        user_id=user.id,
        user_email=user.email,
        role=seeded_tenant_roles["admin"],
    )
    return user


@pytest.fixture
def tenant_branch_manager(tenant_schema, tenant_domain, seeded_tenant_roles):
    connection.set_tenant(tenant_schema)
    branch = Branch.objects.create(name="Main", code="MAIN")
    user = User.objects.create_user(
        email="bmgr@tenant.test",
        password="TestPass1!",
        full_name="Branch Manager",
    )
    UserRole.objects.create(
        user_id=user.id,
        user_email=user.email,
        role=seeded_tenant_roles["branch_manager"],
        branch=branch,
    )
    return user, branch


@pytest.fixture
def tenant_permissions_editor(tenant_schema, tenant_domain, seeded_tenant_roles):
    connection.set_tenant(tenant_schema)
    editor_role, _ = Role.objects.get_or_create(
        slug="permissions_editor",
        defaults={"name": "Permissions Editor", "is_system": False},
    )
    RolePermission.objects.get_or_create(
        role=editor_role,
        feature_key="permissions",
        defaults={"permission_level": "edit"},
    )
    user = User.objects.create_user(
        email="editor@tenant.test",
        password="TestPass1!",
        full_name="Permissions Editor",
    )
    UserRole.objects.create(
        user_id=user.id,
        user_email=user.email,
        role=editor_role,
    )
    return user
