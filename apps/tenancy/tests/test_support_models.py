"""Tests for Invitation, EmailQueue, and TenantAuditLog models."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.tenancy.models import EmailQueue, Invitation, TenantAuditLog


@pytest.mark.django_db
def test_invitation_issue_token(public_schema, tenant):
    raw, invitation = Invitation.issue_token(
        token_type=Invitation.TOKEN_TYPE_VERIFICATION,
        email="admin@example.com",
        subdomain="acme",
        company_name="Acme Inc",
        tenant=tenant,
        ttl_minutes=30,
    )
    assert raw
    assert invitation.token_hash
    assert invitation.is_usable is True
    assert Invitation.from_raw_token(raw) == invitation


@pytest.mark.django_db
def test_invitation_expired(public_schema):
    invitation = Invitation.objects.create(
        token_type=Invitation.TOKEN_TYPE_INVITATION,
        email="x@example.com",
        subdomain="x",
        company_name="X",
        token_hash="abc",
        expires_at=timezone.now() - timedelta(minutes=1),
    )
    assert invitation.is_expired is True
    assert invitation.is_usable is False


@pytest.mark.django_db
def test_email_queue_defaults(public_schema, tenant):
    row = EmailQueue.objects.create(
        tenant=tenant,
        to_email="user@example.com",
        subject="Hello",
        purpose=EmailQueue.PURPOSE_INVITATION,
    )
    assert row.status == EmailQueue.STATUS_PENDING
    assert row.attempts == 0


@pytest.mark.django_db
def test_tenant_audit_log(public_schema, tenant):
    log = TenantAuditLog.objects.create(
        tenant=tenant,
        actor_email="admin@example.com",
        action="tenant.updated",
        target_type="tenant",
        target_id=str(tenant.id),
    )
    assert log.action == "tenant.updated"
    assert log.id.version == 7
