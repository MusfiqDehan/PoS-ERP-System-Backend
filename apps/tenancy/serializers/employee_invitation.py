from django.utils import timezone
from rest_framework import serializers

from apps.tenancy.models import Invitation


class TenantEmployeeInvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=120)
    role_slug = serializers.SlugField()
    branch_id = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, attrs):
        attrs["email"] = attrs["email"].strip().lower()
        return attrs


class TenantEmployeeInvitationListSerializer(serializers.ModelSerializer):
    role_slug = serializers.SerializerMethodField()
    branch_id = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Invitation
        fields = [
            "id",
            "email",
            "invitee_full_name",
            "role_slug",
            "branch_id",
            "expires_at",
            "status",
            "created_at",
        ]

    def get_role_slug(self, obj):
        return (obj.metadata or {}).get("role_slug", "")

    def get_branch_id(self, obj):
        return (obj.metadata or {}).get("branch_id")

    def get_status(self, obj):
        now = timezone.now()
        if obj.used_at:
            return "used"
        if obj.expires_at <= now:
            return "expired"
        return "pending"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return {
            "id": data["id"],
            "email": data["email"],
            "full_name": data["invitee_full_name"],
            "role_slug": data["role_slug"],
            "branch_id": data["branch_id"],
            "expires_at": data["expires_at"],
            "status": data["status"],
            "created_at": data["created_at"],
        }


class TenantEmployeeInvitationTokenSerializer(serializers.Serializer):
    token = serializers.CharField()


class TenantEmployeeInvitationAcceptSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)
