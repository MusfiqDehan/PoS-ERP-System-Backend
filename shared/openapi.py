"""Shared drf-spectacular helpers for Sortorium API documentation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status


def envelope_responses(*descriptions: tuple[int, str]) -> dict[int, OpenApiResponse]:
    return {
        status_code: OpenApiResponse(description=description)
        for status_code, description in descriptions
    }


def document_api_view(
    *,
    tags: list[str],
    summary: str,
    description: str,
    **kwargs: Any,
) -> Callable[[Any], Any]:
    """Decorator factory that requires an operation description."""

    def decorator(view_or_method: Any) -> Any:
        return extend_schema(
            tags=tags,
            summary=summary,
            description=description,
            **kwargs,
        )(view_or_method)

    return decorator


def document_crud_view(
    *,
    tags: list[str],
    operations: dict[str, dict[str, Any]],
) -> Callable[[type[Any]], type[Any]]:
    """Apply per-method extend_schema decorators to ModelCRUDView subclasses."""

    documented_methods = {method.upper() for method in operations}

    def decorator(view_cls: type[Any]) -> type[Any]:
        decorated: Any = view_cls
        for method in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            if method not in documented_methods:
                decorated = extend_schema(methods=[method], exclude=True)(decorated)
        for method, meta in reversed(list(operations.items())):
            method_upper = method.upper()
            responses = meta.get("responses")
            if responses is None:
                if method_upper == "POST":
                    responses = envelope_responses(
                        (status.HTTP_201_CREATED, "Resource created envelope."),
                        (status.HTTP_400_BAD_REQUEST, "Validation error."),
                    )
                elif method_upper == "DELETE":
                    responses = {
                        status.HTTP_204_NO_CONTENT: OpenApiResponse(
                            description="Resource deleted."
                        )
                    }
                else:
                    responses = envelope_responses(
                        (status.HTTP_200_OK, "Success envelope."),
                        (status.HTTP_400_BAD_REQUEST, "Validation error."),
                    )
            schema_kwargs: dict[str, Any] = {
                "methods": [method_upper],
                "tags": tags,
                "summary": meta["summary"],
                "description": meta["description"],
                "responses": responses,
            }
            if "request" in meta:
                schema_kwargs["request"] = meta["request"]
            decorated = extend_schema(**schema_kwargs)(decorated)
        return decorated

    return decorator
