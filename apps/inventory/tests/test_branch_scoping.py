"""Branch scoping security tests for inventory stock."""

import pytest
from rest_framework.test import APIClient

from apps.inventory.models import Category, Product, StockLevel, Unit
from apps.inventory.services.stock import StockService


@pytest.mark.django_db
def test_tenant_admin_sees_all_branch_stock(
    tenant_domain, tenant_schema, tenant_admin, branch_manager_user, second_branch
):
    _, branch_a = branch_manager_user
    category = Category.objects.create(name="Cat", slug="cat")
    unit = Unit.objects.create(name="Unit", short_name="u")
    product = Product.objects.create(
        name="Item",
        slug="item",
        sku="ITEM-1",
        category=category,
        unit=unit,
        price="10.00",
    )
    StockService.get_or_create_branch_stock(branch=branch_a, product=product)
    StockService.get_or_create_branch_stock(branch=second_branch, product=product)

    client = APIClient()
    client.force_authenticate(user=tenant_admin)
    response = client.get(
        "/api/v1/inventory/stock-levels/",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 200
    assert len(response.data["data"]["items"]) == 2


@pytest.mark.django_db
def test_tenant_admin_branch_filter(
    tenant_domain, tenant_schema, tenant_admin, branch_manager_user, second_branch
):
    _, branch_a = branch_manager_user
    category = Category.objects.create(name="Cat", slug="cat")
    unit = Unit.objects.create(name="Unit", short_name="u")
    product = Product.objects.create(
        name="Item",
        slug="item",
        sku="ITEM-2",
        category=category,
        unit=unit,
        price="10.00",
    )
    StockService.get_or_create_branch_stock(branch=branch_a, product=product)
    StockService.get_or_create_branch_stock(branch=second_branch, product=product)

    client = APIClient()
    client.force_authenticate(user=tenant_admin)
    response = client.get(
        f"/api/v1/inventory/stock-levels/?branch={branch_a.id}",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 200
    assert len(response.data["data"]["items"]) == 1
    assert str(response.data["data"]["items"][0]["branch"]) == str(branch_a.id)


@pytest.mark.django_db
def test_branch_manager_cannot_see_other_branch_stock(
    tenant_domain, tenant_schema, branch_manager_user, second_branch
):
    user, branch_a = branch_manager_user
    category = Category.objects.create(name="Cat", slug="cat")
    unit = Unit.objects.create(name="Unit", short_name="u")
    product = Product.objects.create(
        name="Item",
        slug="item",
        sku="ITEM-3",
        category=category,
        unit=unit,
        price="10.00",
    )
    StockService.get_or_create_branch_stock(branch=branch_a, product=product)
    StockService.get_or_create_branch_stock(branch=second_branch, product=product)

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(
        f"/api/v1/inventory/stock-levels/?branch={second_branch.id}",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 200
    assert len(response.data["data"]["items"]) == 0


@pytest.mark.django_db
def test_invalid_branch_filter_returns_empty(
    tenant_domain, tenant_schema, tenant_admin
):
    client = APIClient()
    client.force_authenticate(user=tenant_admin)
    response = client.get(
        "/api/v1/inventory/stock-levels/?branch=not-a-uuid",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 200
    assert response.data["data"]["items"] == []
