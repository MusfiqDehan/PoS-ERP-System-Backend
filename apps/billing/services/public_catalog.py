"""Public-facing package catalog for marketing and registration."""

from __future__ import annotations

from django.core.cache import cache

from apps.billing.models import Package
from shared.cache.helpers import PUBLIC_PACKAGE_TTL, public_packages_key


def _base_queryset():
    return (
        Package.objects.filter(is_public=True, is_active=True)
        .select_related("software_product")
        .prefetch_related("package_features__feature")
        .order_by("sort_order", "name")
    )


def serialize_public_package(package: Package) -> dict:
    return {
        "slug": package.slug,
        "name": package.name,
        "description": package.description,
        "price_monthly": str(package.price_monthly),
        "price_yearly": str(package.price_yearly),
        "is_trial": package.is_trial,
        "max_branches": package.max_branches,
        "max_users": package.max_users,
        "features": [
            {
                "key": pf.feature.key,
                "name": pf.feature.name,
            }
            for pf in package.package_features.all()
        ],
    }


def list_public_packages(*, use_cache: bool = True) -> list[dict]:
    cache_key = public_packages_key()
    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    items = [serialize_public_package(pkg) for pkg in _base_queryset()]
    cache.set(cache_key, items, PUBLIC_PACKAGE_TTL)
    return items


def public_package_slugs() -> set[str]:
    return set(_base_queryset().values_list("slug", flat=True))
