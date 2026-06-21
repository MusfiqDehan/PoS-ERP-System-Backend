"""Tenant branding settings endpoints."""

from django_tenants.utils import get_public_schema_name
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.access.permissions import CanManageTenantBranding
from apps.tenancy.openapi import TENANT_TENANCY_TAG
from apps.tenancy.serializers.branding import TenantBrandingSerializer
from drf_spectacular.utils import OpenApiResponse, extend_schema
from shared.responses import error_response, success_response
from shared.responses.error_codes import ErrorCode
from shared.services.asset_attachment import (
    AssetAttachmentError,
    AssetAttachmentService,
    TENANT_COMPANY_LOGO_FIELD,
    TENANT_COMPANY_LOGO_ROLE,
    serialize_asset_summary,
)


def _resolve_request_tenant(request):
    tenant = getattr(request, "tenant", None)
    if tenant is None or tenant.schema_name == get_public_schema_name():
        return None
    return tenant


@extend_schema(
    tags=[TENANT_TENANCY_TAG],
    summary="Read current tenant branding settings",
    description=(
        "Returns branding settings for the resolved tenant, including company display "
        "metadata. Requires CanManageTenantBranding permission."
    ),
    responses={
        status.HTTP_200_OK: OpenApiResponse(description="Tenant branding envelope."),
    },
)
class TenantBrandingView(APIView):
    permission_classes = [IsAuthenticated, CanManageTenantBranding]

    def get(self, request):
        tenant = _resolve_request_tenant(request)
        if tenant is None:
            return error_response(
                message="Tenant context is required.",
                error_code=str(ErrorCode.NOT_FOUND),
                http_status=status.HTTP_404_NOT_FOUND,
            )
        return success_response(
            data=TenantBrandingSerializer(tenant).data,
            message="Tenant branding retrieved.",
        )


@extend_schema(
    tags=[TENANT_TENANCY_TAG],
    summary="Upload or replace current tenant company logo",
    description=(
        "Uploads or replaces the tenant company logo using multipart form data. "
        "Requires CanManageTenantBranding permission."
    ),
    request={
        "multipart/form-data": {
            "type": "object",
            "properties": {"file": {"type": "string", "format": "binary"}},
            "required": ["file"],
        }
    },
    responses={
        status.HTTP_200_OK: OpenApiResponse(
            description="Company logo updated envelope."
        ),
    },
)
class TenantCompanyLogoView(APIView):
    permission_classes = [IsAuthenticated, CanManageTenantBranding]
    parser_classes = [MultiPartParser, FormParser]

    def put(self, request):
        return self._upload(request)

    def patch(self, request):
        return self._upload(request)

    def _upload(self, request):
        tenant = _resolve_request_tenant(request)
        if tenant is None:
            return error_response(
                message="Tenant context is required.",
                error_code=str(ErrorCode.NOT_FOUND),
                http_status=status.HTTP_404_NOT_FOUND,
            )
        uploaded_file = request.FILES.get("file")
        if uploaded_file is None:
            return error_response(
                message="No file uploaded.",
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            AssetAttachmentService.attach_image(
                file=uploaded_file,
                parent=tenant,
                role=TENANT_COMPANY_LOGO_ROLE,
                field_name=TENANT_COMPANY_LOGO_FIELD,
                actor=request.user,
            )
        except AssetAttachmentError as exc:
            return error_response(
                message=str(exc),
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(
            data={
                "company_logo": serialize_asset_summary(tenant.get_company_logo_asset())
            },
            message="Company logo updated.",
        )

    @extend_schema(
        tags=[TENANT_TENANCY_TAG],
        summary="Remove current tenant company logo",
        description=(
            "Removes the current tenant company logo attachment. Requires "
            "CanManageTenantBranding permission."
        ),
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description="Company logo removed envelope."
            ),
        },
    )
    def delete(self, request):
        tenant = _resolve_request_tenant(request)
        if tenant is None:
            return error_response(
                message="Tenant context is required.",
                error_code=str(ErrorCode.NOT_FOUND),
                http_status=status.HTTP_404_NOT_FOUND,
            )
        AssetAttachmentService.remove_primary(
            parent=tenant,
            role=TENANT_COMPANY_LOGO_ROLE,
            field_name=TENANT_COMPANY_LOGO_FIELD,
            actor=request.user,
        )
        return success_response(
            data={},
            message="Company logo removed.",
        )
