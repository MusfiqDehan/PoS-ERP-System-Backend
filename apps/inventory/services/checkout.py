"""POS checkout service — atomic sale creation with stock decrement."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from apps.branch.models import Branch
from apps.inventory.models import (
    Coupon,
    Customer,
    GiftVoucher,
    LoyaltyAccount,
    Product,
    ProductVariant,
    Sale,
    SaleDiscount,
    SaleLine,
    SalePayment,
    StockLevel,
    StockMovement,
)
from apps.inventory.services.promotion import PromotionService
from apps.inventory.services.stock import StockService
from apps.inventory.utils import generate_ref_number
from shared.responses.error_codes import ErrorCode
from shared.responses.exceptions import DomainAPIException


class CheckoutService:
    @classmethod
    @transaction.atomic
    def checkout(
        cls,
        *,
        branch: Branch,
        cashier,
        lines: list[dict],
        payments: list[dict],
        customer: Customer | None = None,
        coupon_code: str | None = None,
        voucher_code: str | None = None,
        loyalty_points: int = 0,
        idempotency_key: str | None = None,
        notes: str = "",
    ) -> Sale:
        if idempotency_key:
            existing = Sale.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                return existing

        subtotal = Decimal("0")
        sale_lines: list[tuple[Product, ProductVariant | None, Decimal, Decimal]] = []

        for entry in lines:
            product = entry["product"]
            variant = entry.get("variant")
            qty = Decimal(str(entry["quantity"]))
            unit_price = Decimal(str(entry.get("unit_price", product.price)))
            line_total = qty * unit_price
            subtotal += line_total
            sale_lines.append((product, variant, qty, unit_price))

            stock_level = StockService.get_or_create_branch_stock(
                branch=branch, product=product, variant=variant
            )
            locked = StockLevel.objects.select_for_update().get(pk=stock_level.pk)
            if locked.quantity < qty:
                raise DomainAPIException(
                    error_code=ErrorCode.INSUFFICIENT_STOCK,
                    status_code=400,
                )

        discount_total = Decimal("0")
        coupon: Coupon | None = None
        voucher: GiftVoucher | None = None
        voucher_discount = Decimal("0")
        loyalty_discount = Decimal("0")
        loyalty_account: LoyaltyAccount | None = None

        if coupon_code:
            coupon, coupon_discount = PromotionService.validate_coupon(coupon_code)
            discount_total += min(
                (
                    subtotal * coupon_discount / Decimal("100")
                    if coupon.promotion.promotion_type == "percentage"
                    else coupon_discount
                ),
                subtotal,
            )

        if voucher_code:
            voucher, voucher_discount = PromotionService.validate_voucher(
                voucher_code, subtotal - discount_total
            )
            discount_total += voucher_discount

        if customer and loyalty_points:
            loyalty_account = getattr(customer, "loyalty_account", None)
            if loyalty_account is None:
                raise DomainAPIException(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    user_message="Customer has no loyalty account.",
                )
            loyalty_discount = PromotionService.validate_loyalty(
                loyalty_account, loyalty_points
            )
            discount_total += loyalty_discount

        tax = Decimal("0")
        total = max(Decimal("0"), subtotal - discount_total + tax)

        payment_total = sum(Decimal(str(p["amount"])) for p in payments)
        if payment_total != total:
            raise DomainAPIException(
                error_code=ErrorCode.VALIDATION_ERROR,
                user_message="Payment total must equal sale total.",
            )

        sale = Sale.objects.create(
            branch=branch,
            customer=customer,
            cashier=cashier,
            status=Sale.STATUS_COMPLETED,
            subtotal=subtotal,
            tax=tax,
            discount=discount_total,
            total=total,
            ref_number=generate_ref_number("SALE"),
            idempotency_key=idempotency_key,
            notes=notes,
        )

        for product, variant, qty, unit_price in sale_lines:
            line_total = qty * unit_price
            SaleLine.objects.create(
                sale=sale,
                product=product,
                variant=variant,
                quantity=qty,
                unit_price=unit_price,
                line_total=line_total,
            )
            StockService.decrement_branch_product(
                branch=branch,
                product=product,
                variant=variant,
                quantity=qty,
                movement_type=StockMovement.MOVEMENT_SALE,
                reference_type="sale",
                reference_id=sale.id,
                performed_by=cashier,
            )

        for payment in payments:
            SalePayment.objects.create(
                sale=sale,
                method=payment["method"],
                amount=Decimal(str(payment["amount"])),
                reference=payment.get("reference", ""),
            )

        if coupon:
            SaleDiscount.objects.create(
                sale=sale,
                discount_type=SaleDiscount.TYPE_COUPON,
                reference_id=coupon.id,
                amount=discount_total,
            )
            PromotionService.consume_coupon(coupon)
        if voucher:
            SaleDiscount.objects.create(
                sale=sale,
                discount_type=SaleDiscount.TYPE_VOUCHER,
                reference_id=voucher.id,
                amount=voucher_discount,
            )
            PromotionService.consume_voucher(voucher, voucher_discount)
        if loyalty_account and loyalty_points:
            SaleDiscount.objects.create(
                sale=sale,
                discount_type=SaleDiscount.TYPE_LOYALTY,
                reference_id=loyalty_account.id,
                amount=loyalty_discount,
            )
            PromotionService.consume_loyalty(loyalty_account, loyalty_points)

        return sale

    @classmethod
    @transaction.atomic
    def cancel_sale(cls, sale: Sale, user=None) -> Sale:
        if sale.status == Sale.STATUS_CANCELLED:
            return sale
        if sale.status != Sale.STATUS_COMPLETED:
            raise DomainAPIException(
                error_code=ErrorCode.VALIDATION_ERROR,
                user_message="Only completed sales can be cancelled.",
            )
        for line in sale.lines.select_related("product", "variant"):
            StockService.increment_branch_product(
                branch=sale.branch,
                product=line.product,
                variant=line.variant,
                quantity=line.quantity,
                movement_type=StockMovement.MOVEMENT_SALE_CANCEL,
                reference_type="sale",
                reference_id=sale.id,
                performed_by=user,
            )
        sale.status = Sale.STATUS_CANCELLED
        sale.save(update_fields=["status", "updated_at"])
        return sale

    @classmethod
    def validate_cart(
        cls,
        *,
        branch: Branch,
        lines: list[dict],
        coupon_code: str | None = None,
        voucher_code: str | None = None,
    ) -> dict:
        validated_lines = []
        subtotal = Decimal("0")
        for entry in lines:
            product: Product = entry["product"]
            variant: ProductVariant | None = entry.get("variant")
            qty = Decimal(str(entry["quantity"]))
            stock_level = StockService.get_or_create_branch_stock(
                branch=branch, product=product, variant=variant
            )
            unit_price = Decimal(str(entry.get("unit_price", product.price)))
            line_total = qty * unit_price
            subtotal += line_total
            validated_lines.append(
                {
                    "product_id": str(product.id),
                    "variant_id": str(variant.id) if variant else None,
                    "quantity": str(qty),
                    "unit_price": str(unit_price),
                    "line_total": str(line_total),
                    "available_stock": str(stock_level.quantity),
                    "sufficient_stock": stock_level.quantity >= qty,
                }
            )
        discount = Decimal("0")
        if coupon_code:
            _, coupon_discount = PromotionService.validate_coupon(coupon_code)
            discount += coupon_discount
        if voucher_code:
            _, voucher_discount = PromotionService.validate_voucher(
                voucher_code, subtotal
            )
            discount += voucher_discount
        return {
            "lines": validated_lines,
            "subtotal": str(subtotal),
            "discount": str(discount),
            "total": str(max(Decimal("0"), subtotal - discount)),
        }
