from rest_framework import serializers

from apps.tenancy.models import User
from apps.tenancy.services.users import TenantUserService


class TenantUserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id"]

    def to_representation(self, instance):
        return TenantUserService.serialize_user(instance)


class TenantUserRoleAssignmentSerializer(serializers.Serializer):
    role_slug = serializers.SlugField()
    branch_id = serializers.UUIDField(required=False, allow_null=True)


class TenantUserRolesSerializer(serializers.Serializer):
    assignments = serializers.ListField(
        child=TenantUserRoleAssignmentSerializer(),
        allow_empty=False,
    )
