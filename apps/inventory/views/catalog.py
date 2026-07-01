"""Catalog CRUD views."""

from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView

from apps.access.permissions import HasFeaturePermission
from apps.inventory.filters import ProductFilterSet
from apps.inventory.models import Category, Product
from apps.inventory.openapi import INVENTORY_TENANT_TAG, document_crud_view, document_inventory_get_api_view
from apps.inventory.openapi_schemas import LowStockProductRowSerializer
from apps.inventory.serializers.catalog import (
    BrandSerializer,
    CategorySerializer,
    ProductSerializer,
    UnitSerializer,
    VariantAttributeSerializer,
    WarrantySerializer,
)
from apps.inventory.models import Brand, Unit, VariantAttribute, Warranty
from shared.responses import success_response
from shared.tenancy.helpers import scope_queryset_by_branch_access
from shared.views import ModelCRUDView
from shared.views.list_mixins import SearchFilterSortPaginationMixin


def _catalog_crud(summary_list: str, summary_detail: str, model_name: str):
    return document_crud_view(
        tags=[INVENTORY_TENANT_TAG],
        operations={
            "GET": {
                "summary": f"List {model_name}",
                "description": (
                    f"Lists tenant catalog {model_name.lower()} records. "
                    "Requires products view permission."
                ),
            },
            "POST": {
                "summary": f"Create {model_name}",
                "description": (
                    f"Creates a {model_name.lower()} record. "
                    "Requires products edit permission."
                ),
            },
        },
    )


def _catalog_detail_crud(model_name: str):
    return document_crud_view(
        tags=[INVENTORY_TENANT_TAG],
        operations={
            "GET": {
                "summary": f"Retrieve {model_name}",
                "description": f"Returns a single {model_name.lower()} by ID.",
            },
            "PUT": {
                "summary": f"Replace {model_name}",
                "description": f"Replaces a {model_name.lower()} by ID.",
            },
            "PATCH": {
                "summary": f"Update {model_name}",
                "description": f"Partially updates a {model_name.lower()}.",
            },
            "DELETE": {
                "summary": f"Delete {model_name}",
                "description": f"Soft-deletes a {model_name.lower()}.",
            },
        },
    )


class CatalogListCreateView(ModelCRUDView):
    permission_classes = [HasFeaturePermission.require("products", "view")]
    pagination_class = None

    def get_permissions(self):
        if self.request.method == "POST":
            return [HasFeaturePermission.require("products", "edit")()]
        return super().get_permissions()


class CatalogDetailView(CatalogListCreateView):
    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [HasFeaturePermission.require("products", "view")()]
        return [HasFeaturePermission.require("products", "edit")()]


@_catalog_crud("List categories", "Create category", "Category")
class CategoryListCreateView(CatalogListCreateView):
    queryset = Category.objects.select_related("parent").order_by("name")
    serializer_class = CategorySerializer

    def get_success_message(self, action: str) -> str:
        return {
            "list": "Categories retrieved successfully.",
            "create": "Category created successfully.",
        }.get(action, "Operation successful.")


@_catalog_detail_crud("Category")
class CategoryDetailView(CatalogDetailView):
    queryset = Category.objects.select_related("parent")
    serializer_class = CategorySerializer


@document_crud_view(
    tags=[INVENTORY_TENANT_TAG],
    operations={
        "GET": {
            "summary": "List sub-categories",
            "description": (
                "Lists categories that have a parent category. "
                "Requires products view permission."
            ),
        },
    },
)
class SubCategoryListView(CatalogListCreateView):
    queryset = Category.objects.filter(parent__isnull=False).order_by("name")
    serializer_class = CategorySerializer

    def post(self, request, pk=None, **kwargs):
        return self.http_method_not_allowed(request)


@_catalog_crud("List brands", "Create brand", "Brand")
class BrandListCreateView(CatalogListCreateView):
    queryset = Brand.objects.order_by("name")
    serializer_class = BrandSerializer


@_catalog_detail_crud("Brand")
class BrandDetailView(CatalogDetailView):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer


@_catalog_crud("List units", "Create unit", "Unit")
class UnitListCreateView(CatalogListCreateView):
    queryset = Unit.objects.order_by("name")
    serializer_class = UnitSerializer


@_catalog_detail_crud("Unit")
class UnitDetailView(CatalogDetailView):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer


@_catalog_crud("List warranties", "Create warranty", "Warranty")
class WarrantyListCreateView(CatalogListCreateView):
    queryset = Warranty.objects.order_by("name")
    serializer_class = WarrantySerializer


