"""Seed predefined tenant roles inside the current tenant schema."""

from django.core.management.base import BaseCommand
from django.db import connection, transaction

from apps.access.models import Role, RolePermission
from apps.tenancy.feature_registry import TENANT_REGISTRY


def _all_feature_keys() -> list[str]:
    keys: list[str] = []
    for group in TENANT_REGISTRY:
        for item in group.get("children", []):
            keys.append(item["key"])
    return keys


PREDEFINED_TENANT_ROLES = {
    "admin": {
        "name": "Admin",
        "description": "Full access to everything in this tenant.",
        "color": "#dc2626",
        "permissions": "FULL_ACCESS",
    },
    "manager": {
        "name": "Manager",
        "description": "Operational manager for PoS and inventory.",
        "color": "#2563eb",
        "permissions": {
            "dashboard": "view",
            "pos": "edit",
            "orders": "edit",
            "products": "edit",
            "inventory": "edit",
            "customers": "edit",
            "reports": "view",
            "branches": "view",
        },
    },
    "cashier": {
        "name": "Cashier",
        "description": "Point-of-sale operator.",
        "color": "#16a34a",
        "permissions": {
            "dashboard": "view",
            "pos": "edit",
            "orders": "view",
            "products": "view",
            "customers": "view",
        },
    },
    "viewer": {
        "name": "Viewer",
        "description": "Read-only dashboard access.",
        "color": "#64748b",
        "permissions": {
            "dashboard": "view",
            "orders": "view",
            "products": "view",
            "reports": "view",
        },
    },
    "branch_manager": {
        "name": "Branch Manager",
        "description": "Manages a single branch.",
        "color": "#0891b2",
        "permissions": {
            "dashboard": "view",
            "pos": "edit",
            "orders": "edit",
            "products": "edit",
            "inventory": "edit",
            "customers": "edit",
            "branches": "view",
            "reports": "view",
        },
    },
}


class Command(BaseCommand):
    help = "Seed predefined tenant roles in the current tenant schema."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Reset role permissions to defaults if they differ.",
        )

    def handle(self, *args, **options):
        schema = connection.schema_name
        if schema == "public":
            self.stdout.write(
                self.style.WARNING("Skipping public schema (no access tables).")
            )
            return

        reset = options["reset"]
        full_access_keys = _all_feature_keys()
        with transaction.atomic():
            for slug, info in PREDEFINED_TENANT_ROLES.items():
                role, created = Role.objects.update_or_create(
                    slug=slug,
                    defaults={
                        "name": info["name"],
                        "description": info["description"],
                        "color": info["color"],
                        "is_system": True,
                    },
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"Created role: {slug}"))

                permissions = info["permissions"]
                if permissions == "FULL_ACCESS":
                    permissions = {key: "full" for key in full_access_keys}

                for feature_key, level in permissions.items():
                    obj, perm_created = RolePermission.objects.get_or_create(
                        role=role,
                        feature_key=feature_key,
                        defaults={"permission_level": level},
                    )
                    if not perm_created and reset and obj.permission_level != level:
                        obj.permission_level = level
                        obj.save(update_fields=["permission_level"])
                        self.stdout.write(f"  Reset {feature_key} -> {level}")
                    elif perm_created:
                        self.stdout.write(f"  Added {feature_key} = {level}")
        self.stdout.write(self.style.SUCCESS("Tenant roles seeded."))
