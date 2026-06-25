from django.db import models

from shared.models import BaseModel


class PaymentGateway(BaseModel):
    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=120)
    credential_schema = models.JSONField(default=dict, blank=True)
    platform_credentials = models.JSONField(default=dict, blank=True)
    is_enabled_for_tenants = models.BooleanField(default=False)
    is_default_for_subscriptions = models.BooleanField(default=False)
    is_sandbox = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name


class TenantPaymentGateway(BaseModel):
    """Per-tenant gateway credentials (tenant schema only)."""

    gateway_slug = models.CharField(
        max_length=50,
        unique=True,
        help_text="Must match a PaymentGateway.slug in the public schema.",
    )
    credentials = models.JSONField(default=dict, blank=True)
    is_sandbox = models.BooleanField(default=True)

    class Meta:
        ordering = ["gateway_slug"]

    def __str__(self) -> str:
        mode = "sandbox" if self.is_sandbox else "live"
        return f"{self.gateway_slug} ({mode})"
