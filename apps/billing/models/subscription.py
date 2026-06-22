from django.db import models

from shared.models import BaseModel


class TenantProductSubscription(BaseModel):
    STATUS_TRIAL = "trial"
    STATUS_ACTIVE = "active"
    STATUS_PAST_DUE = "past_due"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_TRIAL, "Trial"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_PAST_DUE, "Past Due"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    BILLING_MONTHLY = "monthly"
    BILLING_YEARLY = "yearly"

    BILLING_CYCLE_CHOICES = [
        (BILLING_MONTHLY, "Monthly"),
        (BILLING_YEARLY, "Yearly"),
    ]

    tenant = models.ForeignKey(
        "tenancy.Tenant",
        on_delete=models.CASCADE,
        related_name="product_subscriptions",
    )
    software_product = models.ForeignKey(
        "billing.SoftwareProduct",
        on_delete=models.PROTECT,
        related_name="tenant_subscriptions",
    )
    package = models.ForeignKey(
        "billing.Package",
        on_delete=models.PROTECT,
        related_name="tenant_subscriptions",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_TRIAL
    )
    billing_cycle = models.CharField(
        max_length=10,
        choices=BILLING_CYCLE_CHOICES,
        default=BILLING_MONTHLY,
    )
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant", "status"],
                name="idx_tps_tenant_status",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "software_product"],
                condition=models.Q(
                    status__in=["trial", "active", "past_due"],
                    is_deleted=False,
                ),
                name="uniq_active_tenant_product_sub",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.tenant_id}:{self.software_product.slug} [{self.status}]"


class TenantSubscriptionInvoice(BaseModel):
    STATUS_INIT = "init"
    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"
    STATUS_TRIAL = "trial"

    STATUS_CHOICES = [
        (STATUS_INIT, "Initiated"),
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_TRIAL, "Trial"),
    ]

    tenant = models.ForeignKey(
        "tenancy.Tenant",
        on_delete=models.CASCADE,
        related_name="subscription_invoices",
    )
    software_product_slug = models.SlugField(max_length=80)
    package_slug = models.SlugField(max_length=80)
    tran_id = models.CharField(max_length=100, unique=True, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_INIT
    )
    billing_cycle = models.CharField(max_length=10, default="monthly")
    period_start = models.DateTimeField(null=True, blank=True)
    period_end = models.DateTimeField(null=True, blank=True)
    gateway_slug = models.CharField(max_length=50, blank=True, default="")
    gateway_response = models.JSONField(default=dict, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def delete(self, using=None, keep_parents=False):
        super().hard_delete(using=using, keep_parents=keep_parents)

    def __str__(self) -> str:
        return f"{self.tran_id} [{self.status}]"
