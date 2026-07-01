"""Inventory dashboard views."""

from uuid import UUID

from rest_framework import status
from rest_framework.views import APIView

from apps.access.permissions import HasFeaturePermission
from apps.inventory.openapi import INVENTORY_TENANT_TAG, document_inventory_get_api_view
from apps.inventory.openapi_schemas import (
    DashboardLowStockItemSerializer,
    DashboardPendingActionsSerializer,
    DashboardSummarySerializer,
)
from apps.inventory.services.dashboard import DashboardService
from shared.responses import error_response, success_response
from shared.responses.error_codes import ErrorCode


def _parse_uuid(value):
    if value in (None, "", "all"):
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return "invalid"


@document_inventory_get_api_view(
    tags=[INVENTORY_TENANT_TAG],
    summary="Dashboard summary",
    description=(
        "Aggregated inventory metrics. Query scope=business|branch|warehouse "
        "with optional branch and warehouse filters."
    ),
    response_serializer=DashboardSummarySerializer,
)
class DashboardSummaryView(APIView):
    permission_classes = [HasFeaturePermission.require("dashboard", "view")]

    def get(self, request):
        scope = request.query_params.get("scope", "business")
        branch_id = _parse_uuid(request.query_params.get("branch"))
        warehouse_id = _parse_uuid(request.query_params.get("warehouse"))
        if branch_id == "invalid" or warehouse_id == "invalid":
            return error_response(
                message="Invalid branch or warehouse UUID.",
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        data = DashboardService.summary(
            scope=scope,
            branch_id=branch_id,
            warehouse_id=warehouse_id,
        )
        return success_response(data=data, message="Dashboard summary retrieved.")


@document_inventory_get_api_view(
    tags=[INVENTORY_TENANT_TAG],
    summary="Dashboard low stock",
    description="Low-stock items with optional branch and warehouse filters.",
    response_serializer=DashboardLowStockItemSerializer,
    many=True,
)
class DashboardLowStockView(APIView):
    permission_classes = [HasFeaturePermission.require("dashboard", "view")]

    def get(self, request):
        branch_id = _parse_uuid(request.query_params.get("branch"))
        warehouse_id = _parse_uuid(request.query_params.get("warehouse"))
        if branch_id == "invalid":
            return error_response(
                message="Invalid branch UUID.",
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        data = DashboardService.low_stock(
            branch_id=branch_id if branch_id != "invalid" else None,
            warehouse_id=warehouse_id if warehouse_id != "invalid" else None,
        )
        return success_response(data=data, message="Low stock items retrieved.")


@document_inventory_get_api_view(
    tags=[INVENTORY_TENANT_TAG],
    summary="Dashboard pending actions",
    description="Counts of pending transfers, requests, and purchase orders.",
    response_serializer=DashboardPendingActionsSerializer,
)
class DashboardPendingActionsView(APIView):
    permission_classes = [HasFeaturePermission.require("dashboard", "view")]

    def get(self, request):
        branch_id = _parse_uuid(request.query_params.get("branch"))
        if branch_id == "invalid":
            return error_response(
                message="Invalid branch UUID.",
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        data = DashboardService.pending_actions(
            branch_id=branch_id if branch_id != "invalid" else None,
        )
        return success_response(data=data, message="Pending actions retrieved.")
