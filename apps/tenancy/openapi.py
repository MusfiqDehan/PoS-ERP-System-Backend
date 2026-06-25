"""drf-spectacular helpers for tenancy API documentation."""

from drf_spectacular.utils import extend_schema

from shared.openapi import envelope_responses

PUBLIC_TENANCY_TAG = "Tenancy - Public"
TENANT_TENANCY_TAG = "Tenancy - Tenant"

__all__ = [
    "PUBLIC_TENANCY_TAG",
    "TENANT_TENANCY_TAG",
    "envelope_responses",
    "public_post_schema",
]


def public_post_schema(
    *,
    request,
    responses,
    summary: str,
    description: str,
):
    """Document a public-schema POST endpoint with no auth requirement."""

    return extend_schema(
        tags=[PUBLIC_TENANCY_TAG],
        summary=summary,
        description=description,
        request=request,
        responses=responses,
        auth=[],
    )
