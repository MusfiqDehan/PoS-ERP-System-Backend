from django.db import models

from shared.models import BaseModel


class TenantAuditLog(BaseModel):
    tenant = models.ForeignKey(
        "tenancy.Tenant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    actor_email = models.EmailField(blank=True, default="")
    actor_id = models.UUIDField(null=True, blank=True)
    action = models.CharField(max_length=120)
    target_type = models.CharField(max_length=80, blank=True, default="")
    target_id = models.CharField(max_length=120, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["action", "created_at"], name="idx_audit_action_created"
            ),
        ]
