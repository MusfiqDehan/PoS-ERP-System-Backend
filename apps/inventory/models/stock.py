from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.branch.models import Branch
from shared.models import BaseModel

from .catalog import Product, ProductVariant
from .location import Warehouse


class StockLevel(BaseModel):
    LOCATION_BRANCH = "branch"
    LOCATION_WAREHOUSE = "warehouse"
    LOCATION_TYPE_CHOICES = [
        (LOCATION_BRANCH, "Branch"),
        (LOCATION_WAREHOUSE, "Warehouse"),
    ]

    location_type = models.CharField(max_length=20, choices=LOCATION_TYPE_CHOICES)
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="stock_levels",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="stock_levels",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="stock_levels",
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="stock_levels",
    )
    quantity = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    qty_alert = models.DecimalField(max_digits=14, decimal_places=3, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "product"],
                condition=models.Q(
                    location_type="branch",
                    variant__isnull=True,
                ),
                name="uniq_branch_stock_product_no_variant",
            ),
            models.UniqueConstraint(
                fields=["branch", "product", "variant"],
                condition=models.Q(
                    location_type="branch",
                    variant__isnull=False,
                ),
                name="uniq_branch_stock_product_with_variant",
            ),
            models.UniqueConstraint(
                fields=["warehouse", "product"],
                condition=models.Q(
                    location_type="warehouse",
                    variant__isnull=True,
                ),
                name="uniq_warehouse_stock_product_no_variant",
            ),
            models.UniqueConstraint(
                fields=["warehouse", "product", "variant"],
                condition=models.Q(
                    location_type="warehouse",
                    variant__isnull=False,
                ),
                name="uniq_warehouse_stock_product_with_variant",
            ),
        ]
        indexes = [
            models.Index(fields=["location_type", "branch"]),
            models.Index(fields=["location_type", "warehouse"]),
            models.Index(fields=["product"]),
        ]

    def __str__(self) -> str:
        loc = self.branch or self.warehouse
        return f"{self.product.sku} @ {loc} = {self.quantity}"


class StockMovement(BaseModel):
    MOVEMENT_SALE = "sale"
    MOVEMENT_SALE_CANCEL = "sale_cancel"
    MOVEMENT_ADJUSTMENT = "adjustment"
    MOVEMENT_TRANSFER_OUT = "transfer_out"
    MOVEMENT_TRANSFER_IN = "transfer_in"
    MOVEMENT_PURCHASE_RECEIPT = "purchase_receipt"
    MOVEMENT_TYPE_CHOICES = [
        (MOVEMENT_SALE, "Sale"),
        (MOVEMENT_SALE_CANCEL, "Sale Cancel"),
        (MOVEMENT_ADJUSTMENT, "Adjustment"),
        (MOVEMENT_TRANSFER_OUT, "Transfer Out"),
        (MOVEMENT_TRANSFER_IN, "Transfer In"),
        (MOVEMENT_PURCHASE_RECEIPT, "Purchase Receipt"),
    ]

    stock_level = models.ForeignKey(
        StockLevel,
        on_delete=models.PROTECT,
        related_name="movements",
    )
    movement_type = models.CharField(max_length=30, choices=MOVEMENT_TYPE_CHOICES)
    quantity_delta = models.DecimalField(max_digits=14, decimal_places=3)
    reference_type = models.CharField(max_length=50, blank=True, default="")
    reference_id = models.UUIDField(null=True, blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_movements",
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.movement_type} {self.quantity_delta}"


class StockAdjustment(BaseModel):
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="stock_adjustments",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="stock_adjustments",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="stock_adjustments",
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_adjustments",
    )
    quantity_before = models.DecimalField(max_digits=14, decimal_places=3)
    quantity_after = models.DecimalField(max_digits=14, decimal_places=3)
    reason = models.TextField(blank=True, default="")
    responsible_person = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_adjustments",
    )

    class Meta:
        ordering = ["-created_at"]


class StockTransfer(BaseModel):
    TYPE_BRANCH_BRANCH = "branch_branch"
    TYPE_WAREHOUSE_BRANCH = "warehouse_branch"
    TYPE_WAREHOUSE_WAREHOUSE = "warehouse_warehouse"
    TRANSFER_TYPE_CHOICES = [
        (TYPE_BRANCH_BRANCH, "Branch to Branch"),
        (TYPE_WAREHOUSE_BRANCH, "Warehouse to Branch"),
        (TYPE_WAREHOUSE_WAREHOUSE, "Warehouse to Warehouse"),
    ]

    STATUS_DRAFT = "draft"
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_IN_TRANSIT = "in_transit"
    STATUS_RECEIVED = "received"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_IN_TRANSIT, "In Transit"),
        (STATUS_RECEIVED, "Received"),
        (STATUS_REJECTED, "Rejected"),
    ]

    transfer_type = models.CharField(max_length=30, choices=TRANSFER_TYPE_CHOICES)
    source_branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="outgoing_transfers",
    )
    source_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="outgoing_transfers",
    )
    target_branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="incoming_transfers",
    )
    target_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="incoming_transfers",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )
    ref_number = models.CharField(max_length=50, unique=True)
    notes = models.TextField(blank=True, default="")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_transfers",
    )

    class Meta:
        ordering = ["-created_at"]


class StockTransferLine(BaseModel):
    transfer = models.ForeignKey(
        StockTransfer,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    quantity_requested = models.DecimalField(max_digits=14, decimal_places=3)
    quantity_approved = models.DecimalField(
        max_digits=14, decimal_places=3, default=0
    )
    quantity_received = models.DecimalField(
        max_digits=14, decimal_places=3, default=0
    )


class StockRequest(BaseModel):
    TYPE_BRANCH_TRANSFER = "branch_transfer"
    TYPE_WAREHOUSE_FULFILLMENT = "warehouse_fulfillment"
    REQUEST_TYPE_CHOICES = [
        (TYPE_BRANCH_TRANSFER, "Branch Transfer"),
        (TYPE_WAREHOUSE_FULFILLMENT, "Warehouse Fulfillment"),
    ]

    STATUS_DRAFT = "draft"
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_FULFILLED = "fulfilled"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_FULFILLED, "Fulfilled"),
        (STATUS_REJECTED, "Rejected"),
    ]

    PRIORITY_LOW = "low"
    PRIORITY_NORMAL = "normal"
    PRIORITY_HIGH = "high"
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, "Low"),
        (PRIORITY_NORMAL, "Normal"),
        (PRIORITY_HIGH, "High"),
    ]

    request_type = models.CharField(max_length=30, choices=REQUEST_TYPE_CHOICES)
    requesting_branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name="stock_requests",
    )
    source_branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="fulfilling_stock_requests",
    )
    source_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="fulfilling_stock_requests",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default=PRIORITY_NORMAL,
    )
    ref_number = models.CharField(max_length=50, unique=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]


class StockRequestLine(BaseModel):
    request = models.ForeignKey(
        StockRequest,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    quantity_requested = models.DecimalField(max_digits=14, decimal_places=3)
    quantity_approved = models.DecimalField(
        max_digits=14, decimal_places=3, default=0
    )
