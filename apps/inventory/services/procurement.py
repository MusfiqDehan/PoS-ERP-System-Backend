"""Purchase order and goods receipt service."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from apps.inventory.models import (
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseOrder,
    StockMovement,
)
from apps.inventory.services.stock import StockService
from apps.inventory.utils import generate_ref_number
from shared.responses.error_codes import ErrorCode
from shared.responses.exceptions import DomainAPIException


class ProcurementService:
    @classmethod
    @transaction.atomic
    def send_purchase_order(cls, purchase_order: PurchaseOrder) -> PurchaseOrder:
        if purchase_order.status != PurchaseOrder.STATUS_DRAFT:
            raise DomainAPIException(
                error_code=ErrorCode.VALIDATION_ERROR,
                user_message="Only draft purchase orders can be sent.",
            )
        purchase_order.status = PurchaseOrder.STATUS_SENT
        purchase_order.save(update_fields=["status", "updated_at"])
        return purchase_order

    @classmethod
    @transaction.atomic
    def cancel_purchase_order(cls, purchase_order: PurchaseOrder) -> PurchaseOrder:
        if purchase_order.status == PurchaseOrder.STATUS_RECEIVED:
            raise DomainAPIException(
                error_code=ErrorCode.VALIDATION_ERROR,
                user_message="Received purchase orders cannot be cancelled.",
            )
        purchase_order.status = PurchaseOrder.STATUS_CANCELLED
        purchase_order.save(update_fields=["status", "updated_at"])
        return purchase_order

    @classmethod
    @transaction.atomic
    def create_goods_receipt(
        cls,
        *,
        purchase_order: PurchaseOrder,
        lines: list[dict],
        received_by=None,
    ) -> GoodsReceipt:
        if purchase_order.status != PurchaseOrder.STATUS_SENT:
            raise DomainAPIException(
                error_code=ErrorCode.VALIDATION_ERROR,
                user_message="Goods can only be received for sent purchase orders.",
            )
        receipt = GoodsReceipt.objects.create(
            purchase_order=purchase_order,
            warehouse=purchase_order.warehouse,
            received_by=received_by,
            ref_number=generate_ref_number("GR"),
            status=GoodsReceipt.STATUS_DRAFT,
        )
        for entry in lines:
            po_line = entry["purchase_order_line"]
            qty = Decimal(str(entry["quantity_received"]))
            GoodsReceiptLine.objects.create(
                goods_receipt=receipt,
                purchase_order_line=po_line,
                product=po_line.product,
                variant=po_line.variant,
                quantity_received=qty,
            )
        return receipt

    @classmethod
    @transaction.atomic
    def confirm_goods_receipt(cls, receipt: GoodsReceipt, user=None) -> GoodsReceipt:
        if receipt.status == GoodsReceipt.STATUS_CONFIRMED:
            return receipt
        if receipt.status != GoodsReceipt.STATUS_DRAFT:
            raise DomainAPIException(
                error_code=ErrorCode.VALIDATION_ERROR,
                user_message="Goods receipt cannot be confirmed.",
            )
        po = receipt.purchase_order
        for line in receipt.lines.select_related("product", "variant"):
            StockService.increment_warehouse_product(
                warehouse=receipt.warehouse,
                product=line.product,
                variant=line.variant,
                quantity=line.quantity_received,
                movement_type=StockMovement.MOVEMENT_PURCHASE_RECEIPT,
                reference_type="goods_receipt",
                reference_id=receipt.id,
                performed_by=user,
            )
        receipt.status = GoodsReceipt.STATUS_CONFIRMED
        receipt.save(update_fields=["status", "updated_at"])
        po.status = PurchaseOrder.STATUS_RECEIVED
        po.save(update_fields=["status", "updated_at"])
        return receipt
