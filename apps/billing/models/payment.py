from django.db import models

from shared.models import BaseModel


class PaymentTransaction(BaseModel):
    """Tenant-scoped online payment record (future POS / order linkage)."""

    STATUS_INIT = "init"
    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_INIT, "Initiated"),
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    tran_id = models.CharField(max_length=100, unique=True, db_index=True)
    gateway_slug = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_INIT
    )
    source_type = models.CharField(max_length=50, blank=True, default="")
    source_id = models.UUIDField(null=True, blank=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    val_id = models.CharField(max_length=100, blank=True, default="")
    validated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def delete(self, using=None, keep_parents=False):
        super().hard_delete(using=using, keep_parents=keep_parents)

    def __str__(self) -> str:
        return f"{self.tran_id} [{self.status}]"
