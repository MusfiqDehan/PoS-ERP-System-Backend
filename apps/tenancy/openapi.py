"""drf-spectacular helpers for tenancy API documentation."""

from drf_spectacular.utils import OpenApiResponse, extend_schema

PUBLIC_TENANCY_TAG = "Tenancy - Public"
PLATFORM_TENANCY_TAG = "Tenancy - Platform Admin"
TENANT_TENANCY_TAG = "Tenancy - Tenant"


def public_post_schema(*, request, responses, summary: str):
    """Document a public-schema POST endpoint with no auth requirement."""

    return extend_schema(
        tags=[PUBLIC_TENANCY_TAG],
        summary=summary,
        request=request,
        responses=responses,
        auth=[],
    )


def envelope_responses(*descriptions: tuple[int, str]) -> dict[int, OpenApiResponse]:
    return {
        status_code: OpenApiResponse(
            description=description,
        )
        for status_code, description in descriptions
    }
