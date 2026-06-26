"""API tests for public billing catalog endpoints."""

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.billing.models import Package, SoftwareProduct
from apps.tenancy.models import Feature
from shared.cache.helpers import public_packages_key


@pytest.fixture
def public_product(public_schema):
    return SoftwareProduct.objects.create(name="Sortorium PoS", slug="sortorium-pos")


@pytest.fixture
def public_packages(public_product, public_schema):
    free = Package.objects.create(
        software_product=public_product,
        name="Free",
        slug="free",
        description="Starter plan",
        price_monthly=0,
        price_yearly=0,
        is_public=True,
        sort_order=0,
    )
    pro = Package.objects.create(
        software_product=public_product,
        name="Pro",
        slug="pro",
        description="Growth plan",
        price_monthly=29,
        price_yearly=290,
        is_public=True,
        sort_order=1,
    )
    Package.objects.create(
        software_product=public_product,
        name="Internal",
        slug="internal",
        is_public=False,
        sort_order=2,
    )
    feature = Feature.objects.create(key="dashboard", name="Dashboard")
    from apps.billing.models import PackageFeature

    PackageFeature.objects.create(package=pro, feature=feature)
    return {"free": free, "pro": pro}


@pytest.mark.django_db
def test_public_packages_list_no_auth(public_schema, public_packages):
    client = APIClient()
    response = client.get(
        "/api/v1/billing/public/packages/", HTTP_HOST="localhost"
    )
    assert response.status_code == 200
    assert response.data["success"] is True
    items = response.data["data"]["items"]
    slugs = {item["slug"] for item in items}
    assert slugs == {"free", "pro"}
    pro = next(item for item in items if item["slug"] == "pro")
    assert pro["price_monthly"] == "29.00"
    assert len(pro["features"]) == 1
    assert pro["features"][0]["key"] == "dashboard"


@pytest.mark.django_db
def test_public_packages_excludes_inactive(public_schema, public_product):
    Package.objects.create(
        software_product=public_product,
        name="Retired",
        slug="retired",
        is_public=True,
        is_active=False,
    )
    client = APIClient()
    response = client.get(
        "/api/v1/billing/public/packages/", HTTP_HOST="localhost"
    )
    assert response.status_code == 200
    assert response.data["data"]["items"] == []


@pytest.mark.django_db
def test_public_packages_uses_cache(public_schema, public_packages):
    cache.clear()
    client = APIClient()
    client.get("/api/v1/billing/public/packages/", HTTP_HOST="localhost")
    assert cache.get(public_packages_key()) is not None


@pytest.mark.django_db
def test_registration_rejects_invalid_plan_slug(public_schema, public_packages):
    client = APIClient()
    response = client.post(
        "/api/v1/tenancy/register/",
        {
            "subdomain": "acme",
            "company_name": "Acme",
            "admin_email": "owner@acme.com",
            "plan": "nonexistent",
        },
        format="json",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 400
    assert response.data["success"] is False
    assert response.data["error_code"] == "VALIDATION_ERROR"
    assert "plan" in response.data["errors"]


@pytest.mark.django_db
def test_registration_accepts_public_plan_slug(public_schema, public_packages):
    client = APIClient()
    response = client.post(
        "/api/v1/tenancy/register/",
        {
            "subdomain": "acme",
            "company_name": "Acme",
            "admin_email": "owner@acme.com",
            "plan": "pro",
        },
        format="json",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 201
    assert response.data["success"] is True
    assert response.data["data"]["invitation_id"]
