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
        _request(
            name="Get platform permissions (legacy alias)",
            method="GET",
            path_segments=[
                "api",
                "v1",
                "tenancy",
                "admin",
                "me",
                "platform-permissions",
            ],
            description=(
                "Legacy alias for platform permissions during migration. Prefer "
                "GET /api/v1/platform-owner/me/permissions/. Requires platform JWT."
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


def merge_platform_owner_folder(payload: dict[str, Any]) -> bool:
    collection = payload["collection"]
    ensure_collection_variables(collection)
    folder = build_platform_owner_folder()
    items = collection.setdefault("item", [])
    for idx, existing in enumerate(items):
        if existing.get("name") == folder["name"]:
            items[idx] = folder
            return False
    items.append(folder)
    return True


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
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


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


def _find_or_create_platform_folder(remote_collection: dict[str, Any]) -> str:
    for folder in remote_collection.get("item", []):
        if folder.get("name") == "12 - Platform Owner":
            return folder["id"]
    created = postman_request(
        "POST",
        f"https://api.getpostman.com/collections/{COLLECTION_ID}/folders",
        {
            "name": "12 - Platform Owner",
            "description": (
                "Platform owner console APIs — invite-only onboarding, JWT auth with "
                "platform_user claim, settings, feature registry, and tenant "
                "administration. Run login first to set platformAccessToken."
            ),
        },
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
    for key in ("platformAccessToken", "platformRefreshToken"):
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
    platform_folder = next(
        (item for item in local_items if item.get("name") == "12 - Platform Owner"),
        build_platform_owner_folder(),
    )
    folder_id = _find_or_create_platform_folder(remote_collection)

    existing_names = set()
    for folder in remote_collection.get("item", []):
        if folder.get("name") == "12 - Platform Owner":
            for request in folder.get("item", []):
                existing_names.add(request.get("name"))

    created = 0
    for item in platform_folder.get("item", []):
        if item["name"] in existing_names:
            continue
        postman_request(
            "POST",
            f"https://api.getpostman.com/collections/{COLLECTION_ID}/requests",
            _item_to_postman_request(item, folder_id),
        )
        created += 1

    _sync_environment_variables()
    print(
        f"Synced folder '12 - Platform Owner' on collection {COLLECTION_ID} "
        f"({created} new requests, {len(existing_names)} already present)."
    )


def find_spec_id() -> str | None:
    try:
        data = postman_request(
            "GET",
            f"https://api.getpostman.com/specs?workspace={WORKSPACE_ID}",
        )
    except urllib.error.HTTPError:
        return None
    specs = data.get("data") or data.get("specs") or []
    for spec in specs:
        if spec.get("name") == SPEC_NAME:
            return spec.get("id") or spec.get("uid")
    return None


def push_openapi_spec() -> None:
    if not OPENAPI_PATH.exists():
        regenerate_openapi()
    spec_id = find_spec_id()
    if not spec_id:
        print(f"Spec {SPEC_NAME!r} not found in Postman; skipping spec push.")
        return
    content = OPENAPI_PATH.read_text(encoding="utf-8")
    postman_request(
        "PUT",
        f"https://api.getpostman.com/specs/{spec_id}/files/root",
        {"content": content, "type": "root"},
    )
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
    added = merge_platform_owner_folder(payload)
    info = payload["collection"]["info"]
    info["description"] = (
        "Sortorium PoS API — organized by user journey with example request bodies "
        "derived from serializers and integration tests. Run folders 01→12 in order."
    )
    PAYLOAD_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    action = "Added" if added else "Updated"
    print(f"{action} folder '12 - Platform Owner' in {PAYLOAD_PATH}")

    if args.push:
        push_collection(payload)
        push_openapi_spec()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
