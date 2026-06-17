"""Service-layer tests for tenancy."""

import pytest
from django.core.management import call_command
from django.core import mail
from django.db import connection
from django_tenants.utils import schema_context

from apps.access.models import Role, RolePermission, UserRole
from apps.tenancy.models import EmailQueue, Invitation, TenantAuditLog
from apps.tenancy.services import (
    AuthService,
    EmailService,
    InvitationService,
    PasswordService,
    PlatformPermissionService,
    TenantAuditService,
    TenantRegistrationService,
)


@pytest.mark.django_db
def test_validate_subdomain_rejects_invalid():
    with pytest.raises(ValueError):
        TenantRegistrationService.validate_subdomain("ab")


@pytest.mark.django_db
def test_subdomain_available_true(public_schema):
    assert TenantRegistrationService.subdomain_available("newshop") is True


@pytest.mark.django_db
def test_start_self_registration_enqueues_email(public_schema):
    raw, invitation, domain = TenantRegistrationService.start_self_registration(
        subdomain="newshop",
        company_name="New Shop",
        admin_email="owner@newshop.com",
    )
    assert raw
    assert invitation.email == "owner@newshop.com"
    assert domain.endswith("newshop.localhost")
    assert EmailQueue.objects.filter(purpose=EmailQueue.PURPOSE_VERIFICATION).exists()


@pytest.mark.django_db
def test_auth_login_returns_tenant_schema_claim(tenant, tenant_domain, tenant_user):
    tokens = AuthService.login(
        email="user@test.com",
        password="TestPass1!",
        domain="test-tenant.localhost",
    )
    assert tokens.access
    assert tokens.refresh
    assert tokens.tenant.schema_name == "test_tenant"


@pytest.mark.django_db
def test_auth_login_invalid_credentials(tenant, tenant_domain, tenant_user):
    with pytest.raises(ValueError, match="Invalid credentials"):
        AuthService.login(
            email="user@test.com",
            password="WrongPass1!",
            domain="test-tenant.localhost",
        )


@pytest.mark.django_db
def test_email_service_enqueue_verification(public_schema):
    from django.utils import timezone

    row = EmailService.enqueue_verification(
        to_email="verify@example.com",
        company_name="Co",
        subdomain="co",
        verification_url="http://localhost/verify",
        expires_at=timezone.now(),
    )
    assert row.purpose == EmailQueue.PURPOSE_VERIFICATION
    assert row.to_email == "verify@example.com"


@pytest.mark.django_db
def test_audit_service_log(public_schema, tenant, rf):
    request = rf.get("/")
    request.META["REMOTE_ADDR"] = "127.0.0.1"
    request.user = type("Anon", (), {"is_authenticated": False})()
    log = TenantAuditService.log(
        request=request,
        action="tenant.test",
        tenant=tenant,
        metadata={"ok": True},
    )
    assert TenantAuditLog.objects.filter(pk=log.pk).exists()


@pytest.mark.django_db
def test_platform_permission_superadmin_full_map(public_schema):
    from apps.tenancy.models import User

    admin = User.objects.create_superuser(email="admin@test.com", password="TestPass1!")
    perm_map = PlatformPermissionService.get_permission_map(admin)
    assert perm_map
    assert all(level == "full" for level in perm_map.values())


@pytest.mark.django_db
def test_invitation_service_validate_token(public_schema, tenant):
    raw, invitation = Invitation.issue_token(
        token_type=Invitation.TOKEN_TYPE_INVITATION,
        email="invite@example.com",
        subdomain="acme",
        company_name="Acme",
        tenant=tenant,
    )
    assert InvitationService.validate_token(raw) == invitation
    assert InvitationService.validate_token("invalid-token") is None


@pytest.mark.django_db
def test_password_service_rejects_invalid_token(public_schema):
    with pytest.raises(ValueError, match="Invalid or expired token"):
        PasswordService.setup_password(raw_token="not-a-token", password="NewPass1!")


@pytest.mark.django_db
def test_process_email_queue_command(public_schema):
    EmailQueue.objects.create(
        to_email="recipient@example.com",
        subject="Test",
        text_body="Hello",
        html_body="<p>Hello</p>",
        purpose=EmailQueue.PURPOSE_VERIFICATION,
    )
    mail.outbox.clear()
    call_command("process_email_queue")
    row = EmailQueue.objects.get()
    assert row.status == EmailQueue.STATUS_SENT
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_tenant_permission_resolution(tenant, tenant_user):
    with schema_context(tenant.schema_name):
        connection.set_tenant(tenant)
        role = Role.objects.create(name="Viewer", slug="viewer")
        RolePermission.objects.create(
            role=role, feature_key="permissions", permission_level="view"
        )
        UserRole.objects.create(
            user_id=tenant_user.id,
            user_email=tenant_user.email,
            role=role,
        )
        from apps.access.services.permissions import get_user_permission_level, user_can

        assert get_user_permission_level(tenant_user, "permissions") == "view"
        assert user_can(tenant_user, "permissions", "view") is True
        assert user_can(tenant_user, "permissions", "edit") is False
