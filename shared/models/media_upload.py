"""Centralized asset upload models.

Store files once as ``Asset`` rows and attach them to any ``BaseModel`` entity
via ``AssetRelation`` generic foreign keys.

Usage::

    from django.contrib.contenttypes.models import ContentType
    from shared.models import Asset, AssetRelation, AssetRelationRole, AssetType

    asset = Asset.objects.create(
        file=uploaded_file,
        original_filename=uploaded_file.name,
        mime_type="image/png",
        file_size=uploaded_file.size,
        asset_type=AssetType.IMAGE,
    )
    AssetRelation.objects.create(
        asset=asset,
        content_object=product,
        role=AssetRelationRole.PRIMARY_IMAGE,
        field_name="hero",
        is_primary=True,
    )
"""

from pathlib import Path

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from shared.models.base import BaseModel

__all__ = [
    "Asset",
    "AssetRelation",
    "AssetType",
    "AssetRelationRole",
    "asset_upload_to",
    "infer_asset_type",
]


class AssetType(models.TextChoices):
    IMAGE = "image", "Image"
    PDF = "pdf", "PDF"
    VIDEO = "video", "Video"
    AUDIO = "audio", "Audio"
    HTML = "html", "HTML"
    DOCUMENT = "document", "Document"
    OTHER = "other", "Other"


class AssetRelationRole(models.TextChoices):
    PRIMARY_IMAGE = "primary_image", "Primary Image"
    GALLERY = "gallery", "Gallery"
    ATTACHMENT = "attachment", "Attachment"
    AVATAR = "avatar", "Avatar"
    THUMBNAIL = "thumbnail", "Thumbnail"
    COVER = "cover", "Cover"
    DOCUMENT = "document", "Document"
    OTHER = "other", "Other"


_MIME_TYPE_MAP: dict[str, str] = {
    "image/jpeg": "image",
    "image/png": "image",
    "image/gif": "image",
    "image/webp": "image",
    "image/svg+xml": "image",
    "application/pdf": "pdf",
    "video/mp4": "video",
    "video/webm": "video",
    "video/quicktime": "video",
    "audio/mpeg": "audio",
    "audio/wav": "audio",
    "audio/ogg": "audio",
    "text/html": "html",
    "application/msword": "document",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "document",
    "application/vnd.ms-excel": "document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "document",
    "text/plain": "document",
}


def infer_asset_type(mime_type: str) -> str:
    """Map a MIME type string to an ``AssetType`` value."""
    normalized = mime_type.strip().lower()
    if normalized.startswith("image/"):
        return "image"
    if normalized.startswith("video/"):
        return "video"
    if normalized.startswith("audio/"):
        return "audio"
    return _MIME_TYPE_MAP.get(normalized, "other")


def asset_upload_to(instance: "Asset", filename: str) -> str:
    """Build a deterministic storage path for an asset file."""
    ext = Path(filename).suffix.lower()
    return f"assets/{instance.asset_type}/{instance.id}{ext}"


class Asset(BaseModel):
    """Canonical uploaded file record with metadata."""

    file = models.FileField(upload_to=asset_upload_to, max_length=500)
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=127)
    file_size = models.PositiveBigIntegerField()
    asset_type = models.CharField(max_length=20, choices=AssetType.choices)
    checksum = models.CharField(max_length=64, blank=True, default="")
    title = models.CharField(max_length=255, blank=True, default="")
    alt_text = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    duration_seconds = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "shared_asset"
        indexes = [
            models.Index(fields=["asset_type"]),
            models.Index(fields=["mime_type"]),
        ]

    def __str__(self) -> str:
        return self.original_filename or str(self.id)


class AssetRelation(BaseModel):
    """Links an ``Asset`` to any domain model via generic foreign key."""

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="relations",
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = GenericForeignKey("content_type", "object_id")
    role = models.CharField(max_length=32, choices=AssetRelationRole.choices)
    field_name = models.CharField(max_length=64, blank=True, default="")
    sort_order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = "shared_asset_relation"
        indexes = [
            models.Index(
                fields=["content_type", "object_id", "field_name", "role"],
                name="shared_ar_parent_slot_idx",
            ),
            models.Index(
                fields=["content_type", "object_id", "sort_order"],
                name="shared_ar_parent_order_idx",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.is_primary:
            (
                AssetRelation.objects.filter(
                    content_type=self.content_type,
                    object_id=self.object_id,
                    field_name=self.field_name,
                    role=self.role,
                    is_primary=True,
                    is_deleted=False,
                )
                .exclude(pk=self.pk)
                .update(is_primary=False)
            )
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.asset_id} -> {self.content_type_id}:{self.object_id}"
