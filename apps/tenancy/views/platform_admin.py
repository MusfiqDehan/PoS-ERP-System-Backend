from django_tenants.utils import get_public_schema_name
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.tenancy.openapi import TENANT_TENANCY_TAG
from apps.tenancy.services import get_tenant_enabled_feature_keys
from shared.responses import success_response


@extend_schema(
    tags=[TENANT_TENANCY_TAG],
    summary="List enabled features for the current tenant",
    description=(
        "Returns feature keys enabled for the tenant resolved from the request host. "
        "Requires authentication; returns an empty feature list when no tenant context "
        "is available."
    ),
    responses={
        status.HTTP_200_OK: OpenApiResponse(
            description="Feature keys enabled for the resolved tenant."
        ),
    },
)
class CurrentTenantFeaturesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant = getattr(request, "tenant", None)
        if tenant is None or tenant.schema_name == get_public_schema_name():
            return success_response(data={"features": []}, message="No tenant context.")
        features = sorted(get_tenant_enabled_feature_keys(tenant))
        return success_response(
            data={"features": features}, message="Features retrieved."
        )
