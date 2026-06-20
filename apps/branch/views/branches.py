from django.db import connection
from django.db.models import Count
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.access.permissions import HasFeaturePermission
from apps.branch.models import Branch
from apps.branch.serializers.branch import (
    BranchMinimalSerializer,
    BranchSerializer,
    BranchSummarySerializer,
)
from apps.branch.services.manager import assign_branch_manager
from shared.cache.helpers import (
    PUBLIC_BRANCH_TTL,
    get_cached_value,
    public_branches_key,
)
from shared.responses import error_response, success_response
from shared.responses.error_codes import ErrorCode
from shared.tenancy.helpers import is_tenant_admin_user, scope_queryset_by_branch_access
from shared.tenancy.limits import total_capacity_exceeded
from shared.views import ModelCRUDView


class BranchListCreateView(ModelCRUDView):
    queryset = Branch.objects.select_related("manager").order_by(
        "display_order", "name"
    )
    serializer_class = BranchSerializer
    permission_classes = [HasFeaturePermission.require("branches", "view")]
    pagination_class = None

    def get_permissions(self):
        if self.request.method == "POST":
            return [HasFeaturePermission.require("branches", "edit")()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = super().get_queryset()
        return scope_queryset_by_branch_access(
            queryset,
            self.request.user,
            branch_field="id",
            branch_filter_id=self.request.query_params.get("branch"),
        )

    def _create(self, request):
        limit_error = total_capacity_exceeded(
            Branch.objects, "max_branches", limit_type="branches"
        )
        if limit_error is not None:
            return error_response(
                message=limit_error["detail"],
                error_code=limit_error.get("code", str(ErrorCode.PERMISSION_DENIED)),
                http_status=status.HTTP_403_FORBIDDEN,
            )
        return super()._create(request)

    def get_success_message(self, action: str) -> str:
        return {
            "list": "Branches retrieved successfully.",
            "create": "Branch created successfully.",
        }.get(action, "Operation successful.")


class BranchDetailView(BranchListCreateView):
    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [HasFeaturePermission.require("branches", "view")()]
        return [HasFeaturePermission.require("branches", "edit")()]


class PublicBranchListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        schema_name = connection.schema_name
        homepage = request.query_params.get("homepage") in ("1", "true", "True")
        cache_key = public_branches_key(schema_name, minimal=False, homepage=homepage)

        def load():
            queryset = Branch.objects.filter(is_active=True).order_by(
                "display_order", "name"
            )
            if homepage:
                queryset = queryset.filter(show_on_homepage=True)
            return BranchSerializer(queryset, many=True).data

        return success_response(
            data=get_cached_value(cache_key, PUBLIC_BRANCH_TTL, load),
            message="Public branches retrieved.",
        )


class PublicBranchMinimalListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        schema_name = connection.schema_name
        cache_key = public_branches_key(schema_name, minimal=True)

        def load():
            queryset = Branch.objects.filter(is_active=True).order_by(
                "display_order", "name"
            )
            return BranchMinimalSerializer(queryset, many=True).data

        return success_response(
            data=get_cached_value(cache_key, PUBLIC_BRANCH_TTL, load),
            message="Public branches retrieved.",
        )


class BranchSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_tenant_admin_user(request.user):
            return error_response(
                message="Only tenant administrators can view branch summary.",
                error_code=str(ErrorCode.PERMISSION_DENIED),
                http_status=status.HTTP_403_FORBIDDEN,
            )
        rows = []
        for branch in Branch.objects.annotate(
            user_count=Count("user_roles", distinct=True)
        ).order_by("display_order", "name"):
            rows.append(
                {
                    "id": branch.id,
                    "name": branch.name,
                    "code": branch.code,
                    "status": branch.status,
                    "staff_count": branch.staff_count,
                    "user_count": getattr(branch, "user_count", 0),
                    "monthly_revenue": branch.monthly_revenue,
                    "rating": branch.rating,
                }
            )
        serializer = BranchSummarySerializer(rows, many=True)
        return success_response(
            data=serializer.data, message="Branch summary retrieved."
        )


class BranchManagerAssignView(APIView):
    permission_classes = [HasFeaturePermission.require("branches", "edit")]

    def post(self, request, pk):
        branch = Branch.objects.filter(pk=pk).first()
        if branch is None:
            return error_response(
                message="Branch not found.",
                error_code=str(ErrorCode.NOT_FOUND),
                http_status=status.HTTP_404_NOT_FOUND,
            )
        from django.contrib.auth import get_user_model

        user_id = request.data.get("user_id")
        user = get_user_model().objects.filter(pk=user_id).first()
        if user is None:
            return error_response(
                message="User not found.",
                error_code=str(ErrorCode.NOT_FOUND),
                http_status=status.HTTP_404_NOT_FOUND,
            )
        assign_branch_manager(branch, user)
        return success_response(
            data=BranchSerializer(branch).data,
            message="Branch manager assigned.",
        )
