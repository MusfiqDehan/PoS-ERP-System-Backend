from django.db import models
from django_tenants.models import DomainMixin, TenantMixin

from shared.models import UUIDPrimaryKeyMixin


class Tenant(UUIDPrimaryKeyMixin, TenantMixin):
    ENTRY_ALLOWED_STATUSES = {"active", "trial"}

    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    code = models.CharField(max_length=50, unique=True)

    timezone = models.CharField(max_length=50, default="Asia/Dhaka")
    currency = models.CharField(max_length=10, default="USD")
    locale = models.CharField(max_length=10, default="en")

    plan = models.CharField(max_length=50, default="free")
    billing_email = models.EmailField(blank=True)
    subscription_start = models.DateTimeField(null=True, blank=True)
    subscription_end = models.DateTimeField(null=True, blank=True)

    is_trial = models.BooleanField(default=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ("active", "Active"),
            ("suspended", "Suspended"),
            ("cancelled", "Cancelled"),
            ("trial", "Trial"),
        ],
        default="trial",
    )

    max_users = models.IntegerField(default=10)
    max_branches = models.IntegerField(default=1)
    max_staff_per_branch = models.IntegerField(
        default=0,
        help_text="Maximum staff per branch. 0 means unlimited.",
    )
    is_enabled = models.BooleanField(default=True)

    custom_domain_enabled = models.BooleanField(
        default=False,
        help_text="When True, this tenant may connect a custom domain from Settings.",
    )
    landing_page_enabled = models.BooleanField(default=False)
    features = models.JSONField(default=dict, blank=True)
    owner_email = models.EmailField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "tenancy.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_tenants",
    )
    updated_by = models.ForeignKey(
        "tenancy.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_tenants",
    )

    auto_create_schema = True

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def allows_user_entry(self) -> bool:
        return self.is_enabled and self.status in self.ENTRY_ALLOWED_STATUSES


class Domain(UUIDPrimaryKeyMixin, DomainMixin):
    class Meta:
        indexes = [
            models.Index(
                fields=["tenant", "is_primary", "id"],
                name="idx_domain_tenant_primary",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.domain:
            self.domain = self.domain.strip().lower()
        super().save(*args, **kwargs)
