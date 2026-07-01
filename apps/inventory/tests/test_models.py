"""Model tests for inventory catalog."""

import pytest
from django.db import IntegrityError

from apps.inventory.models import (
    Brand,
    Category,
    Product,
    ProductVariant,
    StockLevel,
    Unit,
    Warehouse,
)


@pytest.mark.django_db
def test_category_parent_child(tenant_schema):
    parent = Category.objects.create(name="Electronics", slug="electronics")
    child = Category.objects.create(
        name="Phones", slug="phones", parent=parent
    )
    assert child.parent_id == parent.id


@pytest.mark.django_db
def test_product_unique_sku(tenant_schema):
    category = Category.objects.create(name="General", slug="general")
    unit = Unit.objects.create(name="Piece", short_name="pc")
    Product.objects.create(
        name="Widget",
        slug="widget",
        sku="SKU-001",
        category=category,
        unit=unit,
        price="10.00",
    )
    with pytest.raises(IntegrityError):
        Product.objects.create(
            name="Widget 2",
            slug="widget-2",
            sku="SKU-001",
            category=category,
            unit=unit,
            price="12.00",
        )


@pytest.mark.django_db
def test_variable_product_variants(tenant_schema):
    category = Category.objects.create(name="Apparel", slug="apparel")
    unit = Unit.objects.create(name="Piece", short_name="pc")
    product = Product.objects.create(
        name="Shirt",
        slug="shirt",
        sku="SHIRT-BASE",
        category=category,
        unit=unit,
        product_type=Product.TYPE_VARIABLE,
        price="0.00",
    )
    variant = ProductVariant.objects.create(
        product=product,
        sku="SHIRT-RED-M",
        attributes={"color": "red", "size": "M"},
        price="25.00",
    )
    assert product.variants.count() == 1
    assert variant.sku == "SHIRT-RED-M"


@pytest.mark.django_db
def test_warehouse_unique_code(tenant_schema):
    Warehouse.objects.create(name="Central", code="WH-MAIN")
    with pytest.raises(IntegrityError):
        Warehouse.objects.create(name="Duplicate", code="WH-MAIN")


@pytest.mark.django_db
def test_stock_level_unique_per_location(tenant_schema, branch_manager_user):
    _, branch = branch_manager_user
    category = Category.objects.create(name="Food", slug="food")
    unit = Unit.objects.create(name="Kg", short_name="kg")
    product = Product.objects.create(
        name="Rice",
        slug="rice",
        sku="RICE-1",
        category=category,
        unit=unit,
        price="5.00",
    )
    StockLevel.objects.create(
        location_type=StockLevel.LOCATION_BRANCH,
        branch=branch,
        product=product,
        quantity="100",
    )
    with pytest.raises(IntegrityError):
        StockLevel.objects.create(
            location_type=StockLevel.LOCATION_BRANCH,
            branch=branch,
            product=product,
            quantity="50",
        )


@pytest.mark.django_db
def test_brand_creation(tenant_schema):
    brand = Brand.objects.create(name="Acme")
    assert brand.name == "Acme"
