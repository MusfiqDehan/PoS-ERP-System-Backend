"""OpenAPI serializers for inventory APIView request/response documentation."""

from __future__ import annotations

from rest_framework import serializers

from apps.inventory.serializers.catalog import ProductSerializer
from apps.inventory.serializers.procurement import (
    GoodsReceiptCreateSerializer,
    GoodsReceiptSerializer,
)
from apps.inventory.serializers.promotions import (
    CouponSerializer,
    GiftVoucherSerializer,
    LoyaltyAccountSerializer,
    SaleSerializer,
)
from apps.inventory.serializers.stock import StockMovementSerializer

__all__ = [
    "CouponValidateRequestSerializer",
    "CouponValidateResponseSerializer",
    "DashboardLowStockItemSerializer",
    "DashboardPendingActionsSerializer",
    "DashboardSummarySerializer",
    "GiftVoucherValidateRequestSerializer",
    "GiftVoucherValidateResponseSerializer",
    "GoodsReceiptCreateSerializer",
    "GoodsReceiptSerializer",
    "LoyaltyPointsPatchSerializer",
    "LowStockProductRowSerializer",
    "POSCartLineInputSerializer",
    "POSCartValidateRequestSerializer",
    "POSCartValidateResponseSerializer",
    "POSCartValidatedLineSerializer",
    "POSCheckoutRequestSerializer",
    "POSPaymentInputSerializer",
    "POSProductRowSerializer",
    "ProductSerializer",
    "ReplenishmentOptionSerializer",
    "SaleSerializer",
    "StockMovementSerializer",
    "LoyaltyAccountSerializer",
]


class DashboardSummarySerializer(serializers.Serializer):
    scope = serializers.CharField()
    branch_id = serializers.CharField(allow_null=True)
    warehouse_id = serializers.CharField(allow_null=True)
    total_sales = serializers.CharField()
    order_count = serializers.IntegerField()
    total_stock_quantity = serializers.CharField()
    stock_sku_count = serializers.IntegerField()
    low_stock_count = serializers.IntegerField()
    product_count = serializers.IntegerField()
    branch_count = serializers.IntegerField()
    warehouse_count = serializers.IntegerField()


class DashboardLowStockItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    product_sku = serializers.CharField()
    product_name = serializers.CharField()
    quantity = serializers.CharField()
    qty_alert = serializers.CharField()
    branch_id = serializers.CharField(allow_null=True)
    warehouse_id = serializers.CharField(allow_null=True)


class DashboardPendingActionsSerializer(serializers.Serializer):
    pending_transfers = serializers.IntegerField()
    pending_requests = serializers.IntegerField()
    pending_purchase_orders = serializers.IntegerField()


class POSProductRowSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    sku = serializers.CharField()
    price = serializers.CharField()
    available_stock = serializers.CharField()


class POSCartLineInputSerializer(serializers.Serializer):
    product = serializers.UUIDField()
    variant = serializers.UUIDField(required=False, allow_null=True)
    quantity = serializers.DecimalField(
        max_digits=12, decimal_places=3, required=False, default=1
    )
    unit_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False
    )


class POSCartValidateRequestSerializer(serializers.Serializer):
    branch = serializers.UUIDField()
    lines = POSCartLineInputSerializer(many=True)
    coupon_code = serializers.CharField(required=False, allow_blank=True)
    voucher_code = serializers.CharField(required=False, allow_blank=True)


class POSCartValidatedLineSerializer(serializers.Serializer):
    product_id = serializers.CharField()
    variant_id = serializers.CharField(allow_null=True)
    quantity = serializers.CharField()
    unit_price = serializers.CharField()
    line_total = serializers.CharField()
    available_stock = serializers.CharField()
    sufficient_stock = serializers.BooleanField()


class POSCartValidateResponseSerializer(serializers.Serializer):
    lines = POSCartValidatedLineSerializer(many=True)
    subtotal = serializers.CharField()
    discount = serializers.CharField()
    total = serializers.CharField()


class POSPaymentInputSerializer(serializers.Serializer):
    method = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    reference = serializers.CharField(required=False, allow_blank=True, default="")


class POSCheckoutRequestSerializer(serializers.Serializer):
    branch = serializers.UUIDField()
    customer = serializers.UUIDField(required=False, allow_null=True)
    lines = POSCartLineInputSerializer(many=True)
    payments = POSPaymentInputSerializer(many=True)
    coupon_code = serializers.CharField(required=False, allow_blank=True)
    voucher_code = serializers.CharField(required=False, allow_blank=True)
    loyalty_points = serializers.IntegerField(required=False, default=0)
    idempotency_key = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class LoyaltyPointsPatchSerializer(serializers.Serializer):
    points_balance = serializers.IntegerField(required=False)


class CouponValidateRequestSerializer(serializers.Serializer):
    code = serializers.CharField()


class CouponValidateResponseSerializer(serializers.Serializer):
    coupon = CouponSerializer()
    discount = serializers.CharField()


class GiftVoucherValidateRequestSerializer(serializers.Serializer):
    code = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, default=0)


class GiftVoucherValidateResponseSerializer(serializers.Serializer):
    voucher = GiftVoucherSerializer()
    applicable_amount = serializers.CharField()


class LowStockProductRowSerializer(serializers.Serializer):
    product_id = serializers.CharField()
    product_sku = serializers.CharField()
    product_name = serializers.CharField()
    quantity = serializers.CharField()
    qty_alert = serializers.CharField()
    branch_id = serializers.CharField(allow_null=True)
    warehouse_id = serializers.CharField(allow_null=True)


class ReplenishmentOptionSerializer(serializers.Serializer):
    source_type = serializers.CharField()
    source_id = serializers.CharField()
    source_name = serializers.CharField()
    quantity = serializers.CharField()
    priority = serializers.IntegerField()
    is_central = serializers.BooleanField(required=False)
