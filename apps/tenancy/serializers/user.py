from rest_framework import serializers

from apps.tenancy.models import PlatformUserRole, User
from shared.services.asset_attachment import serialize_asset_summary


class UserProfileSerializer(serializers.ModelSerializer):
    platform_roles = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "phone",
            "full_name",
            "platform_roles",
            "profile_picture",
            "email_verified",
            "tenant_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_platform_roles(self, obj):
        return list(
            PlatformUserRole.objects.filter(user=obj).values_list(
                "role__slug", flat=True
            )
        )

    def get_profile_picture(self, obj):
        return serialize_asset_summary(obj.get_profile_picture_asset())
