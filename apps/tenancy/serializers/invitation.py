from rest_framework import serializers


class InvitationTokenSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=255)


class PasswordSetupSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=255)
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError("Passwords do not match.")
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    subdomain = serializers.CharField(required=False, allow_blank=True)
    domain = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        from apps.tenancy.services.registration import normalize_subdomain

        attrs["email"] = attrs.get("email", "").strip().lower()
        attrs["subdomain"] = normalize_subdomain(attrs.get("subdomain", ""))
        attrs["domain"] = (attrs.get("domain") or "").strip().lower()
        if not attrs["domain"] and not attrs["subdomain"]:
            raise serializers.ValidationError("Provide either domain or subdomain.")
        return attrs
