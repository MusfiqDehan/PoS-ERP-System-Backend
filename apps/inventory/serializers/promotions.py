from rest_framework import serializers

from apps.inventory.models import (
    Coupon,
    Customer,
    GiftVoucher,
    LoyaltyAccount,
    Promotion,
    Sale,
    SaleDiscount,
    SaleLine,
    SalePayment,
)


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "branch",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class LoyaltyAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyAccount
        fields = ["id", "customer", "points_balance", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class PromotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = [
            "id",
            "name",
            "promotion_type",
            "rules",
            "discount_value",
            "valid_from",
            "valid_to",
            "branch",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = [
            "id",
            "code",
            "promotion",
            "usage_limit",
            "used_count",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "used_count", "created_at", "updated_at"]


class GiftVoucherSerializer(serializers.ModelSerializer):
    class Meta:
        model = GiftVoucher
        fields = [
            "id",
            "code",
            "balance",
            "expires_at",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SaleLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleLine
        fields = [
            "id",
            "product",
            "variant",
            "quantity",
            "unit_price",
            "discount",
            "tax",
            "line_total",
        ]
        read_only_fields = fields


class SalePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalePayment
        fields = ["id", "method", "amount", "reference"]
        read_only_fields = fields


class SaleDiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleDiscount
        fields = ["id", "discount_type", "reference_id", "amount"]
        read_only_fields = fields


class SaleSerializer(serializers.ModelSerializer):
    lines = SaleLineSerializer(many=True, read_only=True)
    payments = SalePaymentSerializer(many=True, read_only=True)
    discounts = SaleDiscountSerializer(many=True, read_only=True)

    class Meta:
        model = Sale
        fields = [
            "id",
            "branch",
            "customer",
            "cashier",
            "status",
            "subtotal",
            "tax",
            "discount",
            "total",
            "ref_number",
            "idempotency_key",
            "notes",
            "lines",
            "payments",
            "discounts",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
