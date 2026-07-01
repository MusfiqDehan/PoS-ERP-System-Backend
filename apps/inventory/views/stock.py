"""Stock operation views."""

from rest_framework import status
from rest_framework.views import APIView

from uuid import UUID

from apps.access.permissions import HasFeaturePermission
from apps.inventory.models import (
    StockAdjustment,
    StockLevel,
    StockMovement,
    StockRequest,
    StockTransfer,
)
from apps.inventory.openapi import (
    INVENTORY_TENANT_TAG,
    document_crud_view,
    document_inventory_get_api_view,
    document_inventory_post_api_view,
)
from apps.inventory.openapi_schemas import ReplenishmentOptionSerializer
from apps.inventory.serializers.stock import (
    StockAdjustmentSerializer,
    StockLevelSerializer,
    StockMovementSerializer,
    StockRequestSerializer,
    StockTransferSerializer,
)
from apps.inventory.services.dashboard import DashboardService
from apps.inventory.services.transfer import TransferService
from shared.responses import error_response, success_response
from shared.responses.error_codes import ErrorCode
from shared.tenancy.helpers import (
    assert_user_branch_access,
    get_user_branch_scope_ids,
    scope_queryset_by_branch_access,
)
from shared.responses.exceptions import DomainAPIException
from shared.views import ModelCRUDView


