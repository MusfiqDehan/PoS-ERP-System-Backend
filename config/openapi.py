"""drf-spectacular hooks and helpers for Sortorium OpenAPI schema."""

from __future__ import annotations

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class MissingOperationDescriptionsError(Exception):
    """Raised when schema generation finds undocumented API operations."""


def collect_missing_operation_descriptions(schema: dict) -> list[str]:
    missing: list[str] = []
    for path, path_item in schema.get("paths", {}).items():
        if not path.startswith("/api/v1/"):
            continue
        for method, operation in path_item.items():
            if method in {"parameters"} or method.startswith("x-"):
                continue
            if not str(operation.get("description", "")).strip():
                missing.append(f"{method.upper()} {path}")
    return missing


def enforce_operation_descriptions(result, generator, request, public):
    missing = collect_missing_operation_descriptions(result)
    if not missing:
        return result

    message = "OpenAPI operations missing description: " + ", ".join(sorted(missing))
    if settings.DEBUG:
        raise MissingOperationDescriptionsError(message)
    logger.warning(message)
    return result
