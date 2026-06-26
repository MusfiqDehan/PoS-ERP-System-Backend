"""Idempotently seed Sortorium PoS product with trial and starter packages."""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import get_public_schema_name, schema_context

from apps.billing.models import (
    Package,
    PackageFeature,
    PackageRoleLimit,
    PaymentGateway,
    SoftwareProductCategory,
    SoftwareProduct,
)
from apps.tenancy.models import Feature

POS_PRODUCT_SLUG = "sortorium-pos"
POS_CATEGORY_SLUG = "point-of-sale"

TRIAL_FEATURE_KEYS = [
    "dashboard",
    "pos",
    "orders",
    "products",
    "customers",
    "branches",
    "settings",
]

STARTER_FEATURE_KEYS = TRIAL_FEATURE_KEYS + [
    "inventory",
    "reports",
    "permissions",
]

PACKAGE_TIERS = {
    "free": {
        "name": "Free Trial",
        "description": "14-day trial with core PoS features.",
        "price_monthly": Decimal("0"),
        "price_yearly": Decimal("0"),
        "is_trial": True,
        "max_branches": 1,
        "max_users": 5,
        "max_custom_roles": 0,
        "max_admins": 1,
        "max_staff": 5,
        "sort_order": 1,
        "feature_keys": TRIAL_FEATURE_KEYS,
        "role_limits": {"cashier": 3},
    },
    "starter": {
        "name": "Starter",
        "description": "Essential PoS for a single branch.",
        "price_monthly": Decimal("29.00"),
        "price_yearly": Decimal("290.00"),
        "is_trial": False,
        "max_branches": 3,
        "max_users": 25,
        "max_custom_roles": 3,
        "max_admins": 2,
        "max_staff": 20,
        "sort_order": 4,
        "feature_keys": STARTER_FEATURE_KEYS,
        "role_limits": {"cashier": 10, "manager": 2},
    },
    "pro": {
        "name": "Pro",
        "description": "Essential PoS for growing retail teams.",
        "price_monthly": Decimal("39.00"),
        "price_yearly": Decimal("390.00"),
        "is_trial": False,
        "max_branches": 3,
        "max_users": 25,
        "max_custom_roles": 3,
        "max_admins": 2,
        "max_staff": 20,
        "sort_order": 2,
        "feature_keys": STARTER_FEATURE_KEYS,
        "role_limits": {"cashier": 10, "manager": 2},
    },
}


class Command(BaseCommand):
    help = (
        "Seed Sortorium PoS product, public packages (free, pro, trial, starter), "
        "and SSLCommerz gateway."
    )

    def handle(self, *args, **options):
        with schema_context(get_public_schema_name()), transaction.atomic():
            category, _ = SoftwareProductCategory.objects.update_or_create(
                slug=POS_CATEGORY_SLUG,
                defaults={"name": "Point of Sale", "sort_order": 1},
            )
            product, _ = SoftwareProduct.objects.update_or_create(
                slug=POS_PRODUCT_SLUG,
                defaults={
                    "name": "Sortorium PoS",
                    "description": "Multi-branch point of sale for retail.",
                    "category": category,
                    "sort_order": 1,
                    "is_active": True,
                    "is_published": True,
                },
            )
            self.stdout.write(self.style.SUCCESS(f"Product: {product.slug}"))

            features = {f.key: f for f in Feature.objects.all()}
            for slug, tier in PACKAGE_TIERS.items():
                package_fields = {
                    k: v
                    for k, v in tier.items()
                    if k not in {"feature_keys", "role_limits"}
                }
                package, created = Package.objects.update_or_create(
                    slug=slug,
                    defaults={
                        **package_fields,
                        "software_product": product,
                        "is_public": True,
                        "is_active": True,
                    },
                )
                self._sync_package_features(package, tier["feature_keys"], features)
                self._sync_role_limits(package, tier["role_limits"])
                verb = "Created" if created else "Updated"
                self.stdout.write(f"  {verb} package '{slug}'")

            PaymentGateway.objects.update_or_create(
                slug="sslcommerz",
                defaults={
                    "name": "SSLCommerz",
                    "credential_schema": {
                        "store_id": "string",
                        "store_password": "string",
                    },
                    "is_enabled_for_tenants": True,
                    "is_default_for_subscriptions": True,
                    "is_sandbox": True,
                    "sort_order": 1,
                },
            )
            self.stdout.write(self.style.SUCCESS("SSLCommerz gateway seeded."))

        self.stdout.write(self.style.SUCCESS("PoS catalog seed complete."))

    def _sync_package_features(self, package, keys, features):
        wanted_ids = {features[k].id for k in keys if k in features}
        missing = [k for k in keys if k not in features]
        if missing:
            self.stdout.write(
                self.style.WARNING(
                    "Missing features (run sync_features first): " + ", ".join(missing)
                )
            )
        existing = {pf.feature_id: pf for pf in package.package_features.all()}
        for feature_id in wanted_ids:
            if feature_id not in existing:
                PackageFeature.objects.create(package=package, feature_id=feature_id)
        for feature_id, pf in existing.items():
            if feature_id not in wanted_ids:
                pf.delete()

    def _sync_role_limits(self, package, limits):
        existing = {rl.role_slug: rl for rl in package.role_limits.all()}
        for role_slug, max_users in limits.items():
            rl = existing.get(role_slug)
            if rl is None:
                PackageRoleLimit.objects.create(
                    package=package, role_slug=role_slug, max_users=max_users
                )
            elif rl.max_users != max_users:
                rl.max_users = max_users
                rl.save(update_fields=["max_users", "updated_at"])
