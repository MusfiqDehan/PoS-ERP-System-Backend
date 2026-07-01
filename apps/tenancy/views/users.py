"""Tenant user listing with branch-scoped access."""

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from apps.access.permissions import CanViewTenantUsers
from apps.tenancy.openapi import TENANT_TENANCY_TAG, envelope_responses
from apps.tenancy.serializers.tenant_user import TenantUserListSerializer
from apps.tenancy.services.users import TenantUserService
from shared.models import AssetRelation
from shared.openapi import document_crud_view
from shared.responses import error_response
from shared.responses.error_codes import ErrorCode
from shared.services.asset_attachment import (
    USER_PROFILE_PICTURE_FIELD,
    USER_PROFILE_PICTURE_ROLE,
)
from shared.tenancy.helpers import scope_users_by_branch_access
from shared.views import ModelCRUDView


def build_profile_picture_asset_map(user_ids):
    if not user_ids:
        return {}
    user_model = get_user_model()
    user_content_type = ContentType.objects.get_for_model(user_model)
    relations = AssetRelation.objects.filter(
        content_type=user_content_type,
        object_id__in=user_ids,
        role=USER_PROFILE_PICTURE_ROLE,
        field_name=USER_PROFILE_PICTURE_FIELD,
        is_primary=True,
        is_deleted=False,
    ).select_related("asset")
    return {
        relation.object_id: relation.asset
        for relation in relations
        if not relation.asset.is_deleted
    }


@document_crud_view(
    tags=[TENANT_TENANCY_TAG],
    operations={
        "GET": {
            "summary": "List tenant users (branch-scoped)",
            "description": (
                "Lists active tenant users visible to the caller based on branch access "
                "rules with cursor pagination. Supports an optional branch query filter. "
                "Requires CanViewTenantUsers permission. No POST — employees are onboarded "
                "via invitation only."
            ),
            "responses": envelope_responses(
                (status.HTTP_200_OK, "Cursor-paginated tenant user list envelope."),
            ),
        },
        "POST": {
            "summary": "Direct tenant user creation (not allowed)",
            "description": (
                "Returns 405 — tenant employees are onboarded via employee invitation only."
            ),
            "responses": envelope_responses(
                (
                    status.HTTP_405_METHOD_NOT_ALLOWED,
                    "Direct user creation not allowed (invite-only).",
                ),
            ),
        },
    },
)
class TenantUserListView(ModelCRUDView):
    queryset = TenantUserService.queryset()
    serializer_class = TenantUserListSerializer
    permission_classes = [CanViewTenantUsers]

    def get_queryset(self):
        queryset = super().get_queryset()
        return scope_users_by_branch_access(
            queryset,
            self.request.user,
            branch_filter_id=self.request.query_params.get("branch"),
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        queryset = self.filter_queryset(self.get_queryset())
        user_ids = list(queryset.values_list("id", flat=True))
        context["profile_picture_assets"] = build_profile_picture_asset_map(user_ids)
        return context

    def get_success_message(self, action: str) -> str:
        return "Tenant users retrieved successfully."

    def post(self, request: Request, pk=None, **kwargs) -> Response:
        return error_response(
            message="Tenant employees are created via invitation only.",
            error_code=str(ErrorCode.VALIDATION_ERROR),
            http_status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )
