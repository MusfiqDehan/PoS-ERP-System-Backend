import hashlib
import secrets
from datetime import timedelta

from django.db import models
from django.utils import timezone

from shared.models import BaseModel


class Invitation(BaseModel):
    TOKEN_TYPE_VERIFICATION = "verification"
    TOKEN_TYPE_INVITATION = "invitation"
    TOKEN_TYPE_PASSWORD_RESET = "password_reset"
    TOKEN_TYPE_PLATFORM_INVITE = "platform_invite"
    TOKEN_TYPE_EMPLOYEE_INVITE = "employee_invite"

    TOKEN_TYPE_CHOICES = [
        (TOKEN_TYPE_VERIFICATION, "Verification"),
        (TOKEN_TYPE_INVITATION, "Invitation"),
        (TOKEN_TYPE_PASSWORD_RESET, "Password Reset"),
        (TOKEN_TYPE_PLATFORM_INVITE, "Platform Team Invitation"),
        (TOKEN_TYPE_EMPLOYEE_INVITE, "Tenant Employee Invitation"),
    ]

    token_type = models.CharField(max_length=20, choices=TOKEN_TYPE_CHOICES)
    tenant = models.ForeignKey(
        "tenancy.Tenant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="invitations",
    )
    email = models.EmailField()
    invitee_full_name = models.CharField(max_length=120, blank=True, default="")
    subdomain = models.CharField(max_length=100)
    company_name = models.CharField(max_length=255)
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    invited_by_email = models.EmailField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    platform_role = models.ForeignKey(
        "tenancy.PlatformRole",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invitations",
    )

    class Meta:
        indexes = [
            models.Index(fields=["token_type", "email"], name="idx_invite_type_email"),
            models.Index(fields=["expires_at"], name="idx_invite_expires"),
        ]

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    @property
    def is_usable(self) -> bool:
        return self.used_at is None and not self.is_expired

    @classmethod
    def issue_token(
        cls,
        *,
        token_type: str,
        email: str,
        subdomain: str,
        company_name: str,
        tenant=None,
        invitee_full_name: str = "",
        invited_by_email: str = "",
        ttl_minutes: int = 60,
        metadata=None,
        platform_role=None,
    ):
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        invitation = cls.objects.create(
            token_type=token_type,
            tenant=tenant,
            email=email,
            invitee_full_name=invitee_full_name or "",
            subdomain=subdomain,
            company_name=company_name,
            token_hash=token_hash,
            expires_at=timezone.now() + timedelta(minutes=ttl_minutes),
            invited_by_email=invited_by_email,
            metadata=metadata or {},
            platform_role=platform_role,
        )
        return raw_token, invitation

    @classmethod
    def from_raw_token(cls, raw_token: str, *, for_update: bool = False):
        token_hash = hashlib.sha256((raw_token or "").encode("utf-8")).hexdigest()
        queryset = cls.objects
        if for_update:
            queryset = queryset.select_for_update()
        return queryset.filter(token_hash=token_hash).first()
