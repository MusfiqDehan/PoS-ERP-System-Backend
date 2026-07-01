"""Checkout service and POS API tests."""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.inventory.models import Category, Product, Sale, Unit
from apps.inventory.services.checkout import CheckoutService
from apps.inventory.services.stock import StockService


@pytest.mark.django_db
def test_checkout_decrements_stock(tenant_schema, branch_manager_user):
    user, branch = branch_manager_user
    category = Category.objects.create(name="Cat", slug="cat")
    unit = Unit.objects.create(name="Unit", short_name="u")
    product = Product.objects.create(
        name="Item",
        slug="item",
        sku="CHK-1",
        category=category,
        unit=unit,
        price="10.00",
    )
    stock = StockService.get_or_create_branch_stock(branch=branch, product=product)
    StockService.increment(
        stock_level_id=stock.id,
        quantity=Decimal("5"),
        movement_type="adjustment",
    )

    sale = CheckoutService.checkout(
        branch=branch,
        cashier=user,
        lines=[{"product": product, "quantity": Decimal("2"), "unit_price": "10.00"}],
        payments=[{"method": "cash", "amount": "20.00"}],
        idempotency_key="test-key-1",
    )
    assert sale.status == Sale.STATUS_COMPLETED
    stock.refresh_from_db()
    assert stock.quantity == Decimal("3")


@pytest.mark.django_db
def test_checkout_insufficient_stock(tenant_schema, branch_manager_user):
    user, branch = branch_manager_user
    category = Category.objects.create(name="Cat", slug="cat")
    unit = Unit.objects.create(name="Unit", short_name="u")
    product = Product.objects.create(
        name="Item",
        slug="item",
        sku="CHK-2",
        category=category,
        unit=unit,
        price="10.00",
    )
    StockService.get_or_create_branch_stock(branch=branch, product=product)

    from shared.responses.exceptions import DomainAPIException

    with pytest.raises(DomainAPIException) as exc:
        CheckoutService.checkout(
            branch=branch,
            cashier=user,
            lines=[
                {"product": product, "quantity": Decimal("1"), "unit_price": "10.00"}
            ],
            payments=[{"method": "cash", "amount": "10.00"}],
        )
    assert exc.value.error_code == "INSUFFICIENT_STOCK"


@pytest.mark.django_db
def test_checkout_idempotency(tenant_schema, branch_manager_user):
    user, branch = branch_manager_user
    category = Category.objects.create(name="Cat", slug="cat")
    unit = Unit.objects.create(name="Unit", short_name="u")
    product = Product.objects.create(
        name="Item",
        slug="item",
        sku="CHK-3",
        category=category,
        unit=unit,
        price="10.00",
    )
    stock = StockService.get_or_create_branch_stock(branch=branch, product=product)
    StockService.increment(
        stock_level_id=stock.id,
        quantity=Decimal("5"),
        movement_type="adjustment",
    )

    kwargs = dict(
        branch=branch,
        cashier=user,
        lines=[{"product": product, "quantity": Decimal("1"), "unit_price": "10.00"}],
        payments=[{"method": "cash", "amount": "10.00"}],
        idempotency_key="idem-123",
    )
    sale1 = CheckoutService.checkout(**kwargs)
    sale2 = CheckoutService.checkout(**kwargs)
    assert sale1.id == sale2.id
    assert Sale.objects.count() == 1


@pytest.mark.django_db
def test_pos_checkout_api(tenant_domain, tenant_schema, branch_manager_user):
    user, branch = branch_manager_user
    category = Category.objects.create(name="Cat", slug="cat")
    unit = Unit.objects.create(name="Unit", short_name="u")
    product = Product.objects.create(
        name="Item",
        slug="item",
        sku="API-CHK-1",
        category=category,
        unit=unit,
        price="15.00",
    )
    stock = StockService.get_or_create_branch_stock(branch=branch, product=product)
    StockService.increment(
        stock_level_id=stock.id,
        quantity=Decimal("10"),
        movement_type="adjustment",
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        "/api/v1/pos/checkout/",
        {
            "branch": str(branch.id),
            "lines": [{"product": str(product.id), "quantity": "2"}],
            "payments": [{"method": "cash", "amount": "30.00"}],
        },
        format="json",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 201
    assert response.data["success"] is True
    assert response.data["data"]["total"] == "30.00"
