"""drf-spectacular helpers for inventory API documentation."""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import OpenApiResponse
from rest_framework import serializers, status

from shared.openapi import document_api_view, document_crud_view, envelope_responses

INVENTORY_TENANT_TAG = "Inventory - Tenant"
POS_TENANT_TAG = "POS - Tenant"


def inventory_get_responses(
    serializer: type[serializers.Serializer],
    *,
    many: bool = False,
    include_not_found: bool = False,
) -> dict[int, Any]:
    response_schema: Any = serializer(many=True) if many else serializer
    responses: dict[int, Any] = {
        status.HTTP_200_OK: response_schema,
        status.HTTP_400_BAD_REQUEST: OpenApiResponse(description="Validation error."),
    }
    if include_not_found:
        responses[status.HTTP_404_NOT_FOUND] = OpenApiResponse(
            description="Resource not found."
        )
    return responses


def inventory_post_responses(
    serializer: type[serializers.Serializer],
    *,
    created: bool = False,
    include_not_found: bool = True,
    include_forbidden: bool = False,
) -> dict[int, Any]:
    success_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    responses: dict[int, Any] = {
        success_status: serializer,
        status.HTTP_400_BAD_REQUEST: OpenApiResponse(description="Validation error."),
    }
    if include_not_found:
        responses[status.HTTP_404_NOT_FOUND] = OpenApiResponse(
            description="Resource not found."
        )
    if include_forbidden:
        responses[status.HTTP_403_FORBIDDEN] = OpenApiResponse(
            description="Permission denied."
        )
    return responses


def document_inventory_get_api_view(
    *,
    tags: list[str],
    summary: str,
    description: str,
    response_serializer: type[serializers.Serializer],
    many: bool = False,
    include_not_found: bool = False,
) -> Any:
    return document_api_view(
        tags=tags,
        summary=summary,
        description=description,
        methods=["GET"],
        responses=inventory_get_responses(
            response_serializer,
            many=many,
            include_not_found=include_not_found,
        ),
    )


def document_inventory_post_api_view(
    *,
    tags: list[str],
    summary: str,
    description: str,
    request_serializer: type[serializers.Serializer],
    response_serializer: type[serializers.Serializer],
    created: bool = False,
    include_not_found: bool = True,
    include_forbidden: bool = False,
) -> Any:
    return document_api_view(
        tags=tags,
        summary=summary,
        description=description,
        methods=["POST"],
        request=request_serializer,
        responses=inventory_post_responses(
            response_serializer,
            created=created,
            include_not_found=include_not_found,
            include_forbidden=include_forbidden,
        ),
    )


__all__ = [
    "INVENTORY_TENANT_TAG",
    "POS_TENANT_TAG",
    "document_api_view",
    "document_crud_view",
    "document_inventory_get_api_view",
    "document_inventory_post_api_view",
    "envelope_responses",
    "inventory_get_responses",
    "inventory_post_responses",
]
