from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.tenancy.models import Tenant
from apps.tenancy.openapi import PLATFORM_TENANCY_TAG, TENANT_TENANCY_TAG
from apps.tenancy.permissions import IsPlatformFeaturePermission
from apps.tenancy.serializers import TenantListSerializer
from apps.tenancy.services import get_tenant_enabled_feature_keys
from drf_spectacular.utils import OpenApiResponse, extend_schema
from shared.responses import success_response
from shared.views import ModelCRUDView


@extend_schema(
    tags=[PLATFORM_TENANCY_TAG],
    summary="List tenants (platform admin)",
    responses={
        status.HTTP_200_OK: OpenApiResponse(
            description="Cursor-paginated tenant list envelope."
        ),
    },
)
class TenantAdminListView(ModelCRUDView):
    permission_classes = [
        IsPlatformFeaturePermission.require("platform.tenants", "view")
    ]
    serializer_class = TenantListSerializer

    def get_queryset(self):
        with schema_context(get_public_schema_name()):
            tenant_ids = list(
                Tenant.objects.order_by("name").values_list("id", flat=True)
            )
        return (
            Tenant.objects.filter(id__in=tenant_ids)
            .prefetch_related("domains")
            .order_by("name")
        )

    def get_success_message(self, action: str) -> str:
        return "Tenants retrieved successfully."


@extend_schema(
    tags=[TENANT_TENANCY_TAG],
    summary="List enabled features for the current tenant",
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
