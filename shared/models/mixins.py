"""Reusable model mixins."""

from django.db import models

from shared.models.base import generate_uuid7

__all__ = ["UUIDPrimaryKeyMixin"]


class UUIDPrimaryKeyMixin(models.Model):
    """Abstract mixin adding a UUID v7 primary key."""

    id = models.UUIDField(
        primary_key=True,
        default=generate_uuid7,
        editable=False,
    )

    class Meta:
        abstract = True