@_catalog_detail_crud("Warranty")
class WarrantyDetailView(CatalogDetailView):
    queryset = Warranty.objects.all()
    serializer_class = WarrantySerializer


@_catalog_crud("List variant attributes", "Create variant attribute", "VariantAttribute")
class VariantAttributeListCreateView(CatalogListCreateView):
    queryset = VariantAttribute.objects.order_by("name")
    serializer_class = VariantAttributeSerializer


@_catalog_detail_crud("VariantAttribute")
class VariantAttributeDetailView(CatalogDetailView):
    queryset = VariantAttribute.objects.all()
    serializer_class = VariantAttributeSerializer


@document_crud_view(
    tags=[INVENTORY_TENANT_TAG],
    operations={
        "GET": {
            "summary": "List products",
            "description": (
                "Lists tenant products with category, brand, and unit relations. "
                "Supports cursor pagination via `cursor` and `page_size`, text search "
                "via `search`, sort via `ordering`, and filters: `category`, `brand`, "
                "`is_active`, `product_type`. Requires products view permission."
            ),
        },
        "POST": {
            "summary": "Create product",
            "description": (
                "Creates a product with optional nested variants atomically. "
                "Requires products edit permission."
            ),
        },
    },
)
class ProductListCreateView(SearchFilterSortPaginationMixin, CatalogListCreateView):
    queryset = Product.objects.select_related(
        "category", "brand", "unit", "warranty"
    ).prefetch_related("variants")
    serializer_class = ProductSerializer
    search_fields = ["name", "sku", "barcode", "slug"]
    ordering_fields = ["name", "created_at", "price", "sku"]
    filterset_class = ProductFilterSet

    def get_success_message(self, action: str) -> str:
        return {
            "list": "Products retrieved successfully.",
            "create": "Product created successfully.",
        }.get(action, "Operation successful.")


@document_crud_view(
    tags=[INVENTORY_TENANT_TAG],
    operations={
        "GET": {
            "summary": "Retrieve product",
            "description": "Returns a single product with variants.",
        },
        "PUT": {"summary": "Replace product", "description": "Replaces a product."},
        "PATCH": {"summary": "Update product", "description": "Updates a product."},
        "DELETE": {"summary": "Delete product", "description": "Soft-deletes a product."},
    },
)
class ProductDetailView(CatalogDetailView):
    queryset = Product.objects.select_related(
        "category", "brand", "unit", "warranty"
    ).prefetch_related("variants")
    serializer_class = ProductSerializer


@document_inventory_get_api_view(
    tags=[INVENTORY_TENANT_TAG],
    summary="List expired products",
    description=(
        "Returns products with expires_at before today. "
        "Tenant admins may filter with optional branch context on related stock."
    ),
    response_serializer=ProductSerializer,
    many=True,
)
class ExpiredProductListView(APIView):
    permission_classes = [HasFeaturePermission.require("products", "view")]

    def get(self, request):
        today = timezone.localdate()
        queryset = Product.objects.filter(expires_at__lt=today).order_by("expires_at")
        serializer = ProductSerializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message="Expired products retrieved.",
        )


@document_inventory_get_api_view(
    tags=[INVENTORY_TENANT_TAG],
    summary="List low-stock products",
    description=(
        "Returns products with stock at or below alert threshold. "
        "Tenant admin sees all branches; optional ?branch= filters."
    ),
    response_serializer=LowStockProductRowSerializer,
    many=True,
)
class LowStockProductListView(APIView):
    permission_classes = [HasFeaturePermission.require("inventory", "view")]

    def get(self, request):
        from django.db.models import F

        from apps.inventory.models import StockLevel

        qs = StockLevel.objects.filter(quantity__lte=F("qty_alert")).select_related(
            "product", "branch", "warehouse"
        )

        qs = scope_queryset_by_branch_access(
            qs,
            request.user,
            branch_field="branch_id",
            branch_filter_id=request.query_params.get("branch"),
        )
        data = [
            {
                "product_id": str(row.product_id),
                "product_sku": row.product.sku,
                "product_name": row.product.name,
                "quantity": str(row.quantity),
                "qty_alert": str(row.qty_alert),
                "branch_id": str(row.branch_id) if row.branch_id else None,
                "warehouse_id": str(row.warehouse_id) if row.warehouse_id else None,
            }
            for row in qs[:200]
        ]
        return success_response(data=data, message="Low-stock products retrieved.")
