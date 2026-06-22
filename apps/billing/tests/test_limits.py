"""Tests for subscription-derived limit aggregation."""

import pytest
from django.db import connection
from django_tenants.utils import get_public_schema_name, schema_context

from apps.billing.models import (
    Package,
    PackageRoleLimit,
    SoftwareProduct,
    TenantProductSubscription,
)
from apps.billing.services.limits_sync import compute_effective_limits
from apps.branch.models import Branch
from shared.tenancy.limits import total_capacity_exceeded


@pytest.mark.django_db
def test_compute_effective_limits_takes_max_across_subscriptions(public_schema, tenant):
    pos = SoftwareProduct.objects.create(name="Sortorium PoS", slug="sortorium-pos")
    crm = SoftwareProduct.objects.create(name="CRM", slug="crm")
    pos_pkg = Package.objects.create(
        software_product=pos, name="Trial", slug="trial", max_branches=1, max_users=5
    )
    crm_pkg = Package.objects.create(
        software_product=crm,
        name="CRM Basic",
        slug="crm-basic",
        max_branches=3,
        max_users=10,
    )
    TenantProductSubscription.objects.create(
        tenant=tenant,
        software_product=pos,
        package=pos_pkg,
        status=TenantProductSubscription.STATUS_ACTIVE,
    )
    TenantProductSubscription.objects.create(
        tenant=tenant,
        software_product=crm,
        package=crm_pkg,
        status=TenantProductSubscription.STATUS_ACTIVE,
    )

    limits = compute_effective_limits(tenant)
    assert limits.max_branches == 3
    assert limits.max_users == 10


@pytest.mark.django_db
def test_per_role_limits_aggregate_max(public_schema, tenant):
    product = SoftwareProduct.objects.create(name="Sortorium PoS", slug="sortorium-pos")
    package = Package.objects.create(
        software_product=product, name="Starter", slug="starter"
    )
    PackageRoleLimit.objects.create(package=package, role_slug="cashier", max_users=2)
    PackageRoleLimit.objects.create(package=package, role_slug="manager", max_users=1)
    TenantProductSubscription.objects.create(
        tenant=tenant,
        software_product=product,
        package=package,
        status=TenantProductSubscription.STATUS_ACTIVE,
    )

    limits = compute_effective_limits(tenant)
    assert limits.per_role_limits["cashier"] == 2
    assert limits.per_role_limits["manager"] == 1


@pytest.mark.django_db
def test_branch_limit_enforcement_uses_subscription(
    public_schema, tenant, tenant_schema
):
    with schema_context(get_public_schema_name()):
        product = SoftwareProduct.objects.create(
            name="Sortorium PoS", slug="sortorium-pos"
        )
        package = Package.objects.create(
            software_product=product, name="Trial", slug="trial", max_branches=1
        )
        TenantProductSubscription.objects.create(
            tenant=tenant,
            software_product=product,
            package=package,
            status=TenantProductSubscription.STATUS_ACTIVE,
        )

    with schema_context(tenant.schema_name):
        connection.set_tenant(tenant)
        Branch.objects.create(name="Only", code="ONLY")
        limit_error = total_capacity_exceeded(
            Branch.objects, "max_branches", limit_type="branches"
        )
        assert limit_error is not None
        assert limit_error["code"] == "LIMIT_EXCEEDED"
        assert limit_error["limit"] == 1
        assert limit_error["current"] == 1
