from rest_framework import serializers

from apps.inventory.models import (
    StockAdjustment,
    StockLevel,
    StockMovement,
    StockRequest,
    StockRequestLine,
    StockTransfer,
    StockTransferLine,
)
from apps.inventory.services.stock import StockService


class StockLevelSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = StockLevel
        fields = [
            "id",
            "location_type",
            "branch",
            "warehouse",
            "product",
            "product_sku",
            "product_name",
            "variant",
            "quantity",
            "qty_alert",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "quantity", "created_at", "updated_at"]


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = [
            "id",
            "stock_level",
            "movement_type",
            "quantity_delta",
            "reference_type",
            "reference_id",
            "performed_by",
            "notes",
            "created_at",
        ]
        read_only_fields = fields


class StockAdjustmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockAdjustment
        fields = [
            "id",
            "branch",
            "warehouse",
            "product",
            "variant",
            "quantity_before",
            "quantity_after",
            "reason",
            "responsible_person",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "quantity_before",
            "quantity_after",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        branch = validated_data.get("branch")
        warehouse = validated_data.get("warehouse")
        product = validated_data["product"]
        variant = validated_data.get("variant")
        new_qty = validated_data["quantity_after"]
        user = self.context["request"].user

        if branch:
            stock_level = StockService.get_or_create_branch_stock(
                branch=branch, product=product, variant=variant
            )
        else:
            stock_level = StockService.get_or_create_warehouse_stock(
                warehouse=warehouse, product=product, variant=variant
            )

        before = stock_level.quantity
        StockService.adjust(
            stock_level_id=stock_level.id,
            new_quantity=new_qty,
            performed_by=user,
        )
        return StockAdjustment.objects.create(
            branch=branch,
            warehouse=warehouse,
            product=product,
            variant=variant,
            quantity_before=before,
            quantity_after=new_qty,
            reason=validated_data.get("reason", ""),
            responsible_person=user,
        )


class StockTransferLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockTransferLine
        fields = [
            "id",
            "product",
            "variant",
            "quantity_requested",
            "quantity_approved",
            "quantity_received",
        ]
        read_only_fields = ["id", "quantity_approved", "quantity_received"]


class StockTransferSerializer(serializers.ModelSerializer):
    lines = StockTransferLineSerializer(many=True)

    class Meta:
        model = StockTransfer
        fields = [
            "id",
            "transfer_type",
            "source_branch",
            "source_warehouse",
            "target_branch",
            "target_warehouse",
            "status",
            "ref_number",
            "notes",
            "requested_by",
            "lines",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "ref_number", "requested_by", "created_at", "updated_at"]

    def create(self, validated_data):
        from apps.inventory.utils import generate_ref_number

        lines_data = validated_data.pop("lines")
        user = self.context["request"].user
        transfer = StockTransfer.objects.create(
            **validated_data,
            ref_number=generate_ref_number("TRF"),
            requested_by=user,
            status=StockTransfer.STATUS_PENDING,
        )
        for line_data in lines_data:
            StockTransferLine.objects.create(transfer=transfer, **line_data)
        return transfer


class StockRequestLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockRequestLine
        fields = [
            "id",
            "product",
            "variant",
            "quantity_requested",
            "quantity_approved",
        ]
        read_only_fields = ["id", "quantity_approved"]


class StockRequestSerializer(serializers.ModelSerializer):
    lines = StockRequestLineSerializer(many=True)

    class Meta:
        model = StockRequest
        fields = [
            "id",
            "request_type",
            "requesting_branch",
            "source_branch",
            "source_warehouse",
            "status",
            "priority",
            "ref_number",
            "notes",
            "lines",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "ref_number", "created_at", "updated_at"]

    def create(self, validated_data):
        from apps.inventory.utils import generate_ref_number

        lines_data = validated_data.pop("lines")
        request = StockRequest.objects.create(
            **validated_data,
            ref_number=generate_ref_number("REQ"),
            status=StockRequest.STATUS_PENDING,
        )
        for line_data in lines_data:
            StockRequestLine.objects.create(request=request, **line_data)
        return request
