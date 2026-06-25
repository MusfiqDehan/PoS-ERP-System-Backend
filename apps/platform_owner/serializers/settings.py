from rest_framework import serializers

from apps.tenancy.models import PlatformSettings


class PlatformSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformSettings
        fields = [
            "id",
            "default_timezone",
            "default_language",
            "default_currency",
            "enable_custom_domains",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]

    def validate_default_timezone(self, value):
        import zoneinfo

        try:
            zoneinfo.ZoneInfo(value)
        except Exception as exc:
            raise serializers.ValidationError("Invalid IANA timezone.") from exc
        return value
