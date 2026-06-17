from django.db import models

from shared.models import UUIDPrimaryKeyMixin


class PlatformSettings(UUIDPrimaryKeyMixin, models.Model):
    """Platform-wide singleton configuration (pk managed explicitly as first row)."""

    default_timezone = models.CharField(
        max_length=50,
        default="Asia/Dhaka",
        help_text="Default IANA timezone for tenants without their own setting.",
    )
    default_language = models.CharField(
        max_length=10,
        default="en",
        help_text="Default ISO 639-1 language code.",
    )
    default_currency = models.CharField(
        max_length=10,
        default="USD",
        help_text="Default currency code.",
    )
    enable_custom_domains = models.BooleanField(
        default=False,
        help_text="Global master switch for tenant custom domains.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Platform Settings"
        verbose_name_plural = "Platform Settings"

    def __str__(self) -> str:
        return f"Platform Settings (tz={self.default_timezone}, lang={self.default_language})"

    @classmethod
    def get_solo(cls):
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create()
        return obj
