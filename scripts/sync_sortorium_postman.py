#!/usr/bin/env python3
"""Sync Sortorium Postman collection with platform-owner endpoints and OpenAPI spec.

Updates `.tmp-postman-collection-payload.json` at the monorepo root and, when
POSTMAN_API_KEY is set, pushes the collection to the GeekSSort workspace.

Usage (from monorepo root):
    cd Sortorium_Backend && source .venv/bin/activate
    python scripts/sync_sortorium_postman.py [--push] [--regenerate-openapi]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_PATH = REPO_ROOT / ".tmp-postman-collection-payload.json"
OPENAPI_PATH = REPO_ROOT / ".tmp-sortorium-openapi.yaml"

WORKSPACE_ID = "60de6d65-7979-42ab-a624-b0aa01c3b03c"
COLLECTION_ID = "28790264-575669e6-fbc3-41d1-9577-e89c9fbb5af1"
SPEC_NAME = "sortorium-pos-api"
SPEC_ROOT_FILE = "sortorium-openapi.json"

JSON_OPTS = {"raw": {"language": "json"}}


def _url(path_segments: list[str]) -> dict[str, Any]:
    raw = "{{baseUrl}}/" + "/".join(path_segments)
    return {
        "raw": raw,
        "host": ["{{baseUrl}}"],
        "path": path_segments,
    }


def _json_body(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "mode": "raw",
        "raw": json.dumps(payload, indent=2) + "\n",
        "options": JSON_OPTS,
    }


def _headers_json() -> list[dict[str, str]]:
    return [{"key": "Content-Type", "value": "application/json"}]


def _platform_auth() -> dict[str, Any]:
    return {
        "type": "bearer",
        "bearer": [
            {"key": "token", "value": "{{platformAccessToken}}", "type": "string"}
        ],
    }


def _tenant_auth() -> dict[str, Any]:
    return {
        "type": "bearer",
        "bearer": [{"key": "token", "value": "{{accessToken}}", "type": "string"}],
    }


def _request(
    *,
    name: str,
    method: str,
    path_segments: list[str],
    description: str,
    body: dict[str, Any] | None = None,
    auth: dict[str, Any] | None = None,
    event: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    req: dict[str, Any] = {
        "method": method,
        "header": _headers_json() if body else [],
        "url": _url(path_segments),
        "description": description,
    }
    if body:
        req["body"] = body
    if auth:
        req["auth"] = auth
    item: dict[str, Any] = {"name": name, "request": req}
    if event:
        item["event"] = event
    return item


def _save_platform_tokens_script() -> list[dict[str, Any]]:
    script = """
