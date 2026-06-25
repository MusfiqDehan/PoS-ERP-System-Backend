"""Tests for payment gateway factory and tenant gateway models."""

import pytest
from django.db import connection
from django_tenants.utils import schema_context

from apps.billing.models import PaymentGateway, TenantPaymentGateway
from apps.billing.services.factory import get_gateway


@pytest.mark.django_db
def test_get_gateway_returns_sslcommerz_service(public_schema):
    PaymentGateway.objects.create(
        slug="sslcommerz",
        name="SSLCommerz",
        platform_credentials={"store_id": "test", "store_password": "secret"},
        is_default_for_subscriptions=True,
    )
    svc = get_gateway(
        "sslcommerz",
        credentials={"store_id": "test", "store_password": "secret"},
        is_sandbox=True,
        success_url="https://example.com/success",
        fail_url="https://example.com/fail",
        cancel_url="https://example.com/cancel",
        ipn_url="https://example.com/ipn",
    )
    assert svc.__class__.__name__ == "SSLCommerzService"


@pytest.mark.django_db
def test_get_gateway_unknown_slug_raises(public_schema):
    with pytest.raises(ValueError, match="Unknown payment gateway"):
        get_gateway(
            "unknown",
            credentials={},
            is_sandbox=True,
            success_url="https://example.com/success",
            fail_url="https://example.com/fail",
            cancel_url="https://example.com/cancel",
            ipn_url="https://example.com/ipn",
        )


@pytest.mark.django_db
def test_tenant_payment_gateway_crud(tenant, tenant_schema):
    with schema_context(tenant.schema_name):
        connection.set_tenant(tenant)
        row = TenantPaymentGateway.objects.create(
            gateway_slug="sslcommerz",
            credentials={"store_id": "tenant-store"},
            is_sandbox=True,
        )
        assert row.is_active is True
        row.credentials = {"store_id": "updated"}
        row.save(update_fields=["credentials"])
        assert TenantPaymentGateway.objects.filter(gateway_slug="sslcommerz").exists()
