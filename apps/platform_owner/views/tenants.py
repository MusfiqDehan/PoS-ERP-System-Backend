from rest_framework import status
from rest_framework.views import APIView

from apps.platform_owner.openapi import PLATFORM_OWNER_TAG
from apps.tenancy.permissions import IsPlatformFeaturePermission
from apps.tenancy.serializers import TenantListSerializer
from apps.tenancy.services import TenantAdministrationService
from drf_spectacular.utils import OpenApiResponse, extend_schema
from shared.openapi import document_crud_view, envelope_responses
from shared.responses import error_response, success_response
from shared.responses.error_codes import ErrorCode
from shared.views import ModelCRUDView


@document_crud_view(
    tags=[PLATFORM_OWNER_TAG],
    operations={
        "GET": {
            "summary": "List tenants (platform owner)",
            "description": (
                "Returns a cursor-paginated list of tenants for platform operators. "
                "Requires platform.tenants view permission."
            ),
            "responses": {
                status.HTTP_200_OK: OpenApiResponse(
                    description="Cursor-paginated tenant list envelope."
                ),
            },
        },
    },
)
class PlatformTenantListView(ModelCRUDView):
    permission_classes = [
        IsPlatformFeaturePermission.require("platform.tenants", "view")
    ]
    serializer_class = TenantListSerializer

    def get_queryset(self):
        return TenantAdministrationService.list_tenants_queryset()

    def get_success_message(self, action: str) -> str:
        return "Tenants retrieved successfully."


@extend_schema(
    methods=["GET"],
    tags=[PLATFORM_OWNER_TAG],
    summary="Read tenant feature overrides (platform owner)",
    description=(
        "Returns per-tenant feature override map. Requires platform.tenants view "
        "permission."
    ),
    responses=envelope_responses(
        (status.HTTP_200_OK, "Tenant feature overrides envelope."),
        (status.HTTP_404_NOT_FOUND, "Tenant not found."),
    ),
)
@extend_schema(
    methods=["PATCH"],
    tags=[PLATFORM_OWNER_TAG],
    summary="Update tenant feature overrides (platform owner)",
    description=(
        "Patches per-tenant feature overrides. Requires platform.tenants edit "
        "permission and a features object in the request body."
    ),
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "features": {
                    "type": "object",
                    "additionalProperties": {"type": "boolean"},
                }
            },
            "required": ["features"],
        }
    },
    responses=envelope_responses(
        (status.HTTP_200_OK, "Updated tenant feature overrides envelope."),
        (status.HTTP_400_BAD_REQUEST, "Validation error."),
        (status.HTTP_404_NOT_FOUND, "Tenant not found."),
    ),
)
class PlatformTenantFeatureOverrideView(APIView):
    permission_classes = [
        IsPlatformFeaturePermission.require("platform.tenants", "edit")
    ]

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsPlatformFeaturePermission.require("platform.tenants", "view")()]
        return [perm() for perm in self.permission_classes]

    def get(self, request, tenant_id):
        features = TenantAdministrationService.get_tenant_feature_overrides(tenant_id)
        if features is None:
            return error_response(
                message="Tenant not found.",
                error_code=str(ErrorCode.TENANT_NOT_FOUND),
                http_status=status.HTTP_404_NOT_FOUND,
            )
        return success_response(
            data={"features": features},
            message="Tenant feature overrides retrieved.",
        )

    def patch(self, request, tenant_id):
        overrides = request.data.get("features")
        if not isinstance(overrides, dict):
            return error_response(
                message="features object is required.",
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        merged = TenantAdministrationService.patch_tenant_feature_overrides_for_admin(
            tenant_id,
            overrides,
        )
        if merged is None:
            return error_response(
                message="Tenant not found.",
                error_code=str(ErrorCode.TENANT_NOT_FOUND),
                http_status=status.HTTP_404_NOT_FOUND,
            )
        return success_response(
            data={"features": merged},
            message="Tenant feature overrides updated.",
        )
