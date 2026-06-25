"""Service tests for tenant RBAC permission resolution."""

import pytest
from django.db import connection
from django_tenants.utils import schema_context

from apps.access.models import Role, RolePermission, UserRole
from apps.access.services.permissions import get_user_permission_map


@pytest.mark.django_db
def test_tenant_admin_role_grants_full_permission(tenant, tenant_user):
    from apps.access.services.permissions import get_user_permission_level

    with schema_context(tenant.schema_name):
        connection.set_tenant(tenant)
        admin_role = Role.objects.create(name="Admin", slug="admin", is_system=True)
        UserRole.objects.create(
            user_id=tenant_user.id, user_email=tenant_user.email, role=admin_role
        )
        assert get_user_permission_level(tenant_user, "dashboard") == "full"


@pytest.mark.django_db
def test_user_permission_map_aggregates_highest_level(tenant, tenant_user):
    with schema_context(tenant.schema_name):
        connection.set_tenant(tenant)
        role_a = Role.objects.create(name="A", slug="a")
        role_b = Role.objects.create(name="B", slug="b")
        RolePermission.objects.create(
            role=role_a, feature_key="dashboard", permission_level="view"
        )
        RolePermission.objects.create(
            role=role_b, feature_key="dashboard", permission_level="edit"
        )
        UserRole.objects.create(
            user_id=tenant_user.id, user_email=tenant_user.email, role=role_a
        )
        UserRole.objects.create(
            user_id=tenant_user.id, user_email=tenant_user.email, role=role_b
        )

        perm_map = get_user_permission_map(tenant_user)
        assert perm_map["dashboard"] == "edit"
