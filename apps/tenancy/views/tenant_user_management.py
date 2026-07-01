from rest_framework import status
from rest_framework.views import APIView

from apps.access.permissions import CanViewTenantUsers, IsRoleAdmin
from apps.tenancy.openapi import TENANT_TENANCY_TAG, envelope_responses
from apps.tenancy.serializers.tenant_user_management import (
    TenantUserDetailSerializer,
    TenantUserRolesSerializer,
)
from apps.tenancy.services.users import TenantUserService
from drf_spectacular.utils import extend_schema
from shared.openapi import document_crud_view
from shared.responses import error_response, success_response
from shared.responses.error_codes import ErrorCode
from shared.tenancy.helpers import scope_users_by_branch_access
from shared.views import ModelCRUDView


@document_crud_view(
    tags=[TENANT_TENANCY_TAG],
    operations={
        "GET": {
            "summary": "Retrieve tenant user detail",
            "description": (
                "Returns a tenant user's profile and role assignments. Results are "
                "branch-scoped per CanViewTenantUsers rules."
            ),
            "responses": envelope_responses(
                (status.HTTP_200_OK, "Tenant user detail envelope."),
                (status.HTTP_404_NOT_FOUND, "Tenant user not found."),
            ),
        },
    },
)
class TenantUserDetailView(ModelCRUDView):
    serializer_class = TenantUserDetailSerializer
    permission_classes = [CanViewTenantUsers]
    lookup_url_kwarg = "user_id"
    pagination_class = None

    def get_queryset(self):
        queryset = TenantUserService.queryset()
        return scope_users_by_branch_access(
            queryset,
            self.request.user,
            branch_filter_id=self.request.query_params.get("branch"),
        )

    def get_success_message(self, action: str) -> str:
        return "Tenant user retrieved."

    def get(self, request, user_id, **kwargs):
        return self._retrieve(user_id)


@extend_schema(
    tags=[TENANT_TENANCY_TAG],
    summary="Replace tenant user role assignments",
    description=(
        "Replaces the tenant user's role assignments with the provided list of role_slug "
        "and optional branch_id pairs. Requires role administrator permission."
    ),
    request=TenantUserRolesSerializer,
    responses=envelope_responses(
        (status.HTTP_200_OK, "Roles updated."),
        (status.HTTP_400_BAD_REQUEST, "Validation or lockout error."),
        (status.HTTP_403_FORBIDDEN, "Permission denied."),
        (status.HTTP_404_NOT_FOUND, "Tenant user not found."),
    ),
)
class TenantUserRolesView(APIView):
    permission_classes = [IsRoleAdmin]

    def patch(self, request, user_id):
        user = TenantUserService.get_tenant_user(user_id)
        if user is None:
            return error_response(
                message="Tenant user not found.",
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_404_NOT_FOUND,
            )
        serializer = TenantUserRolesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            assignments = TenantUserService.replace_roles(
                actor=request.user,
                user=user,
                assignments=serializer.validated_data["assignments"],
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
            data={"role_assignments": assignments},
            message="Roles updated.",
        )


@extend_schema(
    tags=[TENANT_TENANCY_TAG],
    summary="Deactivate a tenant user",
    description=(
        "Soft-deactivates a tenant user account. Cannot deactivate the last active "
        "tenant admin. Requires role administrator permission."
    ),
    responses=envelope_responses(
        (status.HTTP_200_OK, "User deactivated."),
        (status.HTTP_400_BAD_REQUEST, "Lockout or validation error."),
        (status.HTTP_404_NOT_FOUND, "Tenant user not found."),
    ),
)
class TenantUserDeactivateView(APIView):
    permission_classes = [IsRoleAdmin]

    def post(self, request, user_id):
        user = TenantUserService.get_tenant_user(user_id)
        if user is None:
            return error_response(
                message="Tenant user not found.",
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_404_NOT_FOUND,
            )
        try:
            TenantUserService.deactivate(actor=request.user, user=user)
        except ValueError as exc:
            return error_response(
                message=str(exc),
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data={}, message="User deactivated.")