class BranchScopedInventoryView(ModelCRUDView):
    permission_classes = [HasFeaturePermission.require("inventory", "view")]
    pagination_class = None
    branch_field = "branch_id"

    def get_permissions(self):
        if self.request.method == "POST":
            return [HasFeaturePermission.require("inventory", "edit")()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        branch_filter = self.request.query_params.get("branch")
        scope_ids = get_user_branch_scope_ids(self.request.user)
        if scope_ids is not None and branch_filter not in (None, "", "all"):
            try:
                filter_uuid = UUID(str(branch_filter))
            except (TypeError, ValueError):
                return qs.none()
            if filter_uuid not in scope_ids:
                return qs.none()
        return scope_queryset_by_branch_access(
            qs,
            self.request.user,
            branch_field=self.branch_field,
            branch_filter_id=branch_filter,
        )


class BranchScopedDetailView(BranchScopedInventoryView):
    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [HasFeaturePermission.require("inventory", "view")()]
        return [HasFeaturePermission.require("inventory", "edit")()]


@document_crud_view(
    tags=[INVENTORY_TENANT_TAG],
    operations={
        "GET": {
            "summary": "List stock levels",
            "description": (
                "Lists stock levels per branch or warehouse. "
                "Tenant admin sees all branches; optional ?branch= filters."
            ),
        },
        "POST": {
            "summary": "Initialize stock level",
            "description": "Creates or initializes a stock level record.",
        },
    },
)
class StockLevelListCreateView(BranchScopedInventoryView):
    queryset = StockLevel.objects.select_related(
        "product", "variant", "branch", "warehouse"
    ).order_by("-updated_at")
    serializer_class = StockLevelSerializer


@document_crud_view(
    tags=[INVENTORY_TENANT_TAG],
    operations={
        "GET": {"summary": "Retrieve stock level", "description": "Returns a stock level."},
        "PATCH": {"summary": "Update stock level", "description": "Updates alert thresholds."},
        "DELETE": {"summary": "Delete stock level", "description": "Soft-deletes a stock level."},
    },
)
class StockLevelDetailView(BranchScopedDetailView):
    queryset = StockLevel.objects.select_related(
        "product", "variant", "branch", "warehouse"
    )
    serializer_class = StockLevelSerializer


@document_crud_view(
    tags=[INVENTORY_TENANT_TAG],
    operations={
        "GET": {
            "summary": "List stock adjustments",
            "description": "Lists stock adjustments with optional ?branch= filter.",
        },
        "POST": {
            "summary": "Create stock adjustment",
            "description": "Adjusts stock via StockService.",
        },
    },
)
class StockAdjustmentListCreateView(BranchScopedInventoryView):
    queryset = StockAdjustment.objects.select_related(
        "product", "variant", "branch", "warehouse"
    ).order_by("-created_at")
    serializer_class = StockAdjustmentSerializer


@document_crud_view(
    tags=[INVENTORY_TENANT_TAG],
    operations={
        "GET": {"summary": "Retrieve adjustment", "description": "Returns an adjustment."},
    },
)
class StockAdjustmentDetailView(BranchScopedDetailView):
    queryset = StockAdjustment.objects.select_related(
        "product", "variant", "branch", "warehouse"
    )
    serializer_class = StockAdjustmentSerializer

    def put(self, request, pk, **kwargs):
        return self.http_method_not_allowed(request)

    def patch(self, request, pk, **kwargs):
        return self.http_method_not_allowed(request)

    def delete(self, request, pk, **kwargs):
        return self.http_method_not_allowed(request)


def _transfer_action(view, request, pk, action_fn, message: str):
    transfer = StockTransfer.objects.filter(pk=pk).first()
    if transfer is None:
        return error_response(
            message="Transfer not found.",
            error_code=str(ErrorCode.NOT_FOUND),
            http_status=status.HTTP_404_NOT_FOUND,
        )
    updated = action_fn(transfer, user=request.user)
    return success_response(
        data=StockTransferSerializer(updated).data,
        message=message,
    )


@document_crud_view(
    tags=[INVENTORY_TENANT_TAG],
    operations={
        "GET": {
            "summary": "List stock transfers",
            "description": (
                "Lists transfers with branch scoping. "
                "Workflow actions via ?action= on PATCH/POST."
            ),
        },
        "POST": {"summary": "Create transfer", "description": "Creates a stock transfer."},
    },
)
class StockTransferListCreateView(BranchScopedInventoryView):
    queryset = StockTransfer.objects.prefetch_related("lines").order_by("-created_at")
    serializer_class = StockTransferSerializer
    branch_field = "source_branch_id"


@document_crud_view(
    tags=[INVENTORY_TENANT_TAG],
    operations={
        "GET": {"summary": "Retrieve transfer", "description": "Returns a transfer."},
        "PATCH": {
            "summary": "Update transfer or run action",
            "description": (
                "Partial update or workflow action: approve, reject, "
                "partial_approve, ship, receive."
            ),
        },
        "POST": {
            "summary": "Run transfer action",
            "description": "POST with ?action= for workflow transitions.",
        },
    },
)
class StockTransferDetailView(BranchScopedDetailView):
    queryset = StockTransfer.objects.prefetch_related("lines")
    serializer_class = StockTransferSerializer
    branch_field = "source_branch_id"
    actions = {
        "approve": lambda v, r, pk: _transfer_action(
            v, r, pk, TransferService.approve, "Transfer approved."
        ),
        "reject": lambda v, r, pk: _transfer_action(
            v, r, pk, TransferService.reject, "Transfer rejected."
        ),
        "ship": lambda v, r, pk: _transfer_action(
            v, r, pk, TransferService.ship, "Transfer shipped."
        ),
        "receive": lambda v, r, pk: _transfer_action(
            v, r, pk, TransferService.receive, "Transfer received."
        ),
        "partial_approve": lambda v, r, pk: _partial_approve_action(v, r, pk),
    }


def _partial_approve_action(view, request, pk):
    transfer = StockTransfer.objects.filter(pk=pk).first()
    if transfer is None:
        return error_response(
            message="Transfer not found.",
            error_code=str(ErrorCode.NOT_FOUND),
            http_status=status.HTTP_404_NOT_FOUND,
        )
    line_quantities = request.data.get("line_quantities", {})
    updated = TransferService.partial_approve(
        transfer, line_quantities, user=request.user
    )
    return success_response(
        data=StockTransferSerializer(updated).data,
        message="Transfer partially approved.",
    )


@document_crud_view(
    tags=[INVENTORY_TENANT_TAG],
    operations={
        "GET": {
            "summary": "List stock requests",
            "description": "Lists replenishment requests with ?branch= filter.",
        },
        "POST": {"summary": "Create request", "description": "Creates a stock request."},
    },
)
class StockRequestListCreateView(BranchScopedInventoryView):
    queryset = StockRequest.objects.prefetch_related("lines").order_by("-created_at")
    serializer_class = StockRequestSerializer
    branch_field = "requesting_branch_id"


@document_crud_view(
    tags=[INVENTORY_TENANT_TAG],
    operations={
        "GET": {"summary": "Retrieve request", "description": "Returns a stock request."},
        "PATCH": {"summary": "Update request", "description": "Updates a stock request."},
    },
)
class StockRequestDetailView(BranchScopedDetailView):
    queryset = StockRequest.objects.prefetch_related("lines")
    serializer_class = StockRequestSerializer
    branch_field = "requesting_branch_id"


@document_inventory_get_api_view(
    tags=[INVENTORY_TENANT_TAG],
    summary="List stock movements",
    description="Read-only audit log of stock mutations with ?branch= filter.",
    response_serializer=StockMovementSerializer,
    many=True,
)
class StockMovementListView(APIView):
    permission_classes = [HasFeaturePermission.require("inventory", "view")]

    def get(self, request):
        qs = StockMovement.objects.select_related(
            "stock_level", "stock_level__branch", "performed_by"
        ).order_by("-created_at")
        stock_levels = scope_queryset_by_branch_access(
            StockLevel.objects.all(),
            request.user,
            branch_field="branch_id",
            branch_filter_id=request.query_params.get("branch"),
        )
        qs = qs.filter(stock_level__in=stock_levels)
        serializer = StockMovementSerializer(qs[:500], many=True)
        return success_response(
            data=serializer.data,
            message="Stock movements retrieved.",
        )


@document_inventory_get_api_view(
    tags=[INVENTORY_TENANT_TAG],
    summary="Get replenishment options",
    description=(
        "Returns ranked internal stock sources for a product at a branch. "
        "Query params: product, branch."
    ),
    response_serializer=ReplenishmentOptionSerializer,
    many=True,
)
class ReplenishmentOptionsView(APIView):
    permission_classes = [HasFeaturePermission.require("inventory", "view")]

    def get(self, request):
        product_id = request.query_params.get("product")
        branch_id = request.query_params.get("branch")
        if not product_id or not branch_id:
            return error_response(
                message="product and branch query params are required.",
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            assert_user_branch_access(request.user, branch_id)
        except DomainAPIException as exc:
            return error_response(
                message=exc.user_message,
                error_code=exc.error_code,
                http_status=exc.status_code,
            )
        from uuid import UUID

        try:
            include_other = get_user_branch_scope_ids(request.user) is None
            options = DashboardService.replenishment_options(
                product_id=UUID(product_id),
                branch_id=UUID(branch_id),
                user=request.user,
                include_other_branches=include_other,
            )
        except (TypeError, ValueError):
            return error_response(
                message="Invalid product or branch UUID.",
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data=options, message="Replenishment options retrieved.")
