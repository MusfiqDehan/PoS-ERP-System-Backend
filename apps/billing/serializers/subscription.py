from django.utils import timezone
from rest_framework import serializers

from apps.billing.models import TenantProductSubscription, TenantSubscriptionInvoice
from apps.billing.services.subscription_billing import activate_tenant_subscription


class TenantProductSubscriptionSerializer(serializers.ModelSerializer):
    software_product_slug = serializers.CharField(
        source="software_product.slug", read_only=True
    )
    software_product_name = serializers.CharField(
        source="software_product.name", read_only=True
    )
    package_slug = serializers.CharField(source="package.slug", read_only=True)
    package_name = serializers.CharField(source="package.name", read_only=True)

    class Meta:
        model = TenantProductSubscription
        fields = [
            "id",
            "software_product_slug",
            "software_product_name",
            "package_slug",
            "package_name",
            "status",
            "billing_cycle",
            "current_period_start",
            "current_period_end",
            "cancelled_at",
        ]


class TenantSubscriptionInvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantSubscriptionInvoice
        fields = [
            "id",
            "software_product_slug",
            "package_slug",
            "tran_id",
            "amount",
            "currency",
            "status",
            "billing_cycle",
            "period_start",
            "period_end",
            "gateway_slug",
            "validated_at",
            "created_at",
        ]


class SubscriptionSummarySerializer(serializers.Serializer):
    subscriptions = TenantProductSubscriptionSerializer(many=True)
    effective_limits = serializers.DictField()
    total_paid = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()
    status = serializers.CharField()
    is_trial = serializers.BooleanField()


class InitiateSubscriptionChangeSerializer(serializers.Serializer):
    package_slug = serializers.SlugField()
    billing_cycle = serializers.ChoiceField(
        choices=["monthly", "yearly"], default="monthly"
    )
    software_product_slug = serializers.SlugField(required=False, allow_blank=True)


class PlatformSubscriptionInvoiceUpdateSerializer(serializers.ModelSerializer):
    reference_note = serializers.CharField(
        required=False, allow_blank=True, write_only=True
    )

    class Meta:
        model = TenantSubscriptionInvoice
        fields = [
            "status",
            "amount",
            "billing_cycle",
            "period_start",
            "period_end",
            "reference_note",
        ]

    def validate(self, attrs):
        instance = self.instance
        if instance is None:
            return attrs

        pending_gateway = (
            instance.status == TenantSubscriptionInvoice.STATUS_PENDING
            and instance.gateway_slug not in ("", "manual")
        )
        if pending_gateway:
            allowed = {"status"}
            blocked = set(attrs.keys()) - allowed
            if blocked:
                raise serializers.ValidationError(
                    "Pending gateway invoices only allow status changes."
                )
            new_status = attrs.get("status", instance.status)
            if new_status not in (
                TenantSubscriptionInvoice.STATUS_CANCELLED,
                TenantSubscriptionInvoice.STATUS_FAILED,
                TenantSubscriptionInvoice.STATUS_PENDING,
            ):
                raise serializers.ValidationError(
                    "Pending gateway invoices may only be set to cancelled or failed."
                )
        return attrs

    def update(self, instance, validated_data):
        reference_note = validated_data.pop("reference_note", None)
        previous_status = instance.status

        if reference_note is not None:
            gateway_response = dict(instance.gateway_response or {})
            gateway_response["reference_note"] = reference_note
            instance.gateway_response = gateway_response

        for field, value in validated_data.items():
            setattr(instance, field, value)

        if (
            instance.status == TenantSubscriptionInvoice.STATUS_SUCCESS
            and not instance.validated_at
        ):
            instance.validated_at = timezone.now()

        instance.save()
        instance.refresh_from_db()

        if (
            instance.status == TenantSubscriptionInvoice.STATUS_SUCCESS
            and previous_status != instance.status
        ):
            activate_tenant_subscription(instance)
        return instance
