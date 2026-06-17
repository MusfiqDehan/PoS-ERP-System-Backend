"""Tests for tenancy core models."""

import pytest

from apps.tenancy.models import Domain, Tenant


@pytest.mark.django_db
def test_tenant_uuid_primary_key():
    tenant = Tenant(
        schema_name="test_tenant",
        name="Test",
        slug="test",
        code="TEST",
    )
    tenant.save()
    assert tenant.id.version == 7


@pytest.mark.django_db
def test_tenant_allows_user_entry():
    tenant = Tenant.objects.create(
        schema_name="active_t",
        name="Active",
        slug="active",
        code="ACT",
        status="active",
        is_enabled=True,
    )
    assert tenant.allows_user_entry() is True

    tenant.status = "suspended"
    tenant.save(update_fields=["status"])
    assert tenant.allows_user_entry() is False


@pytest.mark.django_db
def test_domain_normalizes_hostname():
    tenant = Tenant.objects.create(
        schema_name="dom_t",
        name="Dom",
        slug="dom",
        code="DOM",
    )
    domain = Domain(domain="  EXAMPLE.COM  ", tenant=tenant, is_primary=True)
    domain.save()
    assert domain.domain == "example.com"
