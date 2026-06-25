from rest_framework import serializers


class PlatformAuthSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        attrs["email"] = attrs["email"].strip().lower()
        return attrs


class PlatformTokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class PlatformPasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class PlatformPasswordConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)
