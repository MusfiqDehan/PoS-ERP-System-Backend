"""Platform invitation and password-reset URL generation tests."""

import re

import pytest
from django.test import override_settings
from django_tenants.utils import get_public_schema_name, schema_context

from apps.platform_owner.services.invitation import PlatformInvitationService
from apps.platform_owner.services.password import PlatformPasswordService
from apps.tenancy.models import EmailQueue, Invitation, PlatformRole
from apps.tenancy.services.invitation import InvitationService


@pytest.mark.django_db
@override_settings(
    PUBLIC_FRONTEND_URL="https://sortorium.com",
    TENANT_FRONTEND_BASE_DOMAIN="sortorium.com",
)
def test_platform_password_reset_email_uses_apex_frontend_url(
    public_schema, platform_superadmin
):
    PlatformPasswordService.request_reset(email=platform_superadmin.email)

    with schema_context(get_public_schema_name()):
        row = (
            EmailQueue.objects.filter(
                to_email=platform_superadmin.email,
                purpose=EmailQueue.PURPOSE_PASSWORD_RESET,
            )
            .order_by("-created_at")
            .first()
        )
        assert row is not None
        match = re.search(
            r"https://sortorium\.com/reset-password\?token=", row.text_body
        )
        assert match is not None
        assert "platform.sortorium.com" not in row.text_body


@pytest.mark.django_db
@override_settings(
    PUBLIC_FRONTEND_URL="https://sortorium.com",
    TENANT_FRONTEND_BASE_DOMAIN="sortorium.com",
)
def test_platform_invite_email_uses_apex_frontend_url(
    public_schema, platform_superadmin
):
    PlatformInvitationService.issue(
        inviter=platform_superadmin,
        email="apex-invite@test.com",
        full_name="Apex Invite",
        role_slug="platform_manager",
    )

    with schema_context(get_public_schema_name()):
        row = (
            EmailQueue.objects.filter(
                to_email="apex-invite@test.com",
                purpose=EmailQueue.PURPOSE_PLATFORM_INVITE,
            )
            .order_by("-created_at")
            .first()
        )
        assert row is not None
        assert "https://sortorium.com/accept-platform-invite?token=" in row.text_body
        assert "platform.sortorium.com" not in row.text_body
        assert "Subdomain:" not in row.text_body


@pytest.mark.django_db
@override_settings(
    PUBLIC_FRONTEND_URL="https://sortorium.com",
    TENANT_FRONTEND_BASE_DOMAIN="sortorium.com",
)
def test_build_token_url_uses_apex_for_legacy_platform_subdomain(public_schema):
    role = PlatformRole.objects.get(slug="platform_manager")
    raw_token, invitation = Invitation.issue_token(
        token_type=Invitation.TOKEN_TYPE_PLATFORM_INVITE,
        email="legacy@test.com",
        invitee_full_name="Legacy",
        subdomain="platform",
        company_name="Sortorium Platform",
        platform_role=role,
    )

    url = InvitationService.build_token_url(invitation, raw_token)
    assert url.startswith("https://sortorium.com/accept-platform-invite?token=")
    assert "platform.sortorium.com" not in url
