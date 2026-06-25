from rest_framework import serializers

from apps.platform_owner.services.users import PlatformUserService
from apps.tenancy.models import User


class PlatformUserListSerializer(serializers.ModelSerializer):
    """Read serializer for platform user list/retrieve via ModelCRUDView."""

    class Meta:
        model = User
        fields = ["id"]

    def to_representation(self, instance):
        return PlatformUserService.serialize_user(instance)


class PlatformUserRolesSerializer(serializers.Serializer):
    role_slugs = serializers.ListField(
        child=serializers.SlugField(),
        allow_empty=False,
    )
