"""API tests for billing catalog endpoints."""

import pytest
from rest_framework.test import APIClient

from apps.billing.models import SoftwareProduct
from apps.tenancy.models import User


@pytest.mark.django_db
def test_packages_list_requires_auth(public_schema):
    client = APIClient()
    response = client.get("/api/v1/billing/packages/", HTTP_HOST="localhost")
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_packages_list_platform_admin(public_schema):
    admin = User.objects.create_superadmin(
        email="platform@test.com", password="TestPass1!"
    )
    product = SoftwareProduct.objects.create(name="Sortorium PoS", slug="sortorium-pos")
    from apps.billing.models import Package

    Package.objects.create(software_product=product, name="Trial", slug="trial")

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get("/api/v1/billing/packages/", HTTP_HOST="localhost")
    assert response.status_code == 200
    assert response.data["success"] is True
    assert len(response.data["data"]) >= 1


@pytest.mark.django_db
def test_products_list_platform_admin(public_schema):
    admin = User.objects.create_superadmin(
        email="platform@test.com", password="TestPass1!"
    )
    SoftwareProduct.objects.create(name="Sortorium PoS", slug="sortorium-pos")

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get("/api/v1/billing/products/", HTTP_HOST="localhost")
    assert response.status_code == 200
    assert response.data["success"] is True
