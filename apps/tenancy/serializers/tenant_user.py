"""Tenant-scoped user list serializers."""

from rest_framework import serializers

from apps.tenancy.models import User
from shared.services.asset_attachment import serialize_asset_summary


class TenantUserListSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "phone",
            "full_name",
            "profile_picture",
            "is_active",
            "email_verified",
            "last_login",
            "created_at",
        ]
        read_only_fields = fields

    def get_profile_picture(self, obj):
        assets = self.context.get("profile_picture_assets")
        if assets is not None:
            return serialize_asset_summary(assets.get(obj.id))
        return serialize_asset_summary(obj.get_profile_picture_asset())
