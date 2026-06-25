"""Domain model base classes."""

from shared.models.base import BaseModel, SoftDeleteManager, generate_uuid7
from shared.models.media_upload import (
    Asset,
    AssetRelation,
    AssetRelationRole,
    AssetType,
    asset_upload_to,
    infer_asset_type,
)
from shared.models.mixins import UUIDPrimaryKeyMixin

__all__ = [
    "Asset",
    "AssetRelation",
    "AssetRelationRole",
    "AssetType",
    "BaseModel",
    "SoftDeleteManager",
    "UUIDPrimaryKeyMixin",
    "asset_upload_to",
    "generate_uuid7",
    "infer_asset_type",
]
