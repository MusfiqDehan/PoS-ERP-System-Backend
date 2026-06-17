from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from apps.tenancy.models import TenantAuditLog


class TenantAuditService:
    @staticmethod
    def log(
        *,
        action: str,
        request=None,
        tenant=None,
        target_type: str = "",
        target_id: str = "",
        metadata: dict | None = None,
        actor_email: str = "",
        actor_id=None,
    ) -> TenantAuditLog:
        if request is not None and request.user.is_authenticated:
            actor_email = actor_email or getattr(request.user, "email", "") or ""
            actor_id = actor_id or getattr(request.user, "id", None)

        return TenantAuditLog.objects.create(
            tenant=tenant,
            actor_email=actor_email,
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id or ""),
            ip_address=request.META.get("REMOTE_ADDR") if request else None,
            user_agent=(request.META.get("HTTP_USER_AGENT", "") if request else ""),
            metadata=TenantAuditService._json_safe(metadata or {}),
        )

    @staticmethod
    def _json_safe(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                str(key): TenantAuditService._json_safe(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple, set)):
            return [TenantAuditService._json_safe(item) for item in value]
        if isinstance(value, (datetime, date, time)):
            return value.isoformat()
        if isinstance(value, timedelta):
            return value.total_seconds()
        return value