if (pm.response.code === 200) {
    const json = pm.response.json();
    const data = json.data || {};
    if (data.access) {
        pm.collectionVariables.set('platformAccessToken', data.access);
    }
    if (data.refresh) {
        pm.collectionVariables.set('platformRefreshToken', data.refresh);
    }
}
""".strip()
    return [
        {
            "listen": "test",
            "script": {"type": "text/javascript", "exec": script.splitlines()},
        }
    ]


def build_platform_owner_folder() -> dict[str, Any]:
    base = ["api", "v1", "platform-owner"]
    auth = _platform_auth()

    items = [
        _request(
            name="Authenticate a platform user",
            method="POST",
            path_segments=base + ["auth", "login"],
            description=(
                "Authenticates a platform operator on the public schema using email and "
                "password. Returns JWT access and refresh tokens with platform_user=true. "
                "Invite-only — no self-registration. Rate limited."
            ),
            body=_json_body({"email": "platform@test.com", "password": "TestPass1!"}),
            event=_save_platform_tokens_script(),
        ),
        _request(
            name="Refresh platform JWT access token",
            method="POST",
            path_segments=base + ["auth", "refresh"],
            description=(
                "Exchanges a valid platform refresh token (platform_user claim) for new "
                "access and refresh tokens. No authentication header required."
            ),
            body=_json_body({"refresh": "{{platformRefreshToken}}"}),
            event=_save_platform_tokens_script(),
        ),
        _request(
            name="Get current platform user profile",
            method="GET",
            path_segments=base + ["me"],
            description=(
                "Returns the authenticated platform user's profile on the public schema. "
                "Requires a platform JWT bearer token."
            ),
            auth=auth,
        ),
        _request(
            name="Get current platform user permissions",
            method="GET",
            path_segments=base + ["me", "permissions"],
            description=(
                "Returns the authenticated platform user's effective permission map and "
                "role assignments. Requires a platform JWT bearer token."
            ),
            auth=auth,
        ),
        _request(
            name="Change password for authenticated platform user",
            method="POST",
            path_segments=base + ["password", "change"],
            description=(
                "Changes the password for the currently authenticated platform user. "
                "Requires the current password and a validated new password."
            ),
            body=_json_body(
                {
                    "current_password": "TestPass1!",
                    "new_password": "NewSecurePass1!",
                }
            ),
            auth=auth,
        ),
        _request(
            name="Request platform password reset email",
            method="POST",
            path_segments=base + ["password", "reset", "request"],
            description=(
                "Requests a password reset email for a platform user. Always returns a "
                "generic success message to avoid account enumeration. Rate limited."
            ),
            body=_json_body({"email": "platform@test.com"}),
        ),
        _request(
            name="Confirm platform password reset",
            method="POST",
            path_segments=base + ["password", "reset", "confirm"],
            description=(
                "Sets a new password using a valid platform password reset token issued "
                "on the public schema."
            ),
            body=_json_body(
                {
                    "token": "paste-platform-password-reset-token-here",
                    "password": "NewSecurePass1!",
                }
            ),
        ),
        _request(
            name="Validate a platform invitation token",
            method="POST",
            path_segments=base + ["invitations", "validate"],
            description=(
                "Validates a platform_invite token on the public schema and returns "
                "invitation metadata without re-exposing the raw token."
            ),
            body=_json_body({"token": "paste-platform-invitation-token-here"}),
        ),
        _request(
            name="Accept a platform invitation",
            method="POST",
            path_segments=base + ["invitations", "accept"],
            description=(
                "Accepts a platform invitation by setting password and assigning the "
                "invited platform role. Returns JWT tokens. Sole API onboarding path "
                "besides bootstrap CLI."
            ),
            body=_json_body(
                {
                    "token": "paste-platform-invitation-token-here",
                    "password": "SecurePass1!",
                }
            ),
            event=_save_platform_tokens_script(),
        ),
        _request(
            name="List platform team invitations",
            method="GET",
            path_segments=base + ["invitations"],
            description=(
                "Returns cursor-paginated platform invitations. Requires "
                "platform.platform_users view permission."
            ),
            auth=auth,
        ),
        _request(
            name="Invite a platform team member",
            method="POST",
            path_segments=base + ["invitations"],
            description=(
                "Issues a platform invitation for invite-only access. Creates a user stub "
                "without password or role until acceptance. Requires "
                "platform.platform_users edit permission."
            ),
            body=_json_body(
                {
                    "email": "new.platform.admin@example.com",
                    "full_name": "New Platform Admin",
                    "role_slug": "platform_manager",
                }
            ),
            auth=auth,
        ),
        _request(
            name="Revoke a pending platform invitation",
            method="DELETE",
            path_segments=base + ["invitations", "{invitation_id}"],
            description=(
                "Marks a pending platform invitation as revoked so it can no longer be "
                "accepted. Requires platform.platform_users edit permission."
            ),
            auth=auth,
        ),
        _request(
            name="List platform users",
            method="GET",
            path_segments=base + ["users"],
            description=(
                "Returns cursor-paginated platform users (tenant=NULL with platform "
                "roles). No POST create — invite-only onboarding. Requires "
                "platform.platform_users view permission."
            ),
            auth=auth,
        ),
        _request(
            name="Retrieve platform user detail",
            method="GET",
            path_segments=base + ["users", "{user_id}"],
            description=(
                "Returns a single platform user's profile and role assignments. Requires "
                "platform.platform_users view permission."
            ),
            auth=auth,
        ),
        _request(
            name="Replace platform user role assignments",
            method="PATCH",
            path_segments=base + ["users", "{user_id}", "roles"],
            description=(
                "Replaces the platform user's role assignments with the provided "
                "role_slugs. Requires platform.platform_users edit permission."
            ),
            body=_json_body({"role_slugs": ["platform_manager"]}),
            auth=auth,
        ),
        _request(
            name="Deactivate a platform user",
            method="POST",
            path_segments=base + ["users", "{user_id}", "deactivate"],
            description=(
                "Soft-deactivates a platform user account. Cannot deactivate the last "
                "active superadmin. Requires platform.platform_users edit permission."
            ),
            auth=auth,
        ),
        _request(
            name="Read platform settings",
            method="GET",
            path_segments=base + ["settings"],
            description=(
                "Returns the platform-wide settings singleton, creating defaults on "
                "first access. Requires platform.settings view permission."
            ),
            auth=auth,
        ),
        _request(
            name="Update platform settings",
            method="PATCH",
            path_segments=base + ["settings"],
            description=(
                "Partially updates platform-wide settings. Requires platform.settings "
                "edit permission."
            ),
            body=_json_body(
                {
                    "default_timezone": "UTC",
                    "default_language": "en",
                    "default_currency": "BDT",
                    "enable_custom_domains": False,
                }
            ),
            auth=auth,
        ),
        _request(
            name="List platform feature registry",
            method="GET",
            path_segments=base + ["features"],
            description=(
                "Returns all feature definitions in the platform registry. Requires "
                "platform.features view permission."
            ),
            auth=auth,
        ),
        _request(
            name="Create platform feature definition",
            method="POST",
            path_segments=base + ["features"],
            description=(
                "Creates a new feature registry entry. Requires platform.features edit "
                "permission."
            ),
            body=_json_body(
                {
                    "key": "custom_reports",
                    "name": "Custom Reports",
                    "description": "Tenant custom reporting module",
                    "parent_key": "",
                    "scope": "tenant",
                    "sort_order": 100,
                }
            ),
            auth=auth,
        ),
        _request(
            name="Update platform feature definition",
            method="PATCH",
            path_segments=base + ["features", "{feature_key}"],
            description=(
                "Partially updates a feature registry entry. System features cannot "
                "change key or scope. Requires platform.features edit permission."
            ),
            body=_json_body(
                {
                    "name": "Custom Reports (updated)",
                    "description": "Updated description for custom reporting module",
                    "sort_order": 110,
                }
            ),
            auth=auth,
        ),
        _request(
            name="List tenants (platform owner)",
            method="GET",
            path_segments=base + ["tenants"],
            description=(
                "Returns a cursor-paginated list of tenants for platform operators. "
                "Requires platform.tenants view permission."
            ),
            auth=auth,
        ),
        _request(
            name="Read tenant feature overrides (platform owner)",
            method="GET",
            path_segments=base + ["tenants", "{tenant_id}", "features"],
            description=(
                "Returns per-tenant feature override map. Requires platform.tenants "
                "view permission."
            ),
            auth=auth,
        ),
        _request(
            name="Update tenant feature overrides (platform owner)",
            method="PATCH",
            path_segments=base + ["tenants", "{tenant_id}", "features"],
            description=(
                "Patches per-tenant feature overrides. Requires platform.tenants edit "
                "permission and a features object in the request body."
            ),
            body=_json_body(
                {
                    "features": {
                        "branches": True,
                        "permissions": True,
                    }
                }
            ),
            auth=auth,
        ),
    ]

    return {
        "name": "12 - Platform Owner",
        "description": (
            "Platform owner console APIs — invite-only onboarding, JWT auth with "
            "platform_user claim, settings, feature registry, and tenant administration. "
            "Run login first to set platformAccessToken."
        ),
        "item": items,
    }


def ensure_collection_variables(collection: dict[str, Any]) -> None:
    variables = collection.setdefault("variable", [])
    keys = {v["key"] for v in variables}
    for key, value in [
        ("platformAccessToken", ""),
        ("platformRefreshToken", ""),
    ]:
        if key not in keys:
            variables.append({"key": key, "value": value})


def remove_stale_postman_folders(payload: dict[str, Any]) -> bool:
    """Drop removed API folders from the local Postman payload."""
    collection = payload["collection"]
    items = collection.get("item", [])
    stale_names = {
        "10 - Platform Admin - Tenancy",
    }
    filtered = [item for item in items if item.get("name") not in stale_names]
    if len(filtered) == len(items):
        return False
    collection["item"] = filtered
    return True


def merge_platform_owner_folder(payload: dict[str, Any]) -> bool:
    return _merge_folder(payload, build_platform_owner_folder())


def build_inventory_pos_folder() -> dict[str, Any]:
    """Tenant inventory, procurement, and POS endpoints (requires accessToken)."""
    inv = ["api", "v1", "inventory"]
    pos = ["api", "v1", "pos"]
    auth = _tenant_auth()
    items = [
        _request(
            name="List categories",
            method="GET",
            path_segments=inv + ["categories"],
            description="Lists product categories. Requires products view permission.",
            auth=auth,
        ),
        _request(
            name="Create category",
            method="POST",
            path_segments=inv + ["categories"],
            description="Creates a category. Requires products edit permission.",
            body=_json_body({"name": "Dairy", "slug": "dairy", "status": "active"}),
            auth=auth,
        ),
        _request(
            name="List products",
            method="GET",
            path_segments=inv + ["products"],
            description="Lists tenant catalog products. Requires products view permission.",
            auth=auth,
        ),
        _request(
            name="Create product",
            method="POST",
            path_segments=inv + ["products"],
            description="Creates a product with category and unit FKs. Requires products edit.",
            body=_json_body(
                {
                    "name": "Milk",
                    "slug": "milk",
                    "sku": "MILK-001",
                    "category": "{{categoryId}}",
                    "unit": "{{unitId}}",
                    "product_type": "single",
                    "selling_type": "retail",
                    "price": "120.00",
                    "cost": "80.00",
                    "min_qty_alert": "10",
                    "is_active": True,
                }
            ),
            auth=auth,
        ),
        _request(
            name="List low-stock products",
            method="GET",
            path_segments=inv + ["products", "low-stock"],
            description=(
                "Cross-location low stock. Tenant admin sees all branches; optional "
                "?branch=<uuid> filter."
            ),
            auth=auth,
        ),
        _request(
            name="List warehouses",
            method="GET",
            path_segments=inv + ["warehouses"],
            description="Lists warehouses. Requires inventory view permission.",
            auth=auth,
        ),
        _request(
            name="Create warehouse",
            method="POST",
            path_segments=inv + ["warehouses"],
            description="Creates a warehouse. Requires inventory edit permission.",
            body=_json_body(
                {
                    "name": "Warehouse North",
                    "code": "WH-NORTH",
                    "city": "Dhaka",
                    "is_central": True,
                    "status": "active",
                }
            ),
            auth=auth,
        ),
        _request(
            name="List suppliers",
            method="GET",
            path_segments=inv + ["suppliers"],
            description="Lists suppliers. Requires inventory view permission.",
            auth=auth,
        ),
        _request(
            name="Create supplier",
            method="POST",
            path_segments=inv + ["suppliers"],
            description="Creates a supplier. Requires inventory edit permission.",
            body=_json_body(
                {
                    "code": "SUP-001",
                    "name": "ABC Foods",
                    "email": "orders@abcfoods.example",
                    "phone": "+8801700000000",
                    "status": "active",
                }
            ),
            auth=auth,
        ),
        _request(
            name="List stock levels",
            method="GET",
            path_segments=inv + ["stock-levels"],
            description=(
                "Branch/warehouse stock levels. Admin: all branches; ?branch= filters."
            ),
            auth=auth,
        ),
        _request(
            name="Create stock adjustment",
            method="POST",
            path_segments=inv + ["stock-adjustments"],
            description="Adjusts stock quantity at a branch or warehouse.",
            body=_json_body(
                {
                    "branch": "{{branchId}}",
                    "product": "{{productId}}",
                    "quantity_after": "50",
                    "reason": "Opening stock",
                }
            ),
            auth=auth,
        ),
        _request(
            name="Create stock transfer",
            method="POST",
            path_segments=inv + ["stock-transfers"],
            description="Creates a branch-to-branch or warehouse transfer request.",
            body=_json_body(
                {
                    "transfer_type": "branch_branch",
                    "source_branch": "{{sourceBranchId}}",
                    "target_branch": "{{branchId}}",
                    "lines": [
                        {
                            "product": "{{productId}}",
                            "quantity_requested": "20",
                        }
                    ],
                }
            ),
            auth=auth,
        ),
        _request(
            name="Get replenishment options",
            method="GET",
            path_segments=inv + ["replenishment-options"],
            description="Ranked internal stock sources for a product at a branch.",
            auth=auth,
        ),
        _request(
            name="Create purchase order",
            method="POST",
            path_segments=inv + ["purchase-orders"],
            description="Creates a draft purchase order for a warehouse.",
            body=_json_body(
                {
                    "supplier": "{{supplierId}}",
                    "warehouse": "{{warehouseId}}",
                    "lines": [
                        {
                            "product": "{{productId}}",
                            "quantity_ordered": "1000",
                            "unit_cost": "80.00",
                        }
                    ],
                }
            ),
            auth=auth,
        ),
        _request(
            name="Create goods receipt",
            method="POST",
            path_segments=inv + ["goods-receipts"],
            description="Receives goods against a sent PO and increments warehouse stock.",
            body=_json_body(
                {
                    "purchase_order": "{{purchaseOrderId}}",
                    "warehouse": "{{warehouseId}}",
                    "lines": [
                        {
                            "product": "{{productId}}",
                            "quantity_received": "1000",
                        }
                    ],
                }
            ),
            auth=auth,
        ),
        _request(
            name="Validate coupon",
            method="POST",
            path_segments=inv + ["coupons", "validate"],
            description="Validates a coupon code for checkout.",
            body=_json_body({"code": "SAVE10"}),
            auth=auth,
        ),
        _request(
            name="List POS products",
            method="GET",
            path_segments=pos + ["products"],
            description="Branch-scoped sellable catalog with live stock. Requires ?branch=.",
            auth=auth,
        ),
        _request(
            name="Validate POS cart",
            method="POST",
            path_segments=pos + ["cart", "validate"],
            description="Validates line items, stock, and promotion preview.",
            body=_json_body(
                {
                    "branch": "{{branchId}}",
                    "lines": [
                        {"product": "{{productId}}", "quantity": "2"},
                    ],
                    "coupon_code": "SAVE10",
                }
            ),
            auth=auth,
        ),
        _request(
            name="POS checkout",
            method="POST",
            path_segments=pos + ["checkout"],
            description=(
                "Completes a sale with payments, promotions, and atomic stock decrement."
            ),
            body=_json_body(
                {
                    "branch": "{{branchId}}",
                    "idempotency_key": "checkout-{{$timestamp}}",
                    "lines": [
                        {
                            "product": "{{productId}}",
                            "quantity": "2",
                            "unit_price": "120.00",
                        }
                    ],
                    "payments": [
                        {"method": "cash", "amount": "100.00"},
                        {"method": "card", "amount": "140.00"},
                    ],
                    "coupon_code": "SAVE10",
                    "loyalty_points_redeemed": 50,
                }
            ),
            auth=auth,
        ),
        _request(
            name="List POS orders",
            method="GET",
            path_segments=pos + ["orders"],
            description=(
                "Lists completed POS orders. Admin: all branches; ?branch= filters."
            ),
            auth=auth,
        ),
        _request(
            name="Dashboard summary",
            method="GET",
            path_segments=inv + ["dashboard", "summary"],
            description=(
                "Aggregated KPIs. ?scope=business|branch|warehouse and optional branch filter."
            ),
            auth=auth,
        ),
    ]
    return {
        "name": "10 - Inventory & POS",
        "description": (
            "Tenant inventory catalog, stock, procurement, promotions, POS checkout, "
            "and dashboard. Requires tenant JWT (accessToken) after folder 02 login."
        ),
        "item": items,
    }


def _merge_folder(payload: dict[str, Any], folder: dict[str, Any]) -> bool:
    collection = payload["collection"]
    ensure_collection_variables(collection)
    items = collection.setdefault("item", [])
    for idx, existing in enumerate(items):
        if existing.get("name") == folder["name"]:
            items[idx] = folder
            return False
    items.append(folder)
    return True


def merge_inventory_pos_folder(payload: dict[str, Any]) -> bool:
    return _merge_folder(payload, build_inventory_pos_folder())


SYNCED_REMOTE_FOLDERS: list[tuple[str, Any]] = [
    ("12 - Platform Owner", build_platform_owner_folder),
    ("10 - Inventory & POS", build_inventory_pos_folder),
]


def regenerate_openapi() -> None:
    subprocess.run(
        [
            sys.executable,
            "manage.py",
            "spectacular",
            "--file",
            str(OPENAPI_PATH),
            "--validate",
        ],
        cwd=BACKEND_ROOT,
        check=True,
    )


def postman_request(
    method: str, url: str, body: dict[str, Any] | None = None
) -> dict[str, Any]:
    api_key = os.environ.get("POSTMAN_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "POSTMAN_API_KEY is not set; use --push only after configuring it."
        )

    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(
            f"Postman API {method} {url} failed (HTTP {exc.code}): {detail}"
        ) from exc


def _item_to_postman_request(item: dict[str, Any], folder_id: str) -> dict[str, Any]:
    request = item["request"]
    body: dict[str, Any] = {
        "name": item["name"],
        "folder": folder_id,
        "method": request["method"],
        "url": request["url"]["raw"],
        "description": request.get("description", ""),
    }
    headers = request.get("header") or []
    if headers:
        body["headerData"] = [
            {"key": header["key"], "value": header["value"]} for header in headers
        ]
    request_body = request.get("body")
    if request_body and request_body.get("mode") == "raw":
        body["dataMode"] = "raw"
        body["rawModeData"] = request_body.get("raw", "")
        language = request_body.get("options", {}).get("raw", {}).get("language")
        if language:
            body["dataOptions"] = {"raw": {"language": language}}
    auth = request.get("auth")
    if auth and auth.get("type") == "bearer":
        token = next(
            (
                entry["value"]
                for entry in auth.get("bearer", [])
                if entry.get("key") == "token"
            ),
            "",
        )
        body["auth"] = {
            "type": "bearer",
            "bearer": [{"key": "token", "value": token, "type": "string"}],
        }
    if item.get("event"):
        body["events"] = item["event"]
    return body


def _find_or_create_folder(
    remote_collection: dict[str, Any], folder_name: str, description: str
) -> str:
    for folder in remote_collection.get("item", []):
        if folder.get("name") == folder_name:
            return folder["id"]
    created = postman_request(
        "POST",
        f"https://api.getpostman.com/collections/{COLLECTION_ID}/folders",
        {"name": folder_name, "description": description},
    )
    return created["data"]["id"]


def _sync_environment_variables() -> None:
    envs = postman_request(
        "GET",
        f"https://api.getpostman.com/environments?workspace={WORKSPACE_ID}",
    )
    target = next(
        (
            env
            for env in envs.get("environments", [])
            if env.get("name") == "Sortorium - Local"
        ),
        None,
    )
    if target is None:
        print("Environment 'Sortorium - Local' not found; skipping env variable sync.")
        return

    env_id = target["uid"]
    remote_env = postman_request(
        "GET",
        f"https://api.getpostman.com/environments/{env_id}",
    )["environment"]
    keys = {value["key"] for value in remote_env.get("values", [])}
    for key in (
        "platformAccessToken",
        "platformRefreshToken",
        "categoryId",
        "unitId",
        "productId",
        "branchId",
        "sourceBranchId",
        "warehouseId",
        "supplierId",
        "purchaseOrderId",
    ):
        if key not in keys:
            remote_env["values"].append({"key": key, "value": "", "enabled": True})
    postman_request(
        "PUT",
        f"https://api.getpostman.com/environments/{env_id}",
        {"environment": remote_env},
    )
    print(f"Updated environment variables on {remote_env['name']}.")


def push_collection(payload: dict[str, Any]) -> None:
    remote = postman_request(
        "GET",
        f"https://api.getpostman.com/collections/{COLLECTION_ID}",
    )
    remote_collection = remote["collection"]
    local_items = payload["collection"].get("item", [])

    total_created = 0
    for folder_name, folder_builder in SYNCED_REMOTE_FOLDERS:
        local_folder = next(
            (item for item in local_items if item.get("name") == folder_name),
            folder_builder(),
        )
        folder_id = _find_or_create_folder(
            remote_collection,
            folder_name,
            local_folder.get("description", ""),
        )

        existing_names = set()
        for folder in remote_collection.get("item", []):
            if folder.get("name") == folder_name:
                for request in folder.get("item", []):
                    existing_names.add(request.get("name"))

        created = 0
        for item in local_folder.get("item", []):
            if item["name"] in existing_names:
                continue
            postman_request(
                "POST",
                f"https://api.getpostman.com/collections/{COLLECTION_ID}/requests",
                _item_to_postman_request(item, folder_id),
            )
            created += 1
        total_created += created
        print(
            f"Synced folder {folder_name!r}: {created} new requests, "
            f"{len(existing_names)} already present."
        )

    _sync_environment_variables()
    print(f"Pushed {total_created} new requests to collection {COLLECTION_ID}.")


def _fetch_specs_page(*, cursor: str | None) -> dict[str, Any]:
    """List one page of specs; tries workspaceId first, then legacy workspace param."""
    query_variants = [
        f"workspaceId={WORKSPACE_ID}&limit=25",
        f"workspace={WORKSPACE_ID}",
    ]
    last_error: RuntimeError | None = None
    for query in query_variants:
        url = f"https://api.getpostman.com/specs?{query}"
        if cursor:
            url += f"&cursor={cursor}"
        try:
            return postman_request("GET", url)
        except RuntimeError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise RuntimeError("Unable to list Postman specs.")


def list_specs() -> list[dict[str, Any]]:
    """Return all Spec Hub specs in the GeekSSort workspace (paginated)."""
    specs: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        data = _fetch_specs_page(cursor=cursor)
        page = data.get("data") or data.get("specs") or []
        specs.extend(page)
        meta = data.get("meta") or {}
        cursor = meta.get("nextCursor") or data.get("nextCursor")
        if not cursor:
            break
    return specs


def find_spec_id() -> str | None:
    for spec in list_specs():
        if spec.get("name") == SPEC_NAME:
            return spec.get("id") or spec.get("uid")
    return None


def _spec_upload_content(content_yaml: str, *, file_path: str) -> str:
    """Match Spec Hub root file format (JSON vs YAML)."""
    if file_path.lower().endswith(".json"):
        import yaml

        return json.dumps(yaml.safe_load(content_yaml), indent=2) + "\n"
    return content_yaml


def get_spec_root_file_path(spec_id: str) -> str:
    """Return the ROOT file path for a Spec Hub spec."""
    data = postman_request("GET", f"https://api.getpostman.com/specs/{spec_id}/files")
    files = data.get("files") or data.get("data") or []
    for entry in files:
        if entry.get("type") == "ROOT":
            return str(entry.get("path") or entry.get("name") or SPEC_ROOT_FILE)
    for entry in files:
        path = entry.get("path") or entry.get("name")
        if path:
            return str(path)
    return SPEC_ROOT_FILE


def update_spec_content(spec_id: str, content: str) -> None:
    """Upload OpenAPI content to the spec's root file."""
    file_path = get_spec_root_file_path(spec_id)
    encoded_path = urllib.parse.quote(file_path, safe="/")
    upload_content = _spec_upload_content(content, file_path=file_path)
    postman_request(
        "PATCH",
        f"https://api.getpostman.com/specs/{spec_id}/files/{encoded_path}",
        {"content": upload_content},
    )


