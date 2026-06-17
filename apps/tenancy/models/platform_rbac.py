from django.db import models

from apps.tenancy.models.constants import (
    PERMISSION_LEVEL_CHOICES,
    PERMISSION_LEVEL_NONE,
)
from shared.models import BaseModel


class PlatformRole(BaseModel):
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=80, unique=True)
    description = models.CharField(max_length=255, blank=True, default="")
    is_system = models.BooleanField(
        default=False,
        help_text="System roles cannot be deleted.",
    )
    color = models.CharField(max_length=20, blank=True, default="")

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class PlatformRolePermission(BaseModel):
    role = models.ForeignKey(
        PlatformRole, on_delete=models.CASCADE, related_name="permissions"
    )
    module_key = models.CharField(max_length=80)
    permission_level = models.CharField(
        max_length=10,
        choices=PERMISSION_LEVEL_CHOICES,
        default=PERMISSION_LEVEL_NONE,
    )

    class Meta:
        unique_together = [("role", "module_key")]
        indexes = [
            models.Index(fields=["module_key"], name="idx_platrp_module"),
        ]

    def __str__(self) -> str:
        return f"{self.role.slug}:{self.module_key}={self.permission_level}"


class PlatformUserRole(BaseModel):
    user = models.ForeignKey(
        "tenancy.User",
        on_delete=models.CASCADE,
        related_name="platform_role_assignments",
    )
    role = models.ForeignKey(
        PlatformRole, on_delete=models.CASCADE, related_name="user_assignments"
    )
    assigned_by = models.ForeignKey(
        "tenancy.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        unique_together = [("user", "role")]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user_id} -> {self.role.slug}"


class Feature(BaseModel):
    key = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=255, blank=True, default="")
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    is_system = models.BooleanField(
        default=False,
        help_text="System features cannot be disabled.",
    )
    sort_order = models.IntegerField(default=0)
    scope = models.CharField(
        max_length=20,
        choices=[
            ("platform", "Platform"),
            ("tenant", "Tenant"),
            ("shared", "Shared"),
        ],
        default="tenant",
    )

    class Meta:
        ordering = ["sort_order", "key"]

    def __str__(self) -> str:
        return self.key
