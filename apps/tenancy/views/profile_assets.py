"""Profile picture upload endpoints."""

from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.tenancy.openapi import TENANT_TENANCY_TAG
from drf_spectacular.utils import OpenApiResponse, extend_schema
from shared.responses import error_response, success_response
from shared.responses.error_codes import ErrorCode
from shared.services.asset_attachment import (
    AssetAttachmentError,
    AssetAttachmentService,
    USER_PROFILE_PICTURE_FIELD,
    USER_PROFILE_PICTURE_ROLE,
    serialize_asset_summary,
)


@extend_schema(
    tags=[TENANT_TENANCY_TAG],
    summary="Upload or replace authenticated user profile picture",
    request={
        "multipart/form-data": {
            "type": "object",
            "properties": {"file": {"type": "string", "format": "binary"}},
            "required": ["file"],
        }
    },
    responses={
        status.HTTP_200_OK: OpenApiResponse(
            description="Profile picture updated envelope."
        ),
    },
)
class ProfilePictureView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def put(self, request):
        return self._upload(request)

    def patch(self, request):
        return self._upload(request)

    def _upload(self, request):
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
                parent=request.user,
                role=USER_PROFILE_PICTURE_ROLE,
                field_name=USER_PROFILE_PICTURE_FIELD,
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
                "profile_picture": serialize_asset_summary(
                    request.user.get_profile_picture_asset()
                )
            },
            message="Profile picture updated.",
        )

    @extend_schema(
        tags=[TENANT_TENANCY_TAG],
        summary="Remove authenticated user profile picture",
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description="Profile picture removed envelope."
            ),
        },
    )
    def delete(self, request):
        AssetAttachmentService.remove_primary(
            parent=request.user,
            role=USER_PROFILE_PICTURE_ROLE,
            field_name=USER_PROFILE_PICTURE_FIELD,
            actor=request.user,
        )
        return success_response(
            data={},
            message="Profile picture removed.",
        )
