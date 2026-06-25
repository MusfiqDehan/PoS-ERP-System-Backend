"""Tests for tenant product subscriptions."""

import pytest
from django.db import IntegrityError

from apps.billing.models import Package, SoftwareProduct, TenantProductSubscription


@pytest.mark.django_db
def test_subscription_uuid_primary_key(public_schema, tenant):
    product = SoftwareProduct.objects.create(name="Sortorium PoS", slug="sortorium-pos")
    package = Package.objects.create(
        software_product=product, name="Trial", slug="trial"
    )
    sub = TenantProductSubscription.objects.create(
        tenant=tenant,
        software_product=product,
        package=package,
        status=TenantProductSubscription.STATUS_TRIAL,
    )
    assert sub.id.version == 7


@pytest.mark.django_db
def test_one_active_subscription_per_product(public_schema, tenant):
    product = SoftwareProduct.objects.create(name="Sortorium PoS", slug="sortorium-pos")
    trial = Package.objects.create(
        software_product=product, name="Trial", slug="trial", is_trial=True
    )
    starter = Package.objects.create(
        software_product=product, name="Starter", slug="starter"
    )
    TenantProductSubscription.objects.create(
        tenant=tenant,
        software_product=product,
        package=trial,
        status=TenantProductSubscription.STATUS_ACTIVE,
    )
    with pytest.raises(IntegrityError):
        TenantProductSubscription.objects.create(
            tenant=tenant,
            software_product=product,
            package=starter,
            status=TenantProductSubscription.STATUS_ACTIVE,
        )


@pytest.mark.django_db
def test_cancelled_subscription_allows_new_active(public_schema, tenant):
    product = SoftwareProduct.objects.create(name="Sortorium PoS", slug="sortorium-pos")
    trial = Package.objects.create(software_product=product, name="Trial", slug="trial")
    starter = Package.objects.create(
        software_product=product, name="Starter", slug="starter"
    )
    TenantProductSubscription.objects.create(
        tenant=tenant,
        software_product=product,
        package=trial,
        status=TenantProductSubscription.STATUS_CANCELLED,
    )
    sub = TenantProductSubscription.objects.create(
        tenant=tenant,
        software_product=product,
        package=starter,
        status=TenantProductSubscription.STATUS_ACTIVE,
    )
    assert sub.package_id == starter.id
