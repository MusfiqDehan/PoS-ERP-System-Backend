"""API tests for inventory catalog endpoints."""

import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_list_products_requires_auth(tenant_domain):
    client = APIClient()
    response = client.get(
        "/api/v1/inventory/products/",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_admin_can_create_and_list_product(
    tenant_domain, tenant_schema, tenant_admin
):
    from apps.inventory.models import Category, Unit

    client = APIClient()
    client.force_authenticate(user=tenant_admin)
    category = Category.objects.create(name="Beverages", slug="beverages")
    unit = Unit.objects.create(name="Bottle", short_name="btl")

    create_resp = client.post(
        "/api/v1/inventory/products/",
        {
            "name": "Cola",
            "slug": "cola",
            "sku": "COLA-001",
            "category": str(category.id),
            "unit": str(unit.id),
            "price": "2.50",
            "cost": "1.00",
            "product_type": "single",
        },
        format="json",
        HTTP_HOST="test-tenant.localhost",
    )
    assert create_resp.status_code == 201
    assert create_resp.data["success"] is True
    assert create_resp.data["data"]["sku"] == "COLA-001"

    list_resp = client.get(
        "/api/v1/inventory/products/",
        HTTP_HOST="test-tenant.localhost",
    )
    assert list_resp.status_code == 200
    assert list_resp.data["success"] is True
    assert len(list_resp.data["data"]["items"]) == 1


@pytest.mark.django_db
def test_create_variable_product_with_variants(
    tenant_domain, tenant_schema, tenant_admin
):
    from apps.inventory.models import Category, Product, Unit

    client = APIClient()
    client.force_authenticate(user=tenant_admin)
    category = Category.objects.create(name="Apparel", slug="apparel")
    unit = Unit.objects.create(name="Piece", short_name="pc")

    create_resp = client.post(
        "/api/v1/inventory/products/",
        {
            "name": "T-Shirt",
            "slug": "t-shirt",
            "sku": "TSHIRT-PARENT",
            "category": str(category.id),
            "unit": str(unit.id),
            "price": "0",
            "product_type": "variable",
            "variants": [
                {
                    "sku": "TSHIRT-RED",
                    "price": "19.99",
                    "attributes": {"color": "red"},
                },
                {
                    "sku": "TSHIRT-BLUE",
                    "price": "19.99",
                    "attributes": {"color": "blue"},
                },
            ],
        },
        format="json",
        HTTP_HOST="test-tenant.localhost",
    )
    assert create_resp.status_code == 201
    product_id = create_resp.data["data"]["id"]
    product = Product.objects.get(id=product_id)
    assert product.product_type == Product.TYPE_VARIABLE
    assert product.variants.count() == 2
    variant_skus = {variant["sku"] for variant in create_resp.data["data"]["variants"]}
    assert variant_skus == {"TSHIRT-RED", "TSHIRT-BLUE"}


@pytest.mark.django_db
def test_create_product_with_extended_fields(
    tenant_domain, tenant_schema, tenant_admin
):
    from apps.inventory.models import Category, Unit, Warranty

    client = APIClient()
    client.force_authenticate(user=tenant_admin)
    category = Category.objects.create(name="Food", slug="food")
    unit = Unit.objects.create(name="Kg", short_name="kg")
    warranty = Warranty.objects.create(name="1 Year", duration_days=365)

    create_resp = client.post(
        "/api/v1/inventory/products/",
        {
            "name": "Rice",
            "slug": "rice",
            "sku": "RICE-001",
            "category": str(category.id),
            "unit": str(unit.id),
            "price": "12.00",
            "cost": "8.00",
            "warranty": str(warranty.id),
            "manufactured_at": "2026-01-01",
            "expires_at": "2027-01-01",
            "images": ["https://cdn.example.com/rice.jpg"],
            "product_type": "single",
        },
        format="json",
        HTTP_HOST="test-tenant.localhost",
    )
    assert create_resp.status_code == 201
    data = create_resp.data["data"]
    assert data["cost"] == "8.00"
    assert str(data["warranty"]) == str(warranty.id)
    assert data["manufactured_at"] == "2026-01-01"
    assert data["expires_at"] == "2027-01-01"
    assert data["images"] == ["https://cdn.example.com/rice.jpg"]


@pytest.mark.django_db
def test_variable_product_without_variants_rejected(
    tenant_domain, tenant_schema, tenant_admin
):
    from apps.inventory.models import Category, Unit

    client = APIClient()
    client.force_authenticate(user=tenant_admin)
    category = Category.objects.create(name="Misc", slug="misc")
    unit = Unit.objects.create(name="Unit", short_name="u")

    create_resp = client.post(
        "/api/v1/inventory/products/",
        {
            "name": "Empty Variable",
            "slug": "empty-variable",
            "sku": "VAR-EMPTY",
            "category": str(category.id),
            "unit": str(unit.id),
            "price": "1.00",
            "product_type": "variable",
            "variants": [],
        },
        format="json",
        HTTP_HOST="test-tenant.localhost",
    )
    assert create_resp.status_code == 400
    assert create_resp.data["success"] is False


@pytest.mark.django_db
def test_list_categories(tenant_domain, tenant_schema, tenant_admin):
    from apps.inventory.models import Category

    Category.objects.create(name="Snacks", slug="snacks")
    client = APIClient()
    client.force_authenticate(user=tenant_admin)
    response = client.get(
        "/api/v1/inventory/categories/",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 200
    assert response.data["data"]["items"][0]["slug"] == "snacks"
