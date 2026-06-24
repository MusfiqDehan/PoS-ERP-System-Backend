"""OpenAPI schema completeness tests for operation descriptions."""

from __future__ import annotations

import pytest
from drf_spectacular.generators import SchemaGenerator


def _load_schema() -> dict:
    return SchemaGenerator().get_schema(request=None, public=True)


def _api_operations(schema: dict) -> list[tuple[str, str, dict]]:
    operations: list[tuple[str, str, dict]] = []
    for path, path_item in schema.get("paths", {}).items():
        if not path.startswith("/api/v1/"):
            continue
        for method, operation in path_item.items():
            if method in {"parameters"} or method.startswith("x-"):
                continue
            operations.append((method.upper(), path, operation))
    return operations


@pytest.mark.django_db
def test_openapi_operations_have_descriptions():
    schema = _load_schema()
    missing = [
        f"{method} {path}"
        for method, path, operation in _api_operations(schema)
        if not str(operation.get("description", "")).strip()
    ]
    assert not missing, "OpenAPI operations missing description:\n" + "\n".join(
        sorted(missing)
    )


@pytest.mark.django_db
def test_openapi_tags_have_descriptions():
    schema = _load_schema()
    used_tags = {
        tag
        for _, _, operation in _api_operations(schema)
        for tag in operation.get("tags", [])
    }
    tag_descriptions = {
        entry["name"]: str(entry.get("description", "")).strip()
        for entry in schema.get("tags", [])
        if entry.get("name")
    }
    missing = sorted(tag for tag in used_tags if not tag_descriptions.get(tag, ""))
    assert not missing, "OpenAPI tags missing description metadata:\n" + "\n".join(
        missing
    )
