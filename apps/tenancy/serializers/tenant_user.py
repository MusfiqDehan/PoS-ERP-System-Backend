"""Tenant-scoped user list serializers."""

from rest_framework import serializers

from apps.tenancy.models import User


class TenantUserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "phone",
            "full_name",
            "is_active",
            "email_verified",
            "last_login",
            "created_at",
        ]
        read_only_fields = fields
