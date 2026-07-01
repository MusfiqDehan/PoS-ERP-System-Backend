"""Shared fixtures for inventory tests."""

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django_tenants.utils import get_public_schema_name, schema_context

from apps.access.models import Role, RolePermission, UserRole
from apps.branch.models import Branch
from apps.tenancy.models import Tenant
from shared.cache.helpers import invalidate_tenant_features

User = get_user_model()

INVENTORY_FEATURES = [
    "products",
    "inventory",
    "pos",
    "orders",
    "customers",
    "dashboard",
    "reports",
]


@pytest.fixture
def inventory_features(tenant, public_schema):
    features = {
        key: {"enabled": True, "force_enable": True} for key in INVENTORY_FEATURES
    }
    with schema_context(get_public_schema_name()):
        Tenant.objects.filter(pk=tenant.pk).update(features=features)
    invalidate_tenant_features(tenant.id)
    return tenant


@pytest.fixture
def tenant_admin(tenant_schema, inventory_features):
    connection.set_tenant(tenant_schema)
    user = User.objects.create_user(
        email="admin@inventory.test",
        password="TestPass1!",
        full_name="Inventory Admin",
    )
    role = Role.objects.create(name="Admin", slug="admin", is_system=True)
    UserRole.objects.create(user_id=user.id, user_email=user.email, role=role)
    return user


@pytest.fixture
def branch_manager_user(tenant_schema, inventory_features):
    connection.set_tenant(tenant_schema)
    branch = Branch.objects.create(name="Branch A", code="A")
    role = Role.objects.create(
        name="Branch Manager", slug="branch_manager", is_system=True
    )
    for feature_key in (
        "inventory",
        "products",
        "pos",
        "orders",
        "customers",
        "dashboard",
    ):
        RolePermission.objects.create(
            role=role, feature_key=feature_key, permission_level="edit"
        )
    user = User.objects.create_user(
        email="mgr@inventory.test",
        password="TestPass1!",
    )
    UserRole.objects.create(
        user_id=user.id,
        user_email=user.email,
        role=role,
        branch=branch,
    )
    return user, branch


@pytest.fixture
def cashier_user(tenant_schema, inventory_features):
    connection.set_tenant(tenant_schema)
    branch = Branch.objects.create(name="Cashier Branch", code="CASH")
    role = Role.objects.create(name="Cashier", slug="cashier", is_system=True)
    for feature_key in ("pos", "orders", "dashboard", "inventory"):
        RolePermission.objects.create(
            role=role, feature_key=feature_key, permission_level="edit"
        )
    user = User.objects.create_user(
        email="cashier@inventory.test",
        password="TestPass1!",
    )
    UserRole.objects.create(
        user_id=user.id,
        user_email=user.email,
        role=role,
        branch=branch,
    )
    return user, branch


@pytest.fixture
def second_branch(tenant_schema):
    connection.set_tenant(tenant_schema)
    return Branch.objects.create(name="Branch B", code="B")
