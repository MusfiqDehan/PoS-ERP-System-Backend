from rest_framework import status
from drf_spectacular.utils import extend_schema

from apps.billing.openapi import PUBLIC_BILLING_TAG, envelope_responses
from apps.billing.services.public_catalog import list_public_packages
from shared.responses import success_response
from shared.views.public import PublicAPIView


@extend_schema(
    tags=[PUBLIC_BILLING_TAG],
    summary="List public subscription packages",
    description=(
        "Returns active, publicly visible subscription packages for the marketing site "
        "and tenant self-registration. Unauthenticated; served from the public schema. "
        "Results are cached for up to 30 minutes and invalidated when packages change."
    ),
    responses=envelope_responses(
        (status.HTTP_200_OK, "Public packages retrieved successfully."),
    ),
    auth=[],
)
class PublicPackageListView(PublicAPIView):
    def get(self, request):
        items = list_public_packages()
        return success_response(
            data={"items": items},
            message="Public packages retrieved successfully.",
        )
