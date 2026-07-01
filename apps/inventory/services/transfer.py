"""Stock transfer workflow service."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from apps.inventory.models import StockMovement, StockTransfer, StockTransferLine
from apps.inventory.services.stock import StockService
from shared.responses.error_codes import ErrorCode
from shared.responses.exceptions import DomainAPIException


class TransferService:
    @classmethod
    @transaction.atomic
    def approve(cls, transfer: StockTransfer, user=None) -> StockTransfer:
        if transfer.status not in (
            StockTransfer.STATUS_DRAFT,
            StockTransfer.STATUS_PENDING,
        ):
            raise DomainAPIException(
                error_code=ErrorCode.VALIDATION_ERROR,
                user_message="Transfer cannot be approved in its current status.",
            )
        for line in transfer.lines.select_related("product", "variant"):
            qty = line.quantity_approved or line.quantity_requested
            line.quantity_approved = qty
            line.save(update_fields=["quantity_approved", "updated_at"])
            cls._decrement_source(transfer, line, qty, user)
        transfer.status = StockTransfer.STATUS_IN_TRANSIT
        transfer.save(update_fields=["status", "updated_at"])
        return transfer

    @classmethod
    @transaction.atomic
    def partial_approve(
        cls, transfer: StockTransfer, line_quantities: dict, user=None
    ) -> StockTransfer:
        if transfer.status not in (
            StockTransfer.STATUS_DRAFT,
            StockTransfer.STATUS_PENDING,
        ):
            raise DomainAPIException(
                error_code=ErrorCode.VALIDATION_ERROR,
                user_message="Transfer cannot be partially approved.",
            )
        for line in transfer.lines.select_related("product", "variant"):
            qty = Decimal(str(line_quantities.get(str(line.id), 0)))
            if qty <= 0:
                continue
            line.quantity_approved = qty
            line.save(update_fields=["quantity_approved", "updated_at"])
            cls._decrement_source(transfer, line, qty, user)
        transfer.status = StockTransfer.STATUS_IN_TRANSIT
        transfer.save(update_fields=["status", "updated_at"])
        return transfer

    @classmethod
    @transaction.atomic
    def reject(cls, transfer: StockTransfer) -> StockTransfer:
        if transfer.status in (
            StockTransfer.STATUS_RECEIVED,
            StockTransfer.STATUS_REJECTED,
        ):
            raise DomainAPIException(
                error_code=ErrorCode.VALIDATION_ERROR,
                user_message="Transfer cannot be rejected.",
            )
        transfer.status = StockTransfer.STATUS_REJECTED
        transfer.save(update_fields=["status", "updated_at"])
        return transfer

    @classmethod
    @transaction.atomic
    def ship(cls, transfer: StockTransfer) -> StockTransfer:
        if transfer.status != StockTransfer.STATUS_APPROVED:
            if transfer.status == StockTransfer.STATUS_IN_TRANSIT:
                return transfer
            raise DomainAPIException(
                error_code=ErrorCode.VALIDATION_ERROR,
                user_message="Transfer must be approved before shipping.",
            )
        transfer.status = StockTransfer.STATUS_IN_TRANSIT
        transfer.save(update_fields=["status", "updated_at"])
        return transfer

    @classmethod
    @transaction.atomic
    def receive(cls, transfer: StockTransfer, user=None) -> StockTransfer:
        if transfer.status != StockTransfer.STATUS_IN_TRANSIT:
            raise DomainAPIException(
                error_code=ErrorCode.VALIDATION_ERROR,
                user_message="Transfer must be in transit to receive.",
            )
        for line in transfer.lines.select_related("product", "variant"):
            qty = line.quantity_approved or line.quantity_requested
            line.quantity_received = qty
            line.save(update_fields=["quantity_received", "updated_at"])
            cls._increment_target(transfer, line, qty, user)
        transfer.status = StockTransfer.STATUS_RECEIVED
        transfer.save(update_fields=["status", "updated_at"])
        return transfer

    @classmethod
    def _decrement_source(cls, transfer, line: StockTransferLine, qty: Decimal, user):
        product = line.product
        variant = line.variant
        if transfer.source_branch_id:
            StockService.decrement_branch_product(
                branch=transfer.source_branch,
                product=product,
                variant=variant,
                quantity=qty,
                movement_type=StockMovement.MOVEMENT_TRANSFER_OUT,
                reference_type="stock_transfer",
                reference_id=transfer.id,
                performed_by=user,
            )
        elif transfer.source_warehouse_id:
            StockService.decrement_warehouse_product(
                warehouse=transfer.source_warehouse,
                product=product,
                variant=variant,
                quantity=qty,
                movement_type=StockMovement.MOVEMENT_TRANSFER_OUT,
                reference_type="stock_transfer",
                reference_id=transfer.id,
                performed_by=user,
            )

    @classmethod
    def _increment_target(cls, transfer, line: StockTransferLine, qty: Decimal, user):
        product = line.product
        variant = line.variant
        if transfer.target_branch_id:
            StockService.increment_branch_product(
                branch=transfer.target_branch,
                product=product,
                variant=variant,
                quantity=qty,
                movement_type=StockMovement.MOVEMENT_TRANSFER_IN,
                reference_type="stock_transfer",
                reference_id=transfer.id,
                performed_by=user,
            )
        elif transfer.target_warehouse_id:
            StockService.increment_warehouse_product(
                warehouse=transfer.target_warehouse,
                product=product,
                variant=variant,
                quantity=qty,
                movement_type=StockMovement.MOVEMENT_TRANSFER_IN,
                reference_type="stock_transfer",
                reference_id=transfer.id,
                performed_by=user,
            )
