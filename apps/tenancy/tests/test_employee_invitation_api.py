"""Tenant employee invitation service and API tests."""

import pytest
from django.contrib.auth import get_user_model
from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework.test import APIClient

from apps.access.models import UserRole
from apps.tenancy.models import Invitation
from apps.tenancy.services.employee_invitation import TenantInvitationService

User = get_user_model()


@pytest.mark.django_db
def test_issue_invitation_creates_stub_without_role(
    tenant, tenant_domain, tenant_schema, tenant_admin_user, seeded_tenant_roles
):
    invitation = TenantInvitationService.issue(
        inviter=tenant_admin_user,
        tenant=tenant,
        email="newcashier@test.com",
        full_name="New Cashier",
        role_slug="cashier",
    )
    user = User.objects.get(email="newcashier@test.com")
    assert user.password_set_at is None
    assert not UserRole.objects.filter(user_id=user.id).exists()
    assert invitation.token_type == Invitation.TOKEN_TYPE_EMPLOYEE_INVITE


@pytest.mark.django_db
def test_accept_invitation_assigns_role_and_enables_login(
    tenant, tenant_domain, tenant_schema, seeded_tenant_roles
):
    with schema_context(get_public_schema_name()):
        raw_token, invitation = Invitation.issue_token(
            token_type=Invitation.TOKEN_TYPE_EMPLOYEE_INVITE,
            tenant=tenant,
            email="accept@test.com",
            invitee_full_name="Accept User",
            subdomain=tenant.slug,
            company_name=tenant.name,
            metadata={
                "role_slug": "cashier",
                "branch_id": None,
                "domain": tenant_domain.domain,
            },
        )
    with schema_context(tenant.schema_name):
        user = User(email="accept@test.com", full_name="Accept User")
        user.set_unusable_password()
        user.save()

    result = TenantInvitationService.accept(
        raw_token=raw_token,
        password="NewPass123!",
    )
    assert "access" in result
    with schema_context(tenant.schema_name):
        assert UserRole.objects.filter(user_id=user.id, role__slug="cashier").exists()


@pytest.mark.django_db
def test_branch_manager_cannot_invite_admin(
    tenant, tenant_branch_manager, seeded_tenant_roles
):
    user, branch = tenant_branch_manager
    with pytest.raises(PermissionError):
        TenantInvitationService.issue(
            inviter=user,
            tenant=tenant,
            email="blocked@test.com",
            full_name="Blocked",
            role_slug="admin",
            branch_id=branch.id,
        )


@pytest.mark.django_db
def test_branch_manager_can_invite_cashier_to_own_branch(
    tenant, tenant_branch_manager, seeded_tenant_roles
):
    user, branch = tenant_branch_manager
    invitation = TenantInvitationService.issue(
        inviter=user,
        tenant=tenant,
        email="cashier2@test.com",
        full_name="Cashier Two",
        role_slug="cashier",
        branch_id=branch.id,
    )
    assert invitation.metadata["branch_id"] == str(branch.id)


@pytest.mark.django_db
def test_tenant_invitation_api_flow(
    tenant, tenant_domain, tenant_schema, tenant_admin_user, seeded_tenant_roles
):
    client = APIClient()
    client.force_authenticate(user=tenant_admin_user)

    create = client.post(
        "/api/v1/tenancy/invitations/",
        {
            "email": "invite@test.com",
            "full_name": "Invited",
            "role_slug": "cashier",
        },
        format="json",
        HTTP_HOST="test-tenant.localhost",
    )
    assert create.status_code == 201

    listing = client.get(
        "/api/v1/tenancy/invitations/",
        HTTP_HOST="test-tenant.localhost",
    )
    assert listing.status_code == 200

    public_client = APIClient()
    with schema_context(get_public_schema_name()):
        raw_token, _ = Invitation.issue_token(
            token_type=Invitation.TOKEN_TYPE_EMPLOYEE_INVITE,
            tenant=tenant,
            email="validate@test.com",
            invitee_full_name="Validate",
            subdomain=tenant.slug,
            company_name=tenant.name,
            metadata={"role_slug": "cashier", "domain": tenant_domain.domain},
        )

    validate = public_client.post(
        "/api/v1/tenancy/invitations/validate/",
        {"token": raw_token},
        format="json",
        HTTP_HOST="localhost",
    )
    assert validate.status_code == 200

    assert (
        client.post(
            "/api/v1/tenancy/users/",
            {},
            format="json",
            HTTP_HOST="test-tenant.localhost",
        ).status_code
        == 405
    )
