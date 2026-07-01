"""Stock mutation service — all quantity changes must go through here."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from django.db import transaction

from apps.inventory.models import StockLevel, StockMovement
from shared.responses.error_codes import ErrorCode
from shared.responses.exceptions import DomainAPIException

if TYPE_CHECKING:
    from apps.branch.models import Branch
    from apps.inventory.models import Product, ProductVariant, Warehouse
    from django.contrib.auth.models import AbstractBaseUser


class StockService:
    allow_negative_stock = False

    @classmethod
    def _lock_stock_level(cls, stock_level_id: UUID) -> StockLevel:
        return StockLevel.objects.select_for_update().get(pk=stock_level_id)

    @classmethod
    def get_or_create_branch_stock(
        cls,
        *,
        branch: Branch,
        product: Product,
        variant: ProductVariant | None = None,
        qty_alert: Decimal | None = None,
    ) -> StockLevel:
        defaults: dict = {"qty_alert": qty_alert or product.min_qty_alert or 0}
        stock_level, _ = StockLevel.objects.get_or_create(
            location_type=StockLevel.LOCATION_BRANCH,
            branch=branch,
            warehouse=None,
            product=product,
            variant=variant,
            defaults=defaults,
        )
        return stock_level

    @classmethod
    def get_or_create_warehouse_stock(
        cls,
        *,
        warehouse: Warehouse,
        product: Product,
        variant: ProductVariant | None = None,
        qty_alert: Decimal | None = None,
    ) -> StockLevel:
        defaults: dict = {"qty_alert": qty_alert or product.min_qty_alert or 0}
        stock_level, _ = StockLevel.objects.get_or_create(
            location_type=StockLevel.LOCATION_WAREHOUSE,
            branch=None,
            warehouse=warehouse,
            product=product,
            variant=variant,
            defaults=defaults,
        )
        return stock_level

    @classmethod
    def _apply_delta(
        cls,
        *,
        stock_level: StockLevel,
        delta: Decimal,
        movement_type: str,
        reference_type: str = "",
        reference_id: UUID | None = None,
        performed_by: AbstractBaseUser | None = None,
        notes: str = "",
    ) -> StockMovement:
        if delta == 0:
            raise DomainAPIException(
                error_code=ErrorCode.VALIDATION_ERROR,
                user_message="Quantity delta cannot be zero.",
            )
        new_qty = stock_level.quantity + delta
        if new_qty < 0:
            if not cls.allow_negative_stock:
                raise DomainAPIException(
                    error_code=ErrorCode.INSUFFICIENT_STOCK,
                    status_code=400,
                )
            if new_qty < 0:
                raise DomainAPIException(
                    error_code=ErrorCode.NEGATIVE_STOCK_NOT_ALLOWED,
                    status_code=400,
                )
        stock_level.quantity = new_qty
        stock_level.save(update_fields=["quantity", "updated_at"])
        return StockMovement.objects.create(
            stock_level=stock_level,
            movement_type=movement_type,
            quantity_delta=delta,
            reference_type=reference_type,
            reference_id=reference_id,
            performed_by=performed_by,
            notes=notes,
        )

    @classmethod
    @transaction.atomic
    def increment(
        cls,
        *,
        stock_level_id: UUID,
        quantity: Decimal,
        movement_type: str,
        reference_type: str = "",
        reference_id: UUID | None = None,
        performed_by: AbstractBaseUser | None = None,
        notes: str = "",
    ) -> StockMovement:
        stock_level = cls._lock_stock_level(stock_level_id)
        return cls._apply_delta(
            stock_level=stock_level,
            delta=abs(quantity),
            movement_type=movement_type,
            reference_type=reference_type,
            reference_id=reference_id,
            performed_by=performed_by,
            notes=notes,
        )

    @classmethod
    @transaction.atomic
    def decrement(
        cls,
        *,
        stock_level_id: UUID,
        quantity: Decimal,
        movement_type: str,
        reference_type: str = "",
        reference_id: UUID | None = None,
        performed_by: AbstractBaseUser | None = None,
        notes: str = "",
    ) -> StockMovement:
        stock_level = cls._lock_stock_level(stock_level_id)
        return cls._apply_delta(
            stock_level=stock_level,
            delta=-abs(quantity),
            movement_type=movement_type,
            reference_type=reference_type,
            reference_id=reference_id,
            performed_by=performed_by,
            notes=notes,
        )

    @classmethod
    @transaction.atomic
    def adjust(
        cls,
        *,
        stock_level_id: UUID,
        new_quantity: Decimal,
        performed_by: AbstractBaseUser | None = None,
        reference_id: UUID | None = None,
        notes: str = "",
    ) -> tuple[StockMovement, Decimal]:
        stock_level = cls._lock_stock_level(stock_level_id)
        delta = new_quantity - stock_level.quantity
        movement = cls._apply_delta(
            stock_level=stock_level,
            delta=delta,
            movement_type=StockMovement.MOVEMENT_ADJUSTMENT,
            reference_type="stock_adjustment",
            reference_id=reference_id,
            performed_by=performed_by,
            notes=notes,
        )
        return movement, stock_level.quantity

    @classmethod
    @transaction.atomic
    def decrement_branch_product(
        cls,
        *,
        branch: Branch,
        product: Product,
        variant: ProductVariant | None,
        quantity: Decimal,
        movement_type: str,
        reference_type: str = "",
        reference_id: UUID | None = None,
        performed_by: AbstractBaseUser | None = None,
    ) -> StockMovement:
        stock_level = cls.get_or_create_branch_stock(
            branch=branch, product=product, variant=variant
        )
        return cls.decrement(
            stock_level_id=stock_level.id,
            quantity=quantity,
            movement_type=movement_type,
            reference_type=reference_type,
            reference_id=reference_id,
            performed_by=performed_by,
        )

    @classmethod
    @transaction.atomic
    def increment_branch_product(
        cls,
        *,
        branch: Branch,
        product: Product,
        variant: ProductVariant | None,
        quantity: Decimal,
        movement_type: str,
        reference_type: str = "",
        reference_id: UUID | None = None,
        performed_by: AbstractBaseUser | None = None,
    ) -> StockMovement:
        stock_level = cls.get_or_create_branch_stock(
            branch=branch, product=product, variant=variant
        )
        return cls.increment(
            stock_level_id=stock_level.id,
            quantity=quantity,
            movement_type=movement_type,
            reference_type=reference_type,
            reference_id=reference_id,
            performed_by=performed_by,
        )

    @classmethod
    @transaction.atomic
    def increment_warehouse_product(
        cls,
        *,
        warehouse: Warehouse,
        product: Product,
        variant: ProductVariant | None,
        quantity: Decimal,
        movement_type: str,
        reference_type: str = "",
        reference_id: UUID | None = None,
        performed_by: AbstractBaseUser | None = None,
    ) -> StockMovement:
        stock_level = cls.get_or_create_warehouse_stock(
            warehouse=warehouse, product=product, variant=variant
        )
        return cls.increment(
            stock_level_id=stock_level.id,
            quantity=quantity,
            movement_type=movement_type,
            reference_type=reference_type,
            reference_id=reference_id,
            performed_by=performed_by,
        )

    @classmethod
    @transaction.atomic
    def decrement_warehouse_product(
        cls,
        *,
        warehouse: Warehouse,
        product: Product,
        variant: ProductVariant | None,
        quantity: Decimal,
        movement_type: str,
        reference_type: str = "",
        reference_id: UUID | None = None,
        performed_by: AbstractBaseUser | None = None,
    ) -> StockMovement:
        stock_level = cls.get_or_create_warehouse_stock(
            warehouse=warehouse, product=product, variant=variant
        )
        return cls.decrement(
            stock_level_id=stock_level.id,
            quantity=quantity,
            movement_type=movement_type,
            reference_type=reference_type,
            reference_id=reference_id,
            performed_by=performed_by,
        )
