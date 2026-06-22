"""Tests for subscription billing service and payment callbacks."""

import pytest
from rest_framework.test import APIClient

from apps.billing.models import (
    Package,
    SoftwareProduct,
    TenantProductSubscription,
    TenantSubscriptionInvoice,
)
from apps.billing.services.subscription_billing import initiate_for_tenant


class _FakeRequest:
    scheme = "https"

    def get_host(self):
        return "test-tenant.localhost"


@pytest.mark.django_db
def test_free_package_activates_subscription_immediately(public_schema, tenant):
    product = SoftwareProduct.objects.create(name="Sortorium PoS", slug="sortorium-pos")
    package = Package.objects.create(
        software_product=product,
        name="Free Trial",
        slug="trial",
        price_monthly=0,
        price_yearly=0,
        is_public=True,
    )

    gateway_url, tran_id, invoice = initiate_for_tenant(
        tenant=tenant,
        package_slug="trial",
        billing_cycle="monthly",
        request=_FakeRequest(),
    )

    assert gateway_url == ""
    assert invoice.status == TenantSubscriptionInvoice.STATUS_SUCCESS
    sub = TenantProductSubscription.objects.get(tenant=tenant, software_product=product)
    assert sub.status == TenantProductSubscription.STATUS_ACTIVE
    assert sub.package_id == package.id
    assert tran_id.startswith("TRIAL-")


@pytest.mark.django_db
def test_subscription_ipn_marks_invoice_success(public_schema, tenant, tenant_domain):
    product = SoftwareProduct.objects.create(name="Sortorium PoS", slug="sortorium-pos")
    Package.objects.create(
        software_product=product,
        name="Starter",
        slug="starter",
        price_monthly=29,
        is_public=True,
    )
    invoice = TenantSubscriptionInvoice.objects.create(
        tenant=tenant,
        software_product_slug=product.slug,
        package_slug="starter",
        tran_id="SUB-TEST-ABC123",
        amount=29,
        currency="USD",
        status=TenantSubscriptionInvoice.STATUS_PENDING,
        billing_cycle="monthly",
        gateway_slug="sslcommerz",
    )

    client = APIClient()
    response = client.post(
        "/api/v1/billing/subscription/ipn/",
        {"tran_id": invoice.tran_id, "status": "VALID", "val_id": "VAL123"},
        format="json",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 200
    invoice.refresh_from_db()
    assert invoice.status == TenantSubscriptionInvoice.STATUS_SUCCESS
    sub = TenantProductSubscription.objects.filter(tenant=tenant).first()
    assert sub is not None
    assert sub.status == TenantProductSubscription.STATUS_ACTIVE
