"""Tenant branding serializers."""

from rest_framework import serializers

from apps.tenancy.models import Tenant
from shared.services.asset_attachment import serialize_asset_summary


class TenantBrandingSerializer(serializers.ModelSerializer):
    company_logo = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = ["id", "name", "slug", "company_logo"]
        read_only_fields = fields

    def get_company_logo(self, obj):
        return serialize_asset_summary(obj.get_company_logo_asset())
