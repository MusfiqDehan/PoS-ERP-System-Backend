from django.conf import settings
from django.db import models

from shared.models import BaseModel


class Branch(BaseModel):
    STATUS_ACTIVE = "active"
    STATUS_MAINTENANCE = "maintenance"
    STATUS_OPENING_SOON = "opening_soon"
    STATUS_CLOSED = "closed"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_MAINTENANCE, "Maintenance"),
        (STATUS_OPENING_SOON, "Opening Soon"),
        (STATUS_CLOSED, "Closed"),
    ]

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    is_headquarters = models.BooleanField(default=False)
    address = models.TextField(blank=True, default="")
    city = models.CharField(max_length=120, blank=True, default="")
    location = models.CharField(max_length=250, blank=True, default="")
    description = models.TextField(blank=True, default="")
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_branches",
    )
    phone_number = models.CharField(max_length=20, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    operating_hours = models.CharField(max_length=100, blank=True, default="")
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    weekdays_hours = models.CharField(max_length=50, blank=True, default="")
    weekend_hours = models.CharField(max_length=50, blank=True, default="")
    opening_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE
    )
    capacity = models.PositiveIntegerField(default=0)
    staff_count = models.PositiveIntegerField(default=0)
    monthly_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    revenue_trend = models.FloatField(default=0.0)
    rating = models.FloatField(default=0.0)
    image = models.CharField(max_length=500, blank=True, default="")
    homepage_image = models.CharField(max_length=500, blank=True, default="")
    website = models.URLField(blank=True, default="")
    show_on_homepage = models.BooleanField(default=False)
    is_flagship = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        indexes = [
            models.Index(
                fields=["is_active", "display_order", "id"],
                name="idx_branch_active_order",
            ),
        ]

    def __str__(self) -> str:
        return self.name
