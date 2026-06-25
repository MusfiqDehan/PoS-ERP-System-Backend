"""Tests for subscription invoice PDF and admin views."""

import pytest
from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework.test import APIClient

from apps.billing.models import TenantSubscriptionInvoice
from apps.billing.services.invoice_pdf import render_subscription_invoice_pdf


@pytest.mark.django_db
def test_render_subscription_invoice_pdf(public_schema, tenant):
    invoice = TenantSubscriptionInvoice.objects.create(
        tenant=tenant,
        software_product_slug="sortorium-pos",
        package_slug="trial",
        tran_id="SUB-TEST-PDF-001",
        amount=29,
        currency="USD",
        status=TenantSubscriptionInvoice.STATUS_SUCCESS,
        billing_cycle="monthly",
        gateway_slug="manual",
    )
    pdf_bytes = render_subscription_invoice_pdf(invoice, generated_by="Admin")
    assert pdf_bytes.startswith(b"%PDF")


@pytest.mark.django_db
def test_tenant_admin_can_list_invoices(
    tenant, tenant_domain, tenant_schema, public_schema
):
    from apps.access.models import Role, UserRole
    from django.contrib.auth import get_user_model

    User = get_user_model()
    with schema_context(get_public_schema_name()):
        TenantSubscriptionInvoice.objects.create(
            tenant=tenant,
            software_product_slug="sortorium-pos",
            package_slug="trial",
            tran_id="SUB-LIST-001",
            amount=0,
            currency="USD",
            status=TenantSubscriptionInvoice.STATUS_SUCCESS,
            billing_cycle="monthly",
        )
    with schema_context(tenant.schema_name):
        admin = User.objects.create_user(email="admin@test.com", password="TestPass1!")
        role = Role.objects.create(name="Admin", slug="admin", is_system=True)
        UserRole.objects.create(user_id=admin.id, user_email=admin.email, role=role)

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get(
        "/api/v1/billing/subscription/invoices/",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 200
    assert response.data["success"] is True
    assert len(response.data["data"]["items"]) == 1


@pytest.mark.django_db
def test_tenant_admin_can_download_invoice_pdf(
    tenant, tenant_domain, tenant_schema, public_schema
):
    from apps.access.models import Role, UserRole
    from django.contrib.auth import get_user_model

    User = get_user_model()
    with schema_context(get_public_schema_name()):
        invoice = TenantSubscriptionInvoice.objects.create(
            tenant=tenant,
            software_product_slug="sortorium-pos",
            package_slug="trial",
            tran_id="SUB-PDF-001",
            amount=10,
            currency="USD",
            status=TenantSubscriptionInvoice.STATUS_SUCCESS,
            billing_cycle="monthly",
        )
    with schema_context(tenant.schema_name):
        admin = User.objects.create_user(email="admin@test.com", password="TestPass1!")
        role = Role.objects.create(name="Admin", slug="admin", is_system=True)
        UserRole.objects.create(user_id=admin.id, user_email=admin.email, role=role)

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get(
        f"/api/v1/billing/subscription/invoices/{invoice.id}/pdf/",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


@pytest.mark.django_db
def test_platform_admin_lists_subscription_invoices(public_schema, tenant):
    from apps.tenancy.models import User

    admin = User.objects.create_superadmin(
        email="platform@test.com", password="TestPass1!"
    )
    TenantSubscriptionInvoice.objects.create(
        tenant=tenant,
        software_product_slug="sortorium-pos",
        package_slug="trial",
        tran_id="SUB-PLATFORM-001",
        amount=29,
        currency="USD",
        status=TenantSubscriptionInvoice.STATUS_SUCCESS,
        billing_cycle="monthly",
    )

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get(
        "/api/v1/billing/subscription/invoices/",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 200
    assert response.data["success"] is True
    assert len(response.data["data"]["items"]) >= 1
    assert "stats" in response.data["data"]
