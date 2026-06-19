from rest_framework import serializers

from apps.billing.models import PaymentGateway, TenantPaymentGateway


class PaymentGatewaySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentGateway
        fields = [
            "id",
            "slug",
            "name",
            "credential_schema",
            "is_enabled_for_tenants",
            "is_default_for_subscriptions",
            "is_sandbox",
            "sort_order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {"platform_credentials": {"write_only": True}}


class PaymentGatewayWriteSerializer(PaymentGatewaySerializer):
    class Meta(PaymentGatewaySerializer.Meta):
        fields = PaymentGatewaySerializer.Meta.fields + ["platform_credentials"]


class TenantPaymentGatewaySerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantPaymentGateway
        fields = [
            "id",
            "gateway_slug",
            "is_sandbox",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TenantPaymentGatewayWriteSerializer(TenantPaymentGatewaySerializer):
    credentials = serializers.JSONField(write_only=True)

    class Meta(TenantPaymentGatewaySerializer.Meta):
        fields = TenantPaymentGatewaySerializer.Meta.fields + ["credentials"]
