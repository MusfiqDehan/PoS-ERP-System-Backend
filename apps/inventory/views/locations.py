"""Warehouse and supplier views."""

from apps.access.permissions import HasFeaturePermission
from apps.inventory.models import Supplier, Warehouse
from apps.inventory.openapi import INVENTORY_TENANT_TAG, document_crud_view
from apps.inventory.serializers.locations import SupplierSerializer, WarehouseSerializer
from shared.views import ModelCRUDView


class InventoryListCreateView(ModelCRUDView):
    permission_classes = [HasFeaturePermission.require("inventory", "view")]
    pagination_class = None

    def get_permissions(self):
        if self.request.method == "POST":
            return [HasFeaturePermission.require("inventory", "edit")()]
        return super().get_permissions()


class InventoryDetailView(InventoryListCreateView):
    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [HasFeaturePermission.require("inventory", "view")()]
        return [HasFeaturePermission.require("inventory", "edit")()]


@document_crud_view(
    tags=[INVENTORY_TENANT_TAG],
    operations={
        "GET": {
            "summary": "List warehouses",
            "description": (
                "Lists tenant warehouses ordered by name. "
                "Requires inventory view permission."
            ),
        },
        "POST": {
            "summary": "Create warehouse",
            "description": "Creates a warehouse. Requires inventory edit permission.",
        },
    },
)
class WarehouseListCreateView(InventoryListCreateView):
    queryset = Warehouse.objects.order_by("name")
    serializer_class = WarehouseSerializer


@document_crud_view(
    tags=[INVENTORY_TENANT_TAG],
    operations={
        "GET": {"summary": "Retrieve warehouse", "description": "Returns a warehouse."},
        "PUT": {"summary": "Replace warehouse", "description": "Replaces a warehouse."},
        "PATCH": {"summary": "Update warehouse", "description": "Updates a warehouse."},
        "DELETE": {
            "summary": "Delete warehouse",
            "description": "Deletes a warehouse.",
        },
    },
)
class WarehouseDetailView(InventoryDetailView):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer


@document_crud_view(
    tags=[INVENTORY_TENANT_TAG],
    operations={
        "GET": {
            "summary": "List suppliers",
            "description": (
                "Lists tenant suppliers ordered by name. "
                "Requires inventory view permission."
            ),
        },
        "POST": {
            "summary": "Create supplier",
            "description": "Creates a supplier. Requires inventory edit permission.",
        },
    },
)
class SupplierListCreateView(InventoryListCreateView):
    queryset = Supplier.objects.order_by("name")
    serializer_class = SupplierSerializer


@document_crud_view(
    tags=[INVENTORY_TENANT_TAG],
    operations={
        "GET": {"summary": "Retrieve supplier", "description": "Returns a supplier."},
        "PUT": {"summary": "Replace supplier", "description": "Replaces a supplier."},
        "PATCH": {"summary": "Update supplier", "description": "Updates a supplier."},
        "DELETE": {"summary": "Delete supplier", "description": "Deletes a supplier."},
    },
)
class SupplierDetailView(InventoryDetailView):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
