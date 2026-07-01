"""API tests for paginated product list endpoint."""

import pytest
from rest_framework.test import APIClient


def _create_product(category, unit, *, name, sku, brand=None):
    from apps.inventory.models import Product

    return Product.objects.create(
        name=name,
        slug=sku.lower(),
        sku=sku,
        category=category,
        unit=unit,
        brand=brand,
        price="1.00",
        product_type=Product.TYPE_SINGLE,
    )


@pytest.fixture
def catalog_fixtures(tenant_schema):
    from apps.inventory.models import Brand, Category, Unit

    category_a = Category.objects.create(name="Beverages", slug="beverages")
    category_b = Category.objects.create(name="Snacks", slug="snacks")
    unit = Unit.objects.create(name="Piece", short_name="pc")
    brand = Brand.objects.create(name="Acme", logo="")
    products = []
    for index in range(12):
        products.append(
            _create_product(
                category_a if index % 2 == 0 else category_b,
                unit,
                name=f"Product {index}",
                sku=f"SKU-{index:03d}",
                brand=brand if index < 3 else None,
            )
        )
    _create_product(category_a, unit, name="Cola Special", sku="COLA-001")
    return {
        "category_a": category_a,
        "category_b": category_b,
        "brand": brand,
        "products": products,
    }


@pytest.mark.django_db
def test_list_products_paginated(tenant_domain, tenant_admin, catalog_fixtures):
    client = APIClient()
    client.force_authenticate(user=tenant_admin)

    response = client.get(
        "/api/v1/inventory/products/",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 200
    assert response.data["success"] is True
    assert "pagination" in response.data["data"]
    pagination = response.data["data"]["pagination"]
    assert pagination["page_size"] == 10
    assert len(response.data["data"]["items"]) == 10
    assert pagination["has_next"] is True


@pytest.mark.django_db
def test_list_products_cursor_next_page(tenant_domain, tenant_admin, catalog_fixtures):
    client = APIClient()
    client.force_authenticate(user=tenant_admin)

    first = client.get(
        "/api/v1/inventory/products/",
        HTTP_HOST="test-tenant.localhost",
    )
    next_cursor = first.data["data"]["pagination"]["next_cursor"]
    second = client.get(
        "/api/v1/inventory/products/",
        {"cursor": next_cursor},
        HTTP_HOST="test-tenant.localhost",
    )
    assert second.status_code == 200
    first_ids = {item["id"] for item in first.data["data"]["items"]}
    second_ids = {item["id"] for item in second.data["data"]["items"]}
    assert first_ids.isdisjoint(second_ids)
    assert second.data["data"]["pagination"]["has_previous"] is True


@pytest.mark.django_db
def test_list_products_search(tenant_domain, tenant_admin, catalog_fixtures):
    client = APIClient()
    client.force_authenticate(user=tenant_admin)

    response = client.get(
        "/api/v1/inventory/products/",
        {"search": "COLA"},
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 200
    items = response.data["data"]["items"]
    assert len(items) == 1
    assert items[0]["sku"] == "COLA-001"


@pytest.mark.django_db
def test_list_products_filter_category(tenant_domain, tenant_admin, catalog_fixtures):
    client = APIClient()
    client.force_authenticate(user=tenant_admin)
    category_a = catalog_fixtures["category_a"]

    response = client.get(
        "/api/v1/inventory/products/",
        {"category": str(category_a.id), "page_size": 100},
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 200
    items = response.data["data"]["items"]
    assert len(items) == 7
    assert all(str(item["category"]) == str(category_a.id) for item in items)


@pytest.mark.django_db
def test_list_products_invalid_cursor(tenant_domain, tenant_admin, catalog_fixtures):
    client = APIClient()
    client.force_authenticate(user=tenant_admin)

    response = client.get(
        "/api/v1/inventory/products/",
        {"cursor": "not-a-valid-cursor"},
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 400
    assert response.data["success"] is False
