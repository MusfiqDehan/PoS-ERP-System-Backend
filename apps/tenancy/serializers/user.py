from rest_framework import serializers

from apps.tenancy.models import User


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "phone",
            "full_name",
            "is_staff",
            "is_superuser",
            "email_verified",
            "tenant_id",
            "created_at",
        ]
        read_only_fields = fields
