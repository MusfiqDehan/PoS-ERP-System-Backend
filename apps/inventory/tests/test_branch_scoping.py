"""Branch scoping security tests for inventory stock."""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.inventory.models import (
    Category,
    Product,
    PurchaseOrder,
    Supplier,
    Unit,
    Warehouse,
)
from apps.inventory.services.checkout import CheckoutService
from apps.inventory.services.stock import StockService


def _product_with_stock(branch, sku: str, second_branch=None):
    category = Category.objects.create(name=f"Cat-{sku}", slug=f"cat-{sku}")
    unit = Unit.objects.create(name=f"Unit-{sku}", short_name="u")
    product = Product.objects.create(
        name=f"Item-{sku}",
        slug=f"item-{sku}",
        sku=sku,
        category=category,
        unit=unit,
        price="10.00",
    )
    StockService.get_or_create_branch_stock(branch=branch, product=product)
    if second_branch is not None:
        StockService.get_or_create_branch_stock(branch=second_branch, product=product)
    return product


@pytest.mark.django_db
def test_tenant_admin_sees_all_branch_stock(
    tenant_domain, tenant_schema, tenant_admin, branch_manager_user, second_branch
):
    _, branch_a = branch_manager_user
    _product_with_stock(branch_a, "ITEM-1", second_branch)

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
    _product_with_stock(branch_a, "ITEM-2", second_branch)

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
    _product_with_stock(branch_a, "ITEM-3", second_branch)

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(
        f"/api/v1/inventory/stock-levels/?branch={second_branch.id}",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 200
    assert len(response.data["data"]["items"]) == 0


@pytest.mark.django_db
def test_cashier_scoped_to_assigned_branch_stock(
    tenant_domain, tenant_schema, cashier_user, second_branch
):
    user, branch_a = cashier_user
    _product_with_stock(branch_a, "ITEM-CASH", second_branch)

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(
        "/api/v1/inventory/stock-levels/",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 200
    assert len(response.data["data"]["items"]) == 1
    assert str(response.data["data"]["items"][0]["branch"]) == str(branch_a.id)


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


@pytest.mark.django_db
def test_branch_assigned_user_dashboard_summary_scoped(
    tenant_domain, tenant_schema, cashier_user, second_branch
):
    user, branch_a = cashier_user
    product = _product_with_stock(branch_a, "DASH-1", second_branch)
    stock = StockService.get_or_create_branch_stock(branch=branch_a, product=product)
    StockService.increment(
        stock_level_id=stock.id,
        quantity=Decimal("5"),
        movement_type="adjustment",
    )
    CheckoutService.checkout(
        branch=branch_a,
        cashier=user,
        lines=[{"product": product, "quantity": Decimal("1"), "unit_price": "10.00"}],
        payments=[{"method": "cash", "amount": "10.00"}],
        idempotency_key="dash-own",
    )
    other_stock = StockService.get_or_create_branch_stock(
        branch=second_branch, product=product
    )
    StockService.increment(
        stock_level_id=other_stock.id,
        quantity=Decimal("5"),
        movement_type="adjustment",
    )
    CheckoutService.checkout(
        branch=second_branch,
        cashier=user,
        lines=[{"product": product, "quantity": Decimal("1"), "unit_price": "10.00"}],
        payments=[{"method": "cash", "amount": "10.00"}],
        idempotency_key="dash-other",
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(
        "/api/v1/inventory/dashboard/summary/?scope=business",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 200
    assert response.data["data"]["order_count"] == 1


@pytest.mark.django_db
def test_pos_checkout_foreign_branch_denied(
    tenant_domain, tenant_schema, cashier_user, second_branch
):
    user, branch_a = cashier_user
    product = _product_with_stock(branch_a, "POS-DENY")
    stock = StockService.get_or_create_branch_stock(branch=branch_a, product=product)
    StockService.increment(
        stock_level_id=stock.id,
        quantity=Decimal("5"),
        movement_type="adjustment",
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        "/api/v1/pos/checkout/",
        {
            "branch": str(second_branch.id),
            "lines": [{"product": str(product.id), "quantity": "1"}],
            "payments": [{"method": "cash", "amount": "10.00"}],
        },
        format="json",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_pos_products_foreign_branch_denied(
    tenant_domain, tenant_schema, cashier_user, second_branch
):
    user, _ = cashier_user
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(
        f"/api/v1/pos/products/?branch={second_branch.id}",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_branch_assigned_user_lists_tenant_wide_purchase_orders(
    tenant_domain, tenant_schema, branch_manager_user
):
    user, _ = branch_manager_user
    supplier = Supplier.objects.create(name="Sup", code="SUP-1")
    warehouse = Warehouse.objects.create(name="WH", code="WH-1")
    PurchaseOrder.objects.create(
        supplier=supplier,
        warehouse=warehouse,
        ref_number="PO-001",
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(
        "/api/v1/inventory/purchase-orders/",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 200
    assert len(response.data["data"]["items"]) == 1


@pytest.mark.django_db
def test_replenishment_hides_other_branches_for_scoped_user(
    tenant_domain, tenant_schema, cashier_user, second_branch
):
    user, branch_a = cashier_user
    product = _product_with_stock(branch_a, "REPL", second_branch)
    own_stock = StockService.get_or_create_branch_stock(
        branch=branch_a, product=product
    )
    StockService.increment(
        stock_level_id=own_stock.id,
        quantity=Decimal("3"),
        movement_type="adjustment",
    )
    other_stock = StockService.get_or_create_branch_stock(
        branch=second_branch, product=product
    )
    StockService.increment(
        stock_level_id=other_stock.id,
        quantity=Decimal("9"),
        movement_type="adjustment",
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(
        f"/api/v1/inventory/replenishment-options/?product={product.id}&branch={branch_a.id}",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 200
    branch_sources = [
        row for row in response.data["data"] if row["source_type"] == "branch"
    ]
    assert all(row["source_id"] == str(branch_a.id) for row in branch_sources)
