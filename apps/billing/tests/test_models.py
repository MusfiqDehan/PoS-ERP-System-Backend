"""Tests for billing catalog models."""

import pytest
from django.db import IntegrityError

from apps.billing.models import (
    Package,
    PackageFeature,
    PackageRoleLimit,
    SoftwareProduct,
    SoftwareProductCategory,
)
from apps.tenancy.models import Feature


@pytest.mark.django_db
def test_software_product_category_uuid_primary_key(public_schema):
    category = SoftwareProductCategory.objects.create(name="Point of Sale", slug="pos")
    assert category.id.version == 7


@pytest.mark.django_db
def test_software_product_category_slug_unique(public_schema):
    SoftwareProductCategory.objects.create(name="POS", slug="pos")
    with pytest.raises(IntegrityError):
        SoftwareProductCategory.objects.create(name="POS 2", slug="pos")


@pytest.mark.django_db
def test_software_product_belongs_to_category(public_schema):
    category = SoftwareProductCategory.objects.create(name="Retail", slug="retail")
    product = SoftwareProduct.objects.create(
        name="Sortorium PoS",
        slug="sortorium-pos",
        category=category,
    )
    assert product.category_id == category.id


@pytest.mark.django_db
def test_package_belongs_to_software_product(public_schema):
    product = SoftwareProduct.objects.create(name="Sortorium PoS", slug="sortorium-pos")
    package = Package.objects.create(
        software_product=product,
        name="Starter",
        slug="starter",
        max_branches=3,
        max_users=25,
    )
    assert package.software_product_id == product.id
    assert package.max_branches == 3


@pytest.mark.django_db
def test_package_slug_unique(public_schema):
    product = SoftwareProduct.objects.create(name="Sortorium PoS", slug="sortorium-pos")
    Package.objects.create(software_product=product, name="Trial", slug="trial")
    with pytest.raises(IntegrityError):
        Package.objects.create(software_product=product, name="Trial 2", slug="trial")


@pytest.mark.django_db
def test_package_feature_unique_per_package(public_schema):
    product = SoftwareProduct.objects.create(name="Sortorium PoS", slug="sortorium-pos")
    package = Package.objects.create(
        software_product=product, name="Trial", slug="trial"
    )
    feature = Feature.objects.create(key="pos", name="Point of Sale")
    PackageFeature.objects.create(package=package, feature=feature)
    with pytest.raises(IntegrityError):
        PackageFeature.objects.create(package=package, feature=feature)


@pytest.mark.django_db
def test_package_role_limit_unique_per_role(public_schema):
    product = SoftwareProduct.objects.create(name="Sortorium PoS", slug="sortorium-pos")
    package = Package.objects.create(
        software_product=product, name="Trial", slug="trial"
    )
    PackageRoleLimit.objects.create(package=package, role_slug="cashier", max_users=5)
    with pytest.raises(IntegrityError):
        PackageRoleLimit.objects.create(
            package=package, role_slug="cashier", max_users=10
        )
