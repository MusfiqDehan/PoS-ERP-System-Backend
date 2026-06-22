"""Tests for branch-scoped tenant user listing."""

import pytest
from django.db import connection
from django_tenants.utils import schema_context
from rest_framework.test import APIClient

from apps.access.models import Role, UserRole
from apps.branch.models import Branch


@pytest.mark.django_db
def test_branch_manager_sees_only_branch_users(tenant, tenant_domain, tenant_schema):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    with schema_context(tenant.schema_name):
        connection.set_tenant(tenant)
        admin = User.objects.create_user(email="admin@test.com", password="TestPass1!")
        manager = User.objects.create_user(email="mgr@test.com", password="TestPass1!")
        staff_a = User.objects.create_user(
            email="staff-a@test.com", password="TestPass1!"
        )
        staff_b = User.objects.create_user(
            email="staff-b@test.com", password="TestPass1!"
        )
        admin_role = Role.objects.create(name="Admin", slug="admin", is_system=True)
        mgr_role = Role.objects.create(
            name="Branch Manager", slug="branch_manager", is_system=True
        )
        branch_a = Branch.objects.create(name="A", code="A")
        branch_b = Branch.objects.create(name="B", code="B")
        UserRole.objects.create(
            user_id=admin.id, user_email=admin.email, role=admin_role
        )
        UserRole.objects.create(
            user_id=manager.id, user_email=manager.email, role=mgr_role, branch=branch_a
        )
        UserRole.objects.create(
            user_id=staff_a.id, user_email=staff_a.email, role=mgr_role, branch=branch_a
        )
        UserRole.objects.create(
            user_id=staff_b.id, user_email=staff_b.email, role=mgr_role, branch=branch_b
        )

    client = APIClient()
    client.force_authenticate(user=manager)
    response = client.get("/api/v1/tenancy/users/", HTTP_HOST="test-tenant.localhost")
    assert response.status_code == 200
    emails = {row["email"] for row in response.data["data"]["items"]}
    assert "staff-a@test.com" in emails
    assert "staff-b@test.com" not in emails
    assert "admin@test.com" not in emails


@pytest.mark.django_db
def test_tenant_admin_can_filter_users_by_branch(tenant, tenant_domain, tenant_schema):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    with schema_context(tenant.schema_name):
        connection.set_tenant(tenant)
        admin = User.objects.create_user(email="admin@test.com", password="TestPass1!")
        user_a = User.objects.create_user(
            email="user-a@test.com", password="TestPass1!"
        )
        user_b = User.objects.create_user(
            email="user-b@test.com", password="TestPass1!"
        )
        admin_role = Role.objects.create(name="Admin", slug="admin", is_system=True)
        cashier = Role.objects.create(name="Cashier", slug="cashier", is_system=True)
        branch_a = Branch.objects.create(name="A", code="A")
        branch_b = Branch.objects.create(name="B", code="B")
        UserRole.objects.create(
            user_id=admin.id, user_email=admin.email, role=admin_role
        )
        UserRole.objects.create(
            user_id=user_a.id, user_email=user_a.email, role=cashier, branch=branch_a
        )
        UserRole.objects.create(
            user_id=user_b.id, user_email=user_b.email, role=cashier, branch=branch_b
        )

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get(
        f"/api/v1/tenancy/users/?branch={branch_a.id}",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 200
    emails = {row["email"] for row in response.data["data"]["items"]}
    assert emails == {"user-a@test.com"}
