"""Abstract base model with UUID v7 primary key (Python 3.14+ stdlib ``uuid.uuid7``)."""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

__all__ = ["BaseModel", "SoftDeleteManager", "generate_uuid7"]


def generate_uuid7() -> uuid.UUID:
    """Return a new time-ordered UUID v7."""
    return uuid.uuid7()


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def all_with_deleted(self):
        return super().get_queryset()

    def deleted_only(self):
        return super().get_queryset().filter(is_deleted=True)


class BaseModel(models.Model):
    """Abstract base model with UUID v7 PK, audit fields, and soft delete.

    Requires Python 3.14+ for UUID v7 generation via ``uuid.uuid7``.

    Usage::

        from shared.models import BaseModel

        class Product(BaseModel):
            name = models.CharField(max_length=255)
    """

    id = models.UUIDField(
        primary_key=True,
        default=generate_uuid7,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created_records",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_updated_records",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_deleted_records",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Whether this item is active and usable",
    )
    is_published = models.BooleanField(
        default=False,
        help_text="Whether this item is published/visible",
    )

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Soft delete the object."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(using=using)

    def restore(self, using=None):
        """Restore a soft-deleted object."""
        self.is_deleted = False
        self.deleted_at = None
        self.save(using=using)

    def hard_delete(self, using=None, keep_parents=False):
        """Permanently delete the object."""
        super().delete(using=using, keep_parents=keep_parents)
