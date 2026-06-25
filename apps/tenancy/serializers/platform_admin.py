from django.db.utils import DatabaseError
from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework import serializers

from apps.access.models import UserRole
from apps.tenancy.models import Tenant, User


class TenantListSerializer(serializers.ModelSerializer):
    domains = serializers.SerializerMethodField()
    admins = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = [
            "id",
            "name",
            "schema_name",
            "slug",
            "code",
            "owner_email",
            "billing_email",
            "plan",
            "status",
            "is_enabled",
            "timezone",
            "locale",
            "currency",
            "custom_domain_enabled",
            "max_users",
            "max_branches",
            "max_staff_per_branch",
            "created_at",
            "domains",
            "admins",
        ]

    def get_domains(self, obj):
        return list(obj.domains.values_list("domain", flat=True))

    def get_admins(self, obj):
        if obj.schema_name == get_public_schema_name():
            return []
        try:
            with schema_context(obj.schema_name):
                admin_ids = UserRole.objects.filter(role__slug="admin").values_list(
                    "user_id", flat=True
                )
                admins = User.objects.filter(id__in=admin_ids).order_by("email", "id")
                return [
                    {
                        "id": str(u.id),
                        "email": u.email,
                        "full_name": u.full_name,
                        "is_active": u.is_active,
                    }
                    for u in admins
                ]
        except DatabaseError:
            return []


class TenantUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = [
            "name",
            "owner_email",
            "billing_email",
            "plan",
            "status",
            "is_enabled",
            "timezone",
            "locale",
            "currency",
            "custom_domain_enabled",
            "max_users",
            "max_branches",
            "max_staff_per_branch",
            "features",
            "metadata",
        ]
