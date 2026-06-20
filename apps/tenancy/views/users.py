"""Tenant user listing with branch-scoped access."""

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status

from apps.access.permissions import CanViewTenantUsers
from apps.tenancy.openapi import TENANT_TENANCY_TAG
from apps.tenancy.serializers.tenant_user import TenantUserListSerializer
from shared.models import AssetRelation
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

    def get_serializer_context(self):
        context = super().get_serializer_context()
        queryset = self.filter_queryset(self.get_queryset())
        user_ids = list(queryset.values_list("id", flat=True))
        context["profile_picture_assets"] = build_profile_picture_asset_map(user_ids)
        return context

    def get_success_message(self, action: str) -> str:
        return "Tenant users retrieved successfully."
