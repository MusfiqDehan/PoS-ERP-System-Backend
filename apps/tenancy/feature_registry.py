"""Canonical PoS tenant feature keys for RBAC and sync_features."""

from __future__ import annotations

from typing import TypedDict


class RegistryItem(TypedDict, total=False):
    key: str
    name: str
    route: str | None
    group: str
    children: list["RegistryItem"]


TENANT_REGISTRY: list[RegistryItem] = [
    {
        "group": "Core",
        "children": [
            {"key": "dashboard", "name": "Dashboard", "route": "/dashboard"},
            {"key": "pos", "name": "Point of Sale", "route": "/pos"},
            {"key": "orders", "name": "Orders", "route": "/orders"},
        ],
    },
    {
        "group": "Catalog",
        "children": [
            {"key": "products", "name": "Products", "route": "/products"},
            {"key": "inventory", "name": "Inventory", "route": "/inventory"},
        ],
    },
    {
        "group": "Customers",
        "children": [
            {"key": "customers", "name": "Customers", "route": "/customers"},
        ],
    },
    {
        "group": "Operations",
        "children": [
            {"key": "branches", "name": "Branches", "route": "/branches"},
            {"key": "reports", "name": "Reports", "route": "/reports"},
        ],
    },
    {
        "group": "Administration",
        "children": [
            {"key": "settings", "name": "Settings", "route": "/settings"},
            {"key": "permissions", "name": "Permissions", "route": "/permissions"},
        ],
    },
]

SHARED_FEATURES: list[dict[str, str]] = []


def default_feature_keys() -> list[str]:
    """Return all tenant feature keys from the canonical registry."""
    keys: list[str] = []
    for group in TENANT_REGISTRY:
        for item in group.get("children", []):
            keys.append(item["key"])
    return keys


PLATFORM_REGISTRY: list[RegistryItem] = [
    {
        "group": "Platform Admin",
        "children": [
            {
                "key": "platform.tenants",
                "name": "Tenants",
                "route": "/platform/tenants",
            },
            {
                "key": "platform.platform_users",
                "name": "Platform Team",
                "route": "/platform/team",
            },
            {
                "key": "platform.features",
                "name": "Features",
                "route": "/platform/features",
            },
            {
                "key": "platform.audit_logs",
                "name": "Audit Logs",
                "route": "/platform/audit-logs",
            },
            {
                "key": "platform.settings",
                "name": "Settings",
                "route": "/platform/settings",
            },
            {
                "key": "platform.billing",
                "name": "Billing",
                "route": "/platform/billing",
            },
            {
                "key": "platform.packages",
                "name": "Packages",
                "route": "/platform/packages",
            },
        ],
    },
]
