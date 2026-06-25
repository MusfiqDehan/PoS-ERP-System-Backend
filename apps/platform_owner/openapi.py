"""drf-spectacular helpers for platform owner API documentation."""

from drf_spectacular.utils import extend_schema

from shared.openapi import envelope_responses

PLATFORM_OWNER_TAG = "Platform Owner"

__all__ = [
    "PLATFORM_OWNER_TAG",
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
        tags=[PLATFORM_OWNER_TAG],
        summary=summary,
        description=description,
        request=request,
        responses=responses,
        auth=[],
    )
