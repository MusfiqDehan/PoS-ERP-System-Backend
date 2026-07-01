"""POS checkout and order views."""

from rest_framework import status
from rest_framework.views import APIView

from apps.access.permissions import HasFeaturePermission
from apps.branch.models import Branch
from apps.inventory.models import Customer, Product, ProductVariant, Sale, StockLevel
from apps.inventory.openapi import (
    POS_TENANT_TAG,
    document_crud_view,
    document_inventory_get_api_view,
    document_inventory_post_api_view,
)
from apps.inventory.openapi_schemas import (
    POSCartValidateRequestSerializer,
    POSCartValidateResponseSerializer,
    POSCheckoutRequestSerializer,
    POSProductRowSerializer,
)
from apps.inventory.serializers.promotions import SaleSerializer
from apps.inventory.services.checkout import CheckoutService
from shared.responses import error_response, success_response
from shared.responses.error_codes import ErrorCode
from shared.tenancy.helpers import scope_queryset_by_branch_access
from shared.views import ModelCRUDView


@document_inventory_get_api_view(
    tags=[POS_TENANT_TAG],
    summary="List sellable POS products",
    description=(
        "Returns branch-scoped product catalog with live stock quantities. "
        "Requires pos view permission. Query param branch is required for stock context."
    ),
    response_serializer=POSProductRowSerializer,
    many=True,
)
class POSProductListView(APIView):
    permission_classes = [HasFeaturePermission.require("pos", "view")]

    def get(self, request):
        branch_id = request.query_params.get("branch")
        if not branch_id:
            return error_response(
                message="branch query param is required.",
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        products = Product.objects.filter(is_active=True).select_related(
            "category", "unit"
        )[:200]
        rows = []
        for product in products:
            stock = StockLevel.objects.filter(
                location_type=StockLevel.LOCATION_BRANCH,
                branch_id=branch_id,
                product=product,
                variant__isnull=True,
            ).first()
            rows.append(
                {
                    "id": str(product.id),
                    "name": product.name,
                    "sku": product.sku,
                    "price": str(product.price),
                    "available_stock": str(stock.quantity) if stock else "0",
                }
            )
        return success_response(data=rows, message="POS products retrieved.")


@document_inventory_post_api_view(
    tags=[POS_TENANT_TAG],
    summary="Validate POS cart",
    description="Validates line items, stock, and promotion preview for checkout.",
    request_serializer=POSCartValidateRequestSerializer,
    response_serializer=POSCartValidateResponseSerializer,
)
class POSCartValidateView(APIView):
    permission_classes = [HasFeaturePermission.require("pos", "view")]

    def post(self, request):
        branch = Branch.objects.filter(pk=request.data.get("branch")).first()
        if branch is None:
            return error_response(
                message="Branch not found.",
                error_code=str(ErrorCode.NOT_FOUND),
                http_status=status.HTTP_404_NOT_FOUND,
            )
        lines = []
        for entry in request.data.get("lines", []):
            product = Product.objects.filter(pk=entry.get("product")).first()
            if product is None:
                return error_response(
                    message="Product not found.",
                    error_code=str(ErrorCode.NOT_FOUND),
                    http_status=status.HTTP_404_NOT_FOUND,
                )
            variant = None
            if entry.get("variant"):
                variant = ProductVariant.objects.filter(pk=entry["variant"]).first()
            lines.append(
                {
                    "product": product,
                    "variant": variant,
                    "quantity": entry.get("quantity", 1),
                    "unit_price": entry.get("unit_price", product.price),
                }
            )
        result = CheckoutService.validate_cart(
            branch=branch,
            lines=lines,
            coupon_code=request.data.get("coupon_code"),
            voucher_code=request.data.get("voucher_code"),
        )
        return success_response(data=result, message="Cart validated.")


@document_inventory_post_api_view(
    tags=[POS_TENANT_TAG],
    summary="Complete POS checkout",
    description=(
        "Atomically creates sale, payments, discounts, and decrements branch stock. "
        "Supports idempotency_key for replay protection."
    ),
    request_serializer=POSCheckoutRequestSerializer,
    response_serializer=SaleSerializer,
    created=True,
)
class POSCheckoutView(APIView):
    permission_classes = [HasFeaturePermission.require("pos", "edit")]

    def post(self, request):
        branch = Branch.objects.filter(pk=request.data.get("branch")).first()
        if branch is None:
            return error_response(
                message="Branch not found.",
                error_code=str(ErrorCode.NOT_FOUND),
                http_status=status.HTTP_404_NOT_FOUND,
            )
        customer = None
        if request.data.get("customer"):
            customer = Customer.objects.filter(pk=request.data["customer"]).first()
        lines = []
        for entry in request.data.get("lines", []):
            product = Product.objects.filter(pk=entry.get("product")).first()
            if product is None:
                return error_response(
                    message="Product not found.",
                    error_code=str(ErrorCode.NOT_FOUND),
                    http_status=status.HTTP_404_NOT_FOUND,
                )
            variant = None
            if entry.get("variant"):
                variant = ProductVariant.objects.filter(pk=entry["variant"]).first()
            lines.append(
                {
                    "product": product,
                    "variant": variant,
                    "quantity": entry.get("quantity", 1),
                    "unit_price": entry.get("unit_price", product.price),
                }
            )
        payments = request.data.get("payments", [])
        if not payments:
            return error_response(
                message="At least one payment is required.",
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        sale = CheckoutService.checkout(
            branch=branch,
            cashier=request.user,
            lines=lines,
            payments=payments,
            customer=customer,
            coupon_code=request.data.get("coupon_code"),
            voucher_code=request.data.get("voucher_code"),
            loyalty_points=int(request.data.get("loyalty_points", 0)),
            idempotency_key=request.data.get("idempotency_key"),
            notes=request.data.get("notes", ""),
        )
        return success_response(
            data=SaleSerializer(sale).data,
            message="Checkout completed.",
            http_status=status.HTTP_201_CREATED,
        )


@document_crud_view(
    tags=[POS_TENANT_TAG],
    operations={
        "GET": {
            "summary": "List POS orders",
            "description": (
                "Lists completed sales. Tenant admin sees all branches; "
                "optional ?branch= filters."
            ),
        },
    },
)
class POSOrderListView(ModelCRUDView):
    permission_classes = [HasFeaturePermission.require("orders", "view")]
    queryset = Sale.objects.select_related("branch", "customer", "cashier").prefetch_related(
        "lines", "payments", "discounts"
    ).order_by("-created_at")
    serializer_class = SaleSerializer
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        return scope_queryset_by_branch_access(
            qs,
            self.request.user,
            branch_field="branch_id",
            branch_filter_id=self.request.query_params.get("branch"),
        )

    def post(self, request, pk=None, **kwargs):
        return self.http_method_not_allowed(request)


@document_crud_view(
    tags=[POS_TENANT_TAG],
    operations={
        "GET": {"summary": "Retrieve POS order", "description": "Returns sale receipt detail."},
        "POST": {
            "summary": "Cancel POS order",
            "description": "POST with ?action=cancel restores stock.",
        },
    },
)
class POSOrderDetailView(POSOrderListView):
    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [HasFeaturePermission.require("orders", "view")()]
        return [HasFeaturePermission.require("orders", "edit")()]

    actions = {
        "cancel": lambda v, r, pk: _cancel_order(v, r, pk),
    }


def _cancel_order(view, request, pk):
    sale = Sale.objects.filter(pk=pk).first()
    if sale is None:
        return error_response(
            message="Order not found.",
            error_code=str(ErrorCode.NOT_FOUND),
            http_status=status.HTTP_404_NOT_FOUND,
        )
    updated = CheckoutService.cancel_sale(sale, user=request.user)
    return success_response(
        data=SaleSerializer(updated).data,
        message="Order cancelled and stock restored.",
    )
