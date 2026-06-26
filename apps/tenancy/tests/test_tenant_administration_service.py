"""Service-layer tests for tenant administration helpers."""

import uuid

import pytest

from apps.tenancy.models import Tenant
from apps.tenancy.services import TenantAdministrationService


@pytest.mark.django_db
def test_list_tenants_queryset_orders_by_name(tenant, public_schema):
    Tenant.objects.create(
        schema_name="alpha_tenant",
        name="Alpha Tenant",
        slug="alpha-tenant",
        code="ALPHA",
        status="active",
    )
    names = list(
        TenantAdministrationService.list_tenants_queryset().values_list(
            "name", flat=True
        )
    )
    assert "Alpha Tenant" in names
    assert "Test Tenant" in names
    assert names == sorted(names)


@pytest.mark.django_db
def test_list_tenants_queryset_prefetches_domains(tenant, tenant_domain, public_schema):
    qs = TenantAdministrationService.list_tenants_queryset()
    row = qs.get(pk=tenant.id)
    assert hasattr(row, "_prefetched_objects_cache")
    assert "domains" in row._prefetched_objects_cache


@pytest.mark.django_db
def test_get_tenant_feature_overrides_returns_map(tenant, public_schema):
    tenant.features = {"pos.offline": True}
    tenant.save(update_fields=["features"])

    result = TenantAdministrationService.get_tenant_feature_overrides(tenant.id)

    assert result == {"pos.offline": True}


@pytest.mark.django_db
def test_get_tenant_feature_overrides_empty_dict(tenant, public_schema):
    tenant.features = {}
    tenant.save(update_fields=["features"])

    result = TenantAdministrationService.get_tenant_feature_overrides(tenant.id)

    assert result == {}


@pytest.mark.django_db
def test_get_tenant_feature_overrides_unknown_tenant(public_schema):
    result = TenantAdministrationService.get_tenant_feature_overrides(uuid.uuid4())

    assert result is None


@pytest.mark.django_db
def test_patch_tenant_feature_overrides_for_admin_merges(tenant, public_schema):
    tenant.features = {"dashboard": True}
    tenant.save(update_fields=["features"])

    merged = TenantAdministrationService.patch_tenant_feature_overrides_for_admin(
        tenant.id,
        {"pos.offline": True},
    )

    assert merged == {"dashboard": True, "pos.offline": True}
    tenant.refresh_from_db()
    assert tenant.features == merged


@pytest.mark.django_db
def test_patch_tenant_feature_overrides_for_admin_unknown_tenant(public_schema):
    result = TenantAdministrationService.patch_tenant_feature_overrides_for_admin(
        uuid.uuid4(),
        {"pos.offline": True},
    )

    assert result is None
