from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.response import Response

_OMIT = object()


def omit_empty(value: Any, *, preserve_empty_lists: bool = False) -> Any:
    """Recursively remove null, empty dict, and empty list values."""
    if value is None:
        return _OMIT

    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            keep_empty_list = preserve_empty_lists or key == "items"
            cleaned_item = omit_empty(item, preserve_empty_lists=keep_empty_list)
            if cleaned_item is not _OMIT:
                cleaned[key] = cleaned_item
        if not cleaned:
            return _OMIT
        return cleaned

    if isinstance(value, list):
        if not value and not preserve_empty_lists:
            return _OMIT
        cleaned_list = []
        for item in value:
            cleaned_item = omit_empty(item, preserve_empty_lists=False)
            if cleaned_item is not _OMIT:
                cleaned_list.append(cleaned_item)
        if not cleaned_list and not preserve_empty_lists:
            return _OMIT
        return cleaned_list

    return value


def _build_envelope(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned = omit_empty(payload)
    if not isinstance(cleaned, dict):
        return payload
    return cleaned


def success_response(
    *,
    data: Any,
    message: str = "Operation successful.",
    http_status: int = status.HTTP_200_OK,
) -> Response:
    body = _build_envelope(
        {
            "success": True,
            "message": message,
            "data": data,
        }
    )
    return Response(body, status=http_status)


def list_success_response(
    *,
    items: list[Any],
    pagination: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
    message: str = "Resources retrieved successfully.",
    http_status: int = status.HTTP_200_OK,
) -> Response:
    data: dict[str, Any] = {"items": items}
    if pagination is not None:
        data["pagination"] = pagination
    if meta is not None:
        data["meta"] = meta

    body = _build_envelope(
        {
            "success": True,
            "message": message,
            "data": data,
        }
    )
    return Response(body, status=http_status)


def error_response(
    *,
    message: str,
    error_code: str,
    errors: dict[str, list[str]] | list[str] | None = None,
    http_status: int = status.HTTP_400_BAD_REQUEST,
) -> Response:
    payload: dict[str, Any] = {
        "success": False,
        "message": message,
        "error_code": error_code,
    }
    if errors is not None:
        payload["errors"] = errors

    body = _build_envelope(payload)
    return Response(body, status=http_status)
