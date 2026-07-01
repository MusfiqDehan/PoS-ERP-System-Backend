"""Procurement views."""

from rest_framework import status
from rest_framework.views import APIView

from apps.access.permissions import HasFeaturePermission
from apps.inventory.openapi import (
    INVENTORY_TENANT_TAG,
    document_crud_view,
    document_inventory_post_api_view,
)
from apps.inventory.serializers.procurement import (
    GoodsReceiptCreateSerializer,
    GoodsReceiptSerializer,
    PurchaseOrderSerializer,
)
from apps.inventory.services.procurement import ProcurementService
from shared.responses import error_response, success_response
from shared.responses.error_codes import ErrorCode
from shared.views import ModelCRUDView

from apps.inventory.models import PurchaseOrder


class _ProcurementBaseView(ModelCRUDView):
    permission_classes = [HasFeaturePermission.require("inventory", "view")]
    pagination_class = None

    def get_permissions(self):
        if self.request.method == "POST":
            return [HasFeaturePermission.require("inventory", "edit")()]
        return super().get_permissions()


class _ProcurementDetailView(_ProcurementBaseView):
    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [HasFeaturePermission.require("inventory", "view")()]
        return [HasFeaturePermission.require("inventory", "edit")()]


def _po_action(view, request, pk, action_fn, message: str):
    po = PurchaseOrder.objects.filter(pk=pk).first()
    if po is None:
        return error_response(
            message="Purchase order not found.",
            error_code=str(ErrorCode.NOT_FOUND),
            http_status=status.HTTP_404_NOT_FOUND,
        )
    updated = action_fn(po)
    return success_response(
        data=PurchaseOrderSerializer(updated).data,
        message=message,
    )


@document_crud_view(
    tags=[INVENTORY_TENANT_TAG],
    operations={
        "GET": {
            "summary": "List purchase orders",
            "description": (
                "Lists tenant-wide purchase orders for warehouse procurement. "
                "Not branch-filtered; requires inventory view permission."
            ),
        },
        "POST": {
            "summary": "Create purchase order",
            "description": "Creates a draft purchase order with lines.",
        },
    },
)
class PurchaseOrderListCreateView(_ProcurementBaseView):
    queryset = (
        PurchaseOrder.objects.select_related("supplier", "warehouse")
        .prefetch_related("lines")
        .order_by("-created_at")
    )
    serializer_class = PurchaseOrderSerializer


@document_crud_view(
    tags=[INVENTORY_TENANT_TAG],
    operations={
        "GET": {"summary": "Retrieve PO", "description": "Returns a purchase order."},
        "PATCH": {
            "summary": "Update PO or action",
            "description": "Update or ?action=send|cancel.",
        },
        "POST": {
            "summary": "PO action",
            "description": "POST with ?action=send|cancel.",
        },
    },
)
class PurchaseOrderDetailView(_ProcurementDetailView):
    queryset = PurchaseOrder.objects.select_related(
        "supplier", "warehouse"
    ).prefetch_related("lines")
    serializer_class = PurchaseOrderSerializer
    actions = {
        "send": lambda v, r, pk: _po_action(
            v, r, pk, ProcurementService.send_purchase_order, "Purchase order sent."
        ),
        "cancel": lambda v, r, pk: _po_action(
            v,
            r,
            pk,
            ProcurementService.cancel_purchase_order,
            "Purchase order cancelled.",
        ),
    }


@document_inventory_post_api_view(
    tags=[INVENTORY_TENANT_TAG],
    summary="Create goods receipt",
    description=(
        "Creates a goods receipt against a sent PO. "
        "Confirm via POST to detail with ?action=confirm to stock-in."
    ),
    request_serializer=GoodsReceiptCreateSerializer,
    response_serializer=GoodsReceiptSerializer,
    created=True,
)
class GoodsReceiptCreateView(APIView):
    permission_classes = [HasFeaturePermission.require("inventory", "edit")]

    def post(self, request):
        serializer = GoodsReceiptCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        receipt = ProcurementService.create_goods_receipt(
            purchase_order=serializer.validated_data["purchase_order_obj"],
            lines=serializer.validated_data["validated_lines"],
            received_by=request.user,
        )
        confirmed = ProcurementService.confirm_goods_receipt(receipt, user=request.user)
        return success_response(
            data=GoodsReceiptSerializer(confirmed).data,
            message="Goods received and stock updated.",
            http_status=status.HTTP_201_CREATED,
        )
