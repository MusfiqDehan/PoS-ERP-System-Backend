"""Shared inventory helpers."""

from __future__ import annotations

import uuid


def generate_ref_number(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"
