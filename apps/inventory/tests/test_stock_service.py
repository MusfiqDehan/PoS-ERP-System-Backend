"""StockService unit tests."""

from decimal import Decimal

import pytest

from apps.inventory.models import Category, Product, StockMovement, Unit
from apps.inventory.services.stock import StockService
from shared.responses.exceptions import DomainAPIException


@pytest.mark.django_db
def test_stock_increment_and_decrement(tenant_schema, branch_manager_user):
    _, branch = branch_manager_user
    category = Category.objects.create(name="Cat", slug="cat")
    unit = Unit.objects.create(name="Unit", short_name="u")
    product = Product.objects.create(
        name="Item",
        slug="item",
        sku="STK-1",
        category=category,
        unit=unit,
        price="10.00",
    )
    stock = StockService.get_or_create_branch_stock(branch=branch, product=product)
    StockService.increment(
        stock_level_id=stock.id,
        quantity=Decimal("10"),
        movement_type=StockMovement.MOVEMENT_ADJUSTMENT,
    )
    stock.refresh_from_db()
    assert stock.quantity == Decimal("10")

    StockService.decrement(
        stock_level_id=stock.id,
        quantity=Decimal("3"),
        movement_type=StockMovement.MOVEMENT_SALE,
    )
    stock.refresh_from_db()
    assert stock.quantity == Decimal("7")
    assert StockMovement.objects.filter(stock_level=stock).count() == 2


@pytest.mark.django_db
def test_decrement_insufficient_stock(tenant_schema, branch_manager_user):
    _, branch = branch_manager_user
    category = Category.objects.create(name="Cat", slug="cat")
    unit = Unit.objects.create(name="Unit", short_name="u")
    product = Product.objects.create(
        name="Item",
        slug="item",
        sku="STK-2",
        category=category,
        unit=unit,
        price="10.00",
    )
    stock = StockService.get_or_create_branch_stock(branch=branch, product=product)

    with pytest.raises(DomainAPIException) as exc:
        StockService.decrement(
            stock_level_id=stock.id,
            quantity=Decimal("1"),
            movement_type=StockMovement.MOVEMENT_SALE,
        )
    assert exc.value.error_code == "INSUFFICIENT_STOCK"
