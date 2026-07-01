"""Tenant user management service and API tests."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.access.models import UserRole
from apps.tenancy.services.users import TenantUserService

User = get_user_model()


@pytest.mark.django_db
def test_replace_roles(tenant_schema, tenant_admin_user, seeded_tenant_roles):
    target = User.objects.create_user(
        email="target@test.com",
        password="TestPass1!",
        full_name="Target User",
    )
    UserRole.objects.create(
        user_id=target.id,
        user_email=target.email,
        role=seeded_tenant_roles["cashier"],
    )

    assignments = TenantUserService.replace_roles(
        actor=tenant_admin_user,
        user=target,
        assignments=[{"role_slug": "cashier"}],
    )
    assert len(assignments) == 1
    assert assignments[0]["role_slug"] == "cashier"


@pytest.mark.django_db
def test_cannot_demote_last_admin(
    tenant_schema, tenant_admin_user, seeded_tenant_roles
):
    with pytest.raises(ValueError, match="last admin"):
        TenantUserService.replace_roles(
            actor=tenant_admin_user,
            user=tenant_admin_user,
            assignments=[{"role_slug": "cashier"}],
        )


@pytest.mark.django_db
def test_deactivate_user(tenant_schema, tenant_admin_user, seeded_tenant_roles):
    target = User.objects.create_user(
        email="deact@test.com",
        password="TestPass1!",
    )
    UserRole.objects.create(
        user_id=target.id,
        user_email=target.email,
        role=seeded_tenant_roles["cashier"],
    )
    TenantUserService.deactivate(actor=tenant_admin_user, user=target)
    target.refresh_from_db()
    assert target.is_active is False


@pytest.mark.django_db
def test_tenant_user_detail_and_roles_api(
    tenant, tenant_domain, tenant_schema, tenant_admin_user, seeded_tenant_roles
):
    target = User.objects.create_user(
        email="detail@test.com",
        password="TestPass1!",
        full_name="Detail User",
    )
    UserRole.objects.create(
        user_id=target.id,
        user_email=target.email,
        role=seeded_tenant_roles["cashier"],
    )

    client = APIClient()
    client.force_authenticate(user=tenant_admin_user)

    detail = client.get(
        f"/api/v1/tenancy/users/{target.id}/",
        HTTP_HOST="test-tenant.localhost",
    )
    assert detail.status_code == 200
    assert detail.data["data"]["email"] == "detail@test.com"

    patch_roles = client.patch(
        f"/api/v1/tenancy/users/{target.id}/roles/",
        {"assignments": [{"role_slug": "cashier"}]},
        format="json",
        HTTP_HOST="test-tenant.localhost",
    )
    assert patch_roles.status_code == 200

    users_list = client.get(
        "/api/v1/tenancy/users/",
        HTTP_HOST="test-tenant.localhost",
    )
    assert users_list.status_code == 200
    assert "pagination" in users_list.data["data"]
