"""Domain model base classes."""

from shared.models.base import BaseModel, SoftDeleteManager, generate_uuid7
from shared.models.mixins import UUIDPrimaryKeyMixin

__all__ = ["BaseModel", "SoftDeleteManager", "UUIDPrimaryKeyMixin", "generate_uuid7"]
