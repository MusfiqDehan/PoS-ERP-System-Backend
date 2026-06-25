from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.platform_owner.openapi import PLATFORM_OWNER_TAG, envelope_responses
from apps.platform_owner.serializers import (
    PlatformUserListSerializer,
    PlatformUserRolesSerializer,
)
from apps.platform_owner.services import PlatformUserService
from apps.tenancy.permissions import IsPlatformFeaturePermission
from drf_spectacular.utils import OpenApiResponse, extend_schema
from shared.openapi import document_crud_view
from shared.responses import error_response, success_response
from shared.responses.error_codes import ErrorCode
from shared.views import ModelCRUDView


@document_crud_view(
    tags=[PLATFORM_OWNER_TAG],
    operations={
        "GET": {
            "summary": "List platform users",
            "description": (
                "Returns cursor-paginated platform users (tenant=NULL with platform "
                "roles). No POST create — invite-only onboarding. Requires "
                "platform.platform_users view permission."
            ),
            "responses": {
                status.HTTP_200_OK: OpenApiResponse(
                    description="Cursor-paginated platform user list envelope."
                ),
            },
        },
        "POST": {
            "summary": "Direct platform user creation (not allowed)",
            "description": "Returns 405 — platform users are onboarded via invitation only.",
            "responses": envelope_responses(
                (
                    status.HTTP_405_METHOD_NOT_ALLOWED,
                    "Direct user creation not allowed (invite-only).",
                ),
            ),
        },
    },
)
class PlatformUserListView(ModelCRUDView):
    serializer_class = PlatformUserListSerializer
    permission_classes = [
        IsPlatformFeaturePermission.require("platform.platform_users", "view")
    ]

    def get_queryset(self):
        with schema_context(get_public_schema_name()):
            return PlatformUserService.queryset()

    def get_success_message(self, action: str) -> str:
        return "Platform users retrieved successfully."

    def post(self, request: Request, pk=None, **kwargs) -> Response:
        return error_response(
            message="Platform users are created via invitation only.",
            error_code=str(ErrorCode.VALIDATION_ERROR),
            http_status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


@document_crud_view(
    tags=[PLATFORM_OWNER_TAG],
    operations={
        "GET": {
            "summary": "Retrieve platform user detail",
            "description": (
                "Returns a single platform user's profile and role assignments. Requires "
                "platform.platform_users view permission."
            ),
            "responses": envelope_responses(
                (status.HTTP_200_OK, "Platform user detail envelope."),
                (status.HTTP_404_NOT_FOUND, "Platform user not found."),
            ),
        },
    },
)
class PlatformUserDetailView(ModelCRUDView):
    serializer_class = PlatformUserListSerializer
    permission_classes = [
        IsPlatformFeaturePermission.require("platform.platform_users", "view")
    ]
    lookup_url_kwarg = "user_id"

    def get_queryset(self):
        with schema_context(get_public_schema_name()):
            return PlatformUserService.queryset()

    def get_success_message(self, action: str) -> str:
        return "Platform user retrieved."

    def get(self, request, user_id, **kwargs):
        return self._retrieve(user_id)


@extend_schema(
    tags=[PLATFORM_OWNER_TAG],
    summary="Replace platform user role assignments",
    description=(
        "Replaces the platform user's role assignments with the provided role_slugs. "
        "Requires platform.platform_users edit permission."
    ),
    request=PlatformUserRolesSerializer,
    responses=envelope_responses(
        (status.HTTP_200_OK, "Roles updated."),
        (status.HTTP_400_BAD_REQUEST, "Validation or lockout error."),
        (status.HTTP_403_FORBIDDEN, "Permission denied."),
        (status.HTTP_404_NOT_FOUND, "Platform user not found."),
    ),
)
class PlatformUserRolesView(APIView):
    permission_classes = [
        IsPlatformFeaturePermission.require("platform.platform_users", "edit")
    ]

    def patch(self, request, user_id):
        user = PlatformUserService.get_platform_user(user_id)
        if user is None:
            return error_response(
                message="Platform user not found.",
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_404_NOT_FOUND,
            )
        serializer = PlatformUserRolesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            slugs = PlatformUserService.replace_roles(
                actor=request.user,
                user=user,
                role_slugs=serializer.validated_data["role_slugs"],
            )
        except PermissionError as exc:
            return error_response(
                message=str(exc),
                error_code=str(ErrorCode.PERMISSION_DENIED),
                http_status=status.HTTP_403_FORBIDDEN,
            )
        except ValueError as exc:
            return error_response(
                message=str(exc),
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(
            data={"platform_roles": slugs},
            message="Roles updated.",
        )


@extend_schema(
    tags=[PLATFORM_OWNER_TAG],
    summary="Deactivate a platform user",
    description=(
        "Soft-deactivates a platform user account. Cannot deactivate the last active "
        "superadmin. Requires platform.platform_users edit permission."
    ),
    responses=envelope_responses(
        (status.HTTP_200_OK, "User deactivated."),
        (status.HTTP_400_BAD_REQUEST, "Lockout or validation error."),
        (status.HTTP_404_NOT_FOUND, "Platform user not found."),
    ),
)
class PlatformUserDeactivateView(APIView):
    permission_classes = [
        IsPlatformFeaturePermission.require("platform.platform_users", "edit")
    ]

    def post(self, request, user_id):
        user = PlatformUserService.get_platform_user(user_id)
        if user is None:
            return error_response(
                message="Platform user not found.",
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_404_NOT_FOUND,
            )
        try:
            PlatformUserService.deactivate(actor=request.user, user=user)
        except ValueError as exc:
            return error_response(
                message=str(exc),
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data={}, message="User deactivated.")
