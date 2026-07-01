"""Promotion validation service."""

from __future__ import annotations

from decimal import Decimal

from django.utils import timezone

from apps.inventory.models import Coupon, GiftVoucher, LoyaltyAccount, Promotion
from shared.responses.error_codes import ErrorCode
from shared.responses.exceptions import DomainAPIException


class PromotionService:
    @classmethod
    def validate_coupon(cls, code: str) -> tuple[Coupon, Decimal]:
        coupon = (
            Coupon.objects.select_related("promotion")
            .filter(code__iexact=code.strip(), is_active=True)
            .first()
        )
        if coupon is None:
            raise DomainAPIException(
                error_code=ErrorCode.NOT_FOUND,
                user_message="Coupon not found.",
                status_code=404,
            )
        if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
            raise DomainAPIException(
                error_code=ErrorCode.VALIDATION_ERROR,
                user_message="Coupon usage limit reached.",
            )
        promo = coupon.promotion
        cls._validate_promotion_window(promo)
        return coupon, cls._discount_amount(promo)

    @classmethod
    def validate_voucher(
        cls, code: str, amount: Decimal
    ) -> tuple[GiftVoucher, Decimal]:
        voucher = GiftVoucher.objects.filter(
            code__iexact=code.strip(), is_active=True
        ).first()
        if voucher is None:
            raise DomainAPIException(
                error_code=ErrorCode.NOT_FOUND,
                user_message="Gift voucher not found.",
                status_code=404,
            )
        if voucher.expires_at and voucher.expires_at < timezone.now():
            raise DomainAPIException(
                error_code=ErrorCode.VALIDATION_ERROR,
                user_message="Gift voucher has expired.",
            )
        applied = min(voucher.balance, amount)
        return voucher, applied

    @classmethod
    def validate_loyalty(
        cls, loyalty_account: LoyaltyAccount, points_to_redeem: int
    ) -> Decimal:
        if points_to_redeem <= 0:
            return Decimal("0")
        if loyalty_account.points_balance < points_to_redeem:
            raise DomainAPIException(
                error_code=ErrorCode.VALIDATION_ERROR,
                user_message="Insufficient loyalty points.",
            )
        return Decimal(points_to_redeem) / Decimal("100")

    @classmethod
    def _validate_promotion_window(cls, promo: Promotion) -> None:
        now = timezone.now()
        if promo.valid_from and promo.valid_from > now:
            raise DomainAPIException(
                error_code=ErrorCode.VALIDATION_ERROR,
                user_message="Promotion is not yet active.",
            )
        if promo.valid_to and promo.valid_to < now:
            raise DomainAPIException(
                error_code=ErrorCode.VALIDATION_ERROR,
                user_message="Promotion has expired.",
            )

    @classmethod
    def _discount_amount(cls, promo: Promotion) -> Decimal:
        if promo.promotion_type == Promotion.TYPE_PERCENTAGE:
            return promo.discount_value
        return promo.discount_value

    @classmethod
    def consume_coupon(cls, coupon: Coupon) -> None:
        coupon.used_count += 1
        coupon.save(update_fields=["used_count", "updated_at"])

    @classmethod
    def consume_voucher(cls, voucher: GiftVoucher, amount: Decimal) -> None:
        voucher.balance = max(Decimal("0"), voucher.balance - amount)
        voucher.save(update_fields=["balance", "updated_at"])

    @classmethod
    def consume_loyalty(cls, account: LoyaltyAccount, points: int) -> None:
        account.points_balance = max(0, account.points_balance - points)
        account.save(update_fields=["points_balance", "updated_at"])
