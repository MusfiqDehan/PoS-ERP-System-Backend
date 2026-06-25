from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.platform_owner.openapi import PLATFORM_OWNER_TAG, envelope_responses, public_post_schema
from apps.platform_owner.serializers import (
    PlatformInvitationAcceptSerializer,
    PlatformInvitationCreateSerializer,
    PlatformInvitationListSerializer,
    PlatformInvitationTokenSerializer,
)
from apps.platform_owner.services import PlatformInvitationService
from apps.tenancy.permissions import IsPlatformFeaturePermission
from shared.openapi import document_crud_view
from shared.responses import error_response, success_response
from shared.responses.error_codes import ErrorCode
from shared.views import ModelCRUDView
from shared.views.public import PublicAPIView


@document_crud_view(
    tags=[PLATFORM_OWNER_TAG],
    operations={
        "GET": {
            "summary": "List platform team invitations",
            "description": (
                "Returns cursor-paginated platform invitations. Requires "
                "platform.platform_users view permission. Invite-only onboarding path."
            ),
            "responses": envelope_responses(
                (status.HTTP_200_OK, "Cursor-paginated invitation list envelope."),
            ),
        },
        "POST": {
            "summary": "Invite a platform team member",
            "description": (
                "Issues a platform invitation for invite-only access. Creates a user stub "
                "without password or role until acceptance. Requires platform.platform_users "
                "edit permission; superadmin role requires superadmin caller."
            ),
            "request": PlatformInvitationCreateSerializer,
            "responses": envelope_responses(
                (status.HTTP_201_CREATED, "Invitation created."),
                (status.HTTP_400_BAD_REQUEST, "Validation error."),
                (status.HTTP_403_FORBIDDEN, "Permission denied."),
            ),
        },
    },
)
class PlatformInvitationListCreateView(ModelCRUDView):
    serializer_class = PlatformInvitationListSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "superadmin_invitation"

    def get_permissions(self):
        if self.request.method == "POST":
            return [
                IsPlatformFeaturePermission.require("platform.platform_users", "edit")()
            ]
        return [
            IsPlatformFeaturePermission.require("platform.platform_users", "view")()
        ]

    def get_queryset(self):
        with schema_context(get_public_schema_name()):
            return PlatformInvitationService.list_queryset()

    def get_success_message(self, action: str) -> str:
        if action == "create":
            return "Invitation sent."
        return "Invitations retrieved successfully."

    def _create(self, request: Request) -> Response:
        serializer = PlatformInvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            invitation = PlatformInvitationService.issue(
                inviter=request.user,
                **serializer.validated_data,
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
            data=PlatformInvitationListSerializer(invitation).data,
            message=self.get_success_message("create"),
            http_status=status.HTTP_201_CREATED,
        )


@document_crud_view(
    tags=[PLATFORM_OWNER_TAG],
    operations={
        "DELETE": {
            "summary": "Revoke a pending platform invitation",
            "description": (
                "Marks a pending platform invitation as used/revoked so it can no longer "
                "be accepted. Requires platform.platform_users edit permission."
            ),
            "responses": envelope_responses(
                (status.HTTP_200_OK, "Invitation revoked."),
                (status.HTTP_400_BAD_REQUEST, "Invitation not found or already used."),
            ),
        },
    },
)
class PlatformInvitationRevokeView(ModelCRUDView):
    serializer_class = PlatformInvitationListSerializer
    permission_classes = [
        IsPlatformFeaturePermission.require("platform.platform_users", "edit")
    ]
    lookup_url_kwarg = "invitation_id"

    def get_queryset(self):
        with schema_context(get_public_schema_name()):
            return PlatformInvitationService.list_queryset().filter(used_at__isnull=True)

    def delete(self, request, invitation_id, **kwargs):
        try:
            PlatformInvitationService.revoke(invitation_id)
        except ValueError as exc:
            return error_response(
                message=str(exc),
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data={}, message="Invitation revoked.")


@public_post_schema(
    request=PlatformInvitationTokenSerializer,
    summary="Validate a platform invitation token",
    description=(
        "Validates a platform_invite token on the public schema and returns invitation "
        "metadata without re-exposing the raw token."
    ),
    responses=envelope_responses(
        (status.HTTP_200_OK, "Token is valid."),
        (status.HTTP_400_BAD_REQUEST, "Invalid or expired token."),
    ),
)
class PlatformInvitationValidateView(PublicAPIView):

    def post(self, request):
        serializer = PlatformInvitationTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invitation = PlatformInvitationService.validate(
            serializer.validated_data["token"]
        )
        if invitation is None:
            return error_response(
                message="Invalid or expired token.",
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(
            data=PlatformInvitationService.serialize(invitation),
            message="Token is valid.",
        )


@public_post_schema(
    request=PlatformInvitationAcceptSerializer,
    summary="Accept a platform invitation",
    description=(
        "Accepts a platform invitation by setting password and assigning the invited "
        "platform role. Returns JWT tokens. Sole API onboarding path besides bootstrap."
    ),
    responses=envelope_responses(
        (status.HTTP_200_OK, "Invitation accepted; session created."),
        (status.HTTP_400_BAD_REQUEST, "Invalid token or password validation error."),
    ),
)
class PlatformInvitationAcceptView(PublicAPIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "platform_password_setup"

    def post(self, request):
        serializer = PlatformInvitationAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = PlatformInvitationService.accept(
                raw_token=serializer.validated_data["token"],
                password=serializer.validated_data["password"],
            )
        except ValueError as exc:
            return error_response(
                message=str(exc),
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(
            data=result,
            message="Invitation accepted.",
        )