def create_spec(content: str) -> str:
    """Create the Spec Hub spec and return its ID."""
    upload_content = _spec_upload_content(content, file_path=SPEC_ROOT_FILE)
    data = postman_request(
        "POST",
        f"https://api.getpostman.com/specs?workspaceId={WORKSPACE_ID}",
        {
            "name": SPEC_NAME,
            "type": "OPENAPI:3.0",
            "files": [
                {
                    "path": SPEC_ROOT_FILE,
                    "content": upload_content,
                    "type": "ROOT",
                }
            ],
        },
    )
    spec = data.get("spec") or data.get("data") or data
    spec_id = spec.get("id") or spec.get("uid")
    if not spec_id:
        raise RuntimeError(
            f"Postman did not return a spec id after creating {SPEC_NAME!r}: {data!r}"
        )
    print(f"Created Spec Hub spec {SPEC_NAME!r} ({spec_id}).")
    return spec_id


def push_openapi_spec() -> None:
    if not OPENAPI_PATH.exists():
        regenerate_openapi()
    content = OPENAPI_PATH.read_text(encoding="utf-8")
    try:
        spec_id = find_spec_id()
    except RuntimeError as exc:
        print(f"Warning: could not list specs ({exc}); will attempt create.")
        spec_id = None
    if spec_id is None:
        spec_id = create_spec(content)
        print(f"Uploaded OpenAPI to new Spec Hub spec {spec_id}.")
        return
    update_spec_content(spec_id, content)
    print(f"Pushed OpenAPI to Spec Hub spec {spec_id}.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push collection (and OpenAPI spec) to Postman when POSTMAN_API_KEY is set.",
    )
    parser.add_argument(
        "--regenerate-openapi",
        action="store_true",
        help="Regenerate OpenAPI YAML before syncing.",
    )
    args = parser.parse_args()

    if args.regenerate_openapi or not OPENAPI_PATH.exists():
        regenerate_openapi()
        print(f"OpenAPI written to {OPENAPI_PATH}")

    if not PAYLOAD_PATH.exists():
        print(f"Missing {PAYLOAD_PATH}; cannot update local payload.", file=sys.stderr)
        return 1

    payload = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
    removed = remove_stale_postman_folders(payload)
    platform_added = merge_platform_owner_folder(payload)
    inventory_added = merge_inventory_pos_folder(payload)
    info = payload["collection"]["info"]
    info["description"] = (
        "Sortorium PoS API — organized by user journey with example request bodies "
        "derived from serializers and integration tests. Run folders 01→12 in order."
    )
    PAYLOAD_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    for label, added in (
        ("12 - Platform Owner", platform_added),
        ("10 - Inventory & POS", inventory_added),
    ):
        action = "Added" if added else "Updated"
        print(f"{action} folder {label!r} in {PAYLOAD_PATH}")
    if removed:
        print("Removed stale folder '10 - Platform Admin - Tenancy' from payload.")

    if args.push:
        push_collection(payload)
        push_openapi_spec()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
