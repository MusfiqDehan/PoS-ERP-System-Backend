from __future__ import annotations

from django.db import models

from apps.branch.models import Branch
from shared.models import BaseModel


class Customer(BaseModel):
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customers",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class LoyaltyAccount(BaseModel):
    customer = models.OneToOneField(
        Customer,
        on_delete=models.CASCADE,
        related_name="loyalty_account",
    )
    points_balance = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return f"Loyalty for {self.customer.name}"


class Promotion(BaseModel):
    TYPE_PERCENTAGE = "percentage"
    TYPE_FIXED = "fixed_amount"
    TYPE_BUY_X_GET_Y = "buy_x_get_y"
    TYPE_CHOICES = [
        (TYPE_PERCENTAGE, "Percentage"),
        (TYPE_FIXED, "Fixed Amount"),
        (TYPE_BUY_X_GET_Y, "Buy X Get Y"),
    ]

    name = models.CharField(max_length=255)
    promotion_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    rules = models.JSONField(default=dict, blank=True)
    discount_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="promotions",
    )

    class Meta:
        ordering = ["name"]


class Coupon(BaseModel):
    code = models.CharField(max_length=50, unique=True)
    promotion = models.ForeignKey(
        Promotion,
        on_delete=models.CASCADE,
        related_name="coupons",
    )
    usage_limit = models.PositiveIntegerField(default=0)
    used_count = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return self.code


class GiftVoucher(BaseModel):
    code = models.CharField(max_length=50, unique=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return self.code
