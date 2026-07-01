"""Platform invitation service and API tests."""

import pytest
from django.contrib.auth import get_user_model

from apps.platform_owner.services.auth import PlatformAuthService
from apps.platform_owner.services.invitation import PlatformInvitationService
from apps.tenancy.models import Invitation, PlatformRole, PlatformUserRole

User = get_user_model()


@pytest.mark.django_db
def test_issue_invitation_creates_stub_without_role(public_schema, platform_superadmin):
    invitation = PlatformInvitationService.issue(
        inviter=platform_superadmin,
        email="newadmin@test.com",
        full_name="New Admin",
        role_slug="platform_manager",
    )
    user = User.objects.get(email="newadmin@test.com", tenant__isnull=True)
    assert user.password_set_at is None
    assert not PlatformUserRole.objects.filter(user=user).exists()
    assert invitation.token_type == Invitation.TOKEN_TYPE_PLATFORM_INVITE


@pytest.mark.django_db
def test_accept_invitation_assigns_role_and_enables_login(
    public_schema, platform_superadmin
):
    role = PlatformRole.objects.get(slug="support_agent")
    raw_token, _invitation = Invitation.issue_token(
        token_type=Invitation.TOKEN_TYPE_PLATFORM_INVITE,
        email="accept2@test.com",
        invitee_full_name="Accept2",
        subdomain="",
        company_name="Sortorium Platform",
        platform_role=role,
    )
    user = User(email="accept2@test.com", tenant=None, full_name="Accept2")
    user.set_unusable_password()
    user.save()

    result = PlatformInvitationService.accept(
        raw_token=raw_token,
        password="NewPass123!",
    )
    assert "access" in result
    assert "support_agent" in result["user"]["platform_roles"]

    tokens = PlatformAuthService.login(
        email="accept2@test.com",
        password="NewPass123!",
    )
    assert tokens.access


@pytest.mark.django_db
def test_invitation_api_flow(public_schema, platform_auth_client):
    create = platform_auth_client.post(
        "/api/v1/platform-owner/invitations/",
        {
            "email": "invite@test.com",
            "full_name": "Invited",
            "role_slug": "platform_manager",
        },
        format="json",
        HTTP_HOST="localhost",
    )
    assert create.status_code == 201

    listing = platform_auth_client.get(
        "/api/v1/platform-owner/invitations/",
        HTTP_HOST="localhost",
    )
    assert listing.status_code == 200

    assert (
        platform_auth_client.post(
            "/api/v1/platform-owner/users/",
            {},
            format="json",
            HTTP_HOST="localhost",
        ).status_code
        == 405
    )
