from decimal import Decimal

from django.db import models

from shared.models import BaseModel


class Package(BaseModel):
    software_product = models.ForeignKey(
        "billing.SoftwareProduct",
        on_delete=models.CASCADE,
        related_name="packages",
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=80, unique=True)
    description = models.TextField(blank=True, default="")
    price_monthly = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0")
    )
    price_yearly = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0")
    )
    is_public = models.BooleanField(default=True)
    is_trial = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    max_branches = models.PositiveIntegerField(default=1)
    max_users = models.PositiveIntegerField(default=10)
    max_custom_roles = models.PositiveIntegerField(default=0)
    max_admins = models.PositiveIntegerField(default=0)
    max_staff = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return f"{self.software_product.slug}:{self.slug}"


class PackageFeature(BaseModel):
    package = models.ForeignKey(
        Package,
        on_delete=models.CASCADE,
        related_name="package_features",
    )
    feature = models.ForeignKey(
        "tenancy.Feature",
        on_delete=models.CASCADE,
        related_name="package_features",
    )
    limit_value = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Optional numeric cap for this feature.",
    )

    class Meta:
        unique_together = [("package", "feature")]

    def __str__(self) -> str:
        return f"{self.package.slug}:{self.feature.key}"


class PackageRoleLimit(BaseModel):
    package = models.ForeignKey(
        Package,
        on_delete=models.CASCADE,
        related_name="role_limits",
    )
    role_slug = models.SlugField(max_length=120)
    max_users = models.PositiveIntegerField(
        default=0,
        help_text="Maximum users with this role. 0 means unlimited.",
    )

    class Meta:
        unique_together = [("package", "role_slug")]

    def __str__(self) -> str:
        return f"{self.package.slug}:{self.role_slug}={self.max_users}"
