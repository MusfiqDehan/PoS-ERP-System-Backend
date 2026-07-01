from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.access.permissions import CanManageEmployeeInvitations
from apps.tenancy.openapi import (
    TENANT_TENANCY_TAG,
    envelope_responses,
    public_post_schema,
)
from apps.tenancy.serializers.employee_invitation import (
    TenantEmployeeInvitationAcceptSerializer,
    TenantEmployeeInvitationCreateSerializer,
    TenantEmployeeInvitationListSerializer,
    TenantEmployeeInvitationTokenSerializer,
)
from apps.tenancy.services.employee_invitation import TenantInvitationService
from shared.openapi import document_crud_view
from shared.responses import error_response, success_response
from shared.responses.error_codes import ErrorCode
from shared.views import ModelCRUDView
from shared.views.public import PublicAPIView


@document_crud_view(
    tags=[TENANT_TENANCY_TAG],
    operations={
        "GET": {
            "summary": "List tenant employee invitations",
            "description": (
                "Returns cursor-paginated employee invitations for the current tenant. "
                "Tenant admins and permissions editors see all invitations; branch managers "
                "see only invitations for branches they manage."
            ),
            "responses": envelope_responses(
                (status.HTTP_200_OK, "Cursor-paginated invitation list envelope."),
            ),
        },
        "POST": {
            "summary": "Invite a tenant employee",
            "description": (
                "Issues an employee invitation for invite-only onboarding. Creates a user "
                "stub without password or role until acceptance. Branch managers may invite "
                "only to their branches with non-admin roles."
            ),
            "request": TenantEmployeeInvitationCreateSerializer,
            "responses": envelope_responses(
                (status.HTTP_201_CREATED, "Invitation created."),
                (status.HTTP_400_BAD_REQUEST, "Validation error."),
                (status.HTTP_403_FORBIDDEN, "Permission denied."),
            ),
        },
    },
)
class TenantEmployeeInvitationListCreateView(ModelCRUDView):
    serializer_class = TenantEmployeeInvitationListSerializer
    permission_classes = [CanManageEmployeeInvitations]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "tenant_employee_invitation"

    def get_queryset(self):
        return TenantInvitationService.list_queryset(
            self.request.tenant, inviter=self.request.user
        )

    def get_success_message(self, action: str) -> str:
        if action == "create":
            return "Invitation sent."
        return "Invitations retrieved successfully."

    def _create(self, request: Request) -> Response:
        serializer = TenantEmployeeInvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            invitation = TenantInvitationService.issue(
                inviter=request.user,
                tenant=request.tenant,
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
            data=TenantEmployeeInvitationListSerializer(invitation).data,
            message=self.get_success_message("create"),
            http_status=status.HTTP_201_CREATED,
        )


@document_crud_view(
    tags=[TENANT_TENANCY_TAG],
    operations={
        "DELETE": {
            "summary": "Revoke a pending tenant employee invitation",
            "description": (
                "Marks a pending employee invitation as revoked so it can no longer be "
                "accepted. Invitation must belong to the current tenant."
            ),
            "responses": envelope_responses(
                (status.HTTP_200_OK, "Invitation revoked."),
                (status.HTTP_400_BAD_REQUEST, "Invitation not found or already used."),
            ),
        },
    },
)
class TenantEmployeeInvitationRevokeView(ModelCRUDView):
    serializer_class = TenantEmployeeInvitationListSerializer
    permission_classes = [CanManageEmployeeInvitations]
    lookup_url_kwarg = "invitation_id"

    def get_queryset(self):
        return TenantInvitationService.list_queryset(
            self.request.tenant, inviter=self.request.user
        ).filter(used_at__isnull=True)

    def delete(self, request, invitation_id, **kwargs):
        try:
            TenantInvitationService.revoke(
                invitation_id=invitation_id,
                tenant=request.tenant,
            )
        except ValueError as exc:
            return error_response(
                message=str(exc),
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data={}, message="Invitation revoked.")


@public_post_schema(
    request=TenantEmployeeInvitationTokenSerializer,
    summary="Validate a tenant employee invitation token",
    description=(
        "Validates an employee_invite token on the public schema and returns invitation "
        "metadata without re-exposing the raw token."
    ),
    responses=envelope_responses(
        (status.HTTP_200_OK, "Token is valid."),
        (status.HTTP_400_BAD_REQUEST, "Invalid or expired token."),
    ),
)
class TenantEmployeeInvitationValidateView(PublicAPIView):

    def post(self, request):
        serializer = TenantEmployeeInvitationTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invitation = TenantInvitationService.validate(
            serializer.validated_data["token"]
        )
        if invitation is None:
            return error_response(
                message="Invalid or expired token.",
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        tenant = invitation.tenant
        if tenant is not None and not tenant.allows_user_entry():
            return error_response(
                message="Tenant workspace is suspended.",
                error_code=str(ErrorCode.TENANT_SUSPENDED),
                http_status=status.HTTP_403_FORBIDDEN,
            )
        return success_response(
            data=TenantInvitationService.serialize(invitation),
            message="Token is valid.",
        )


@public_post_schema(
    request=TenantEmployeeInvitationAcceptSerializer,
    summary="Accept a tenant employee invitation",
    description=(
        "Accepts a tenant employee invitation by setting password and assigning the "
        "invited tenant role. Returns tenant JWT tokens."
    ),
    responses=envelope_responses(
        (status.HTTP_200_OK, "Invitation accepted; session created."),
        (status.HTTP_400_BAD_REQUEST, "Invalid token or password validation error."),
    ),
)
class TenantEmployeeInvitationAcceptView(PublicAPIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "tenant_password_setup"

    def post(self, request):
        serializer = TenantEmployeeInvitationAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = TenantInvitationService.accept(
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
