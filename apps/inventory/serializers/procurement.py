from decimal import Decimal

from rest_framework import serializers

from apps.inventory.models import (
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseOrder,
    PurchaseOrderLine,
)


class PurchaseOrderLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrderLine
        fields = [
            "id",
            "product",
            "variant",
            "quantity_ordered",
            "unit_cost",
        ]
        read_only_fields = ["id"]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    lines = PurchaseOrderLineSerializer(many=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            "id",
            "supplier",
            "warehouse",
            "status",
            "ref_number",
            "total",
            "notes",
            "lines",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "ref_number", "total", "created_at", "updated_at"]

    def create(self, validated_data):
        from apps.inventory.utils import generate_ref_number

        lines_data = validated_data.pop("lines")
        total = sum(
            Decimal(str(line["quantity_ordered"])) * Decimal(str(line.get("unit_cost", 0)))
            for line in lines_data
        )
        po = PurchaseOrder.objects.create(
            **validated_data,
            ref_number=generate_ref_number("PO"),
            total=total,
            status=PurchaseOrder.STATUS_DRAFT,
        )
        for line_data in lines_data:
            PurchaseOrderLine.objects.create(purchase_order=po, **line_data)
        return po


class GoodsReceiptLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoodsReceiptLine
        fields = [
            "id",
            "purchase_order_line",
            "product",
            "variant",
            "quantity_received",
        ]
        read_only_fields = ["id", "product", "variant"]


class GoodsReceiptSerializer(serializers.ModelSerializer):
    lines = GoodsReceiptLineSerializer(many=True, read_only=True)

    class Meta:
        model = GoodsReceipt
        fields = [
            "id",
            "purchase_order",
            "warehouse",
            "received_by",
            "status",
            "ref_number",
            "notes",
            "lines",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class GoodsReceiptCreateSerializer(serializers.Serializer):
    purchase_order = serializers.UUIDField()
    lines = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
    )

    def validate(self, attrs):
        po = PurchaseOrder.objects.filter(pk=attrs["purchase_order"]).first()
        if po is None:
            raise serializers.ValidationError({"purchase_order": "Not found."})
        attrs["purchase_order_obj"] = po
        validated_lines = []
        for entry in attrs["lines"]:
            po_line = PurchaseOrderLine.objects.filter(
                pk=entry.get("purchase_order_line"),
                purchase_order=po,
            ).first()
            if po_line is None:
                raise serializers.ValidationError(
                    {"lines": "Invalid purchase order line."}
                )
            validated_lines.append(
                {
                    "purchase_order_line": po_line,
                    "quantity_received": entry["quantity_received"],
                }
            )
        attrs["validated_lines"] = validated_lines
        return attrs
