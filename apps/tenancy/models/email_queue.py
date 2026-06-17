from django.db import models

from shared.models import BaseModel


class EmailQueue(BaseModel):
    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SENT, "Sent"),
        (STATUS_FAILED, "Failed"),
    ]

    PURPOSE_VERIFICATION = "verification"
    PURPOSE_INVITATION = "invitation"
    PURPOSE_PASSWORD_RESET = "password_reset"
    PURPOSE_PLATFORM_INVITE = "platform_invite"

    PURPOSE_CHOICES = [
        (PURPOSE_VERIFICATION, "Verification"),
        (PURPOSE_INVITATION, "Invitation"),
        (PURPOSE_PASSWORD_RESET, "Password Reset"),
        (PURPOSE_PLATFORM_INVITE, "Platform Invitation"),
    ]

    tenant = models.ForeignKey(
        "tenancy.Tenant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emails",
    )
    to_email = models.EmailField()
    subject = models.CharField(max_length=255)
    html_body = models.TextField(blank=True, default="")
    text_body = models.TextField(blank=True, default="")
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    attempts = models.PositiveIntegerField(default=0)
    provider_message_id = models.CharField(max_length=255, blank=True, default="")
    last_error = models.TextField(blank=True, default="")
    context = models.JSONField(default=dict, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["status", "created_at"], name="idx_email_status_created"
            ),
        ]
