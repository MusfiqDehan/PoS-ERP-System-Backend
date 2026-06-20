"""Attach and resolve primary image assets via AssetRelation."""

from __future__ import annotations

from contextlib import AbstractContextManager, nullcontext
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django_tenants.utils import get_public_schema_name, schema_context

from shared.models import (
    Asset,
    AssetRelation,
    AssetRelationRole,
    AssetType,
    infer_asset_type,
)

USER_PROFILE_PICTURE_ROLE = AssetRelationRole.AVATAR
USER_PROFILE_PICTURE_FIELD = "profile_picture"
TENANT_COMPANY_LOGO_ROLE = AssetRelationRole.PRIMARY_IMAGE
TENANT_COMPANY_LOGO_FIELD = "company_logo"
MAX_IMAGE_UPLOAD_BYTES = 5 * 1024 * 1024


class AssetAttachmentError(ValidationError):
    """Raised when an uploaded file cannot be attached."""


def serialize_asset_summary(asset: Asset | None) -> dict[str, str] | None:
    if asset is None or asset.is_deleted:
        return None
    return {
        "id": str(asset.id),
        "url": asset.file.url if asset.file else "",
        "mime_type": asset.mime_type,
        "original_filename": asset.original_filename,
        "alt_text": asset.alt_text,
    }


class AssetAttachmentService:
    @staticmethod
    def _schema_context_for(parent: Any) -> AbstractContextManager[Any]:
        from apps.tenancy.models import Tenant

        if isinstance(parent, Tenant):
            return schema_context(get_public_schema_name())
        return nullcontext()

    @staticmethod
    def _validate_image_file(uploaded_file: Any) -> None:
        mime_type = getattr(uploaded_file, "content_type", "") or ""
        if infer_asset_type(mime_type) != AssetType.IMAGE:
            raise AssetAttachmentError("File must be an image.")
        size = getattr(uploaded_file, "size", 0) or 0
        if size > MAX_IMAGE_UPLOAD_BYTES:
            raise AssetAttachmentError("Image exceeds maximum upload size.")

    @staticmethod
    def get_primary_asset(*, parent: Any, role: str, field_name: str) -> Asset | None:
        with AssetAttachmentService._schema_context_for(parent):
            content_type = ContentType.objects.get_for_model(parent)
            relation = (
                AssetRelation.objects.filter(
                    content_type=content_type,
                    object_id=parent.pk,
                    role=role,
                    field_name=field_name,
                    is_primary=True,
                    is_deleted=False,
                )
                .select_related("asset")
                .first()
            )
            if relation is None or relation.asset.is_deleted:
                return None
            return relation.asset

    @staticmethod
    def attach_image(
        *,
        file: Any,
        parent: Any,
        role: str,
        field_name: str,
        actor: Any | None = None,
    ) -> AssetRelation:
        AssetAttachmentService._validate_image_file(file)
        mime_type = getattr(file, "content_type", "") or "application/octet-stream"
        original_filename = getattr(file, "name", "upload")

        with AssetAttachmentService._schema_context_for(parent):
            asset = Asset(
                file=file,
                original_filename=original_filename,
                mime_type=mime_type,
                file_size=getattr(file, "size", 0) or 0,
                asset_type=AssetType.IMAGE,
            )
            asset.save()

            content_type = ContentType.objects.get_for_model(parent)
            relation = AssetRelation(
                asset=asset,
                content_type=content_type,
                object_id=parent.pk,
                role=role,
                field_name=field_name,
                is_primary=True,
            )
            relation.save()
            return relation

    @staticmethod
    def remove_primary(
        *,
        parent: Any,
        role: str,
        field_name: str,
        actor: Any | None = None,
    ) -> None:
        with AssetAttachmentService._schema_context_for(parent):
            content_type = ContentType.objects.get_for_model(parent)
            relations = AssetRelation.objects.filter(
                content_type=content_type,
                object_id=parent.pk,
                role=role,
                field_name=field_name,
                is_primary=True,
                is_deleted=False,
            )
            for relation in relations:
                relation.delete()
