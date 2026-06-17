from django.db import models

from apps.tenancy.models.constants import (
    PERMISSION_LEVEL_CHOICES,
    PERMISSION_LEVEL_VIEW,
)
from shared.models import BaseModel


class Role(BaseModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True, default="")
    is_system = models.BooleanField(
        default=False,
        help_text="System roles (e.g. admin) cannot be deleted.",
    )
    color = models.CharField(max_length=20, blank=True, default="")

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class RolePermission(BaseModel):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="permissions")
    feature_key = models.CharField(max_length=120)
    permission_level = models.CharField(
        max_length=10,
        choices=PERMISSION_LEVEL_CHOICES,
        default=PERMISSION_LEVEL_VIEW,
    )

    class Meta:
        unique_together = [("role", "feature_key")]
        indexes = [models.Index(fields=["feature_key"])]

    def __str__(self) -> str:
        return f"{self.role.name}::{self.feature_key}={self.permission_level}"


class UserRole(BaseModel):
    user_id = models.UUIDField(db_index=True)
    user_email = models.EmailField(blank=True, default="")
    branch = models.ForeignKey(
        "branch.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_roles",
    )
    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name="user_assignments"
    )
    assigned_by_email = models.EmailField(blank=True, default="")

    class Meta:
        unique_together = [("user_id", "role")]
        indexes = [models.Index(fields=["user_email"])]

    def __str__(self) -> str:
        return f"{self.user_email or self.user_id} → {self.role.name}"
