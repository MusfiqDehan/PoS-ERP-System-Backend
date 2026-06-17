from rest_framework import serializers

from apps.tenancy.services.registration import normalize_subdomain


class TenantAuthSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    subdomain = serializers.CharField(required=False, allow_blank=True)
    domain = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        email = attrs.get("email", "").strip().lower()
        subdomain = normalize_subdomain(attrs.get("subdomain", ""))
        domain = (attrs.get("domain") or "").strip().lower()
        if not domain and not subdomain:
            raise serializers.ValidationError("Provide either domain or subdomain.")
        attrs["email"] = email
        attrs["subdomain"] = subdomain
        attrs["domain"] = domain
        return attrs


class TokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
