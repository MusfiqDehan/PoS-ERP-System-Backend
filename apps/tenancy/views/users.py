"""Tenant user listing with branch-scoped access."""

from django.contrib.auth import get_user_model
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status

from apps.access.permissions import CanViewTenantUsers
from apps.tenancy.openapi import TENANT_TENANCY_TAG
from apps.tenancy.serializers.tenant_user import TenantUserListSerializer
from shared.tenancy.helpers import scope_users_by_branch_access
from shared.views import ModelCRUDView


@extend_schema(
    tags=[TENANT_TENANCY_TAG],
    summary="List tenant users (branch-scoped)",
    responses={
        status.HTTP_200_OK: OpenApiResponse(description="Tenant user list envelope.")
    },
)
class TenantUserListView(ModelCRUDView):
    queryset = (
        get_user_model().objects.filter(is_active=True).order_by("full_name", "email")
    )
    serializer_class = TenantUserListSerializer
    permission_classes = [CanViewTenantUsers]
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        return scope_users_by_branch_access(
            queryset,
            self.request.user,
            branch_filter_id=self.request.query_params.get("branch"),
        )

    def get_success_message(self, action: str) -> str:
        return "Tenant users retrieved successfully."
