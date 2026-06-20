from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.billing.models import PaymentGateway, TenantPaymentGateway
from apps.billing.serializers.gateway import (
    PaymentGatewaySerializer,
    PaymentGatewayWriteSerializer,
    TenantPaymentGatewaySerializer,
    TenantPaymentGatewayWriteSerializer,
)
from apps.tenancy.permissions import IsPlatformFeaturePermission
from shared.responses import success_response
from shared.views import ModelCRUDView


class PaymentGatewayListCreateView(ModelCRUDView):
    queryset = PaymentGateway.objects.all().order_by("sort_order", "name")
    serializer_class = PaymentGatewayWriteSerializer
    permission_classes = [
        IsPlatformFeaturePermission.require("platform.billing", "view")
    ]
    pagination_class = None

    def get_serializer_class(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return PaymentGatewaySerializer
        return PaymentGatewayWriteSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsPlatformFeaturePermission.require("platform.billing", "edit")()]
        return super().get_permissions()

    def get_success_message(self, action: str) -> str:
        return {
            "list": "Payment gateways retrieved.",
            "create": "Payment gateway created.",
        }.get(action, "Operation successful.")


class PaymentGatewayDetailView(APIView):
    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsPlatformFeaturePermission.require("platform.billing", "view")()]
        return [IsPlatformFeaturePermission.require("platform.billing", "edit")()]

    def get(self, request, slug):
        gateway = get_object_or_404(PaymentGateway, slug=slug)
        return success_response(
            data=PaymentGatewaySerializer(gateway).data,
            message="Payment gateway retrieved.",
        )

    def patch(self, request, slug):
        gateway = get_object_or_404(PaymentGateway, slug=slug)
        serializer = PaymentGatewayWriteSerializer(
            gateway, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=PaymentGatewaySerializer(gateway).data,
            message="Payment gateway updated.",
        )

    def delete(self, request, slug):
        gateway = get_object_or_404(PaymentGateway, slug=slug)
        gateway.delete()
        return success_response(data={}, message="Payment gateway deleted.")


class TenantPaymentGatewayView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug=None):
        if slug:
            row = get_object_or_404(TenantPaymentGateway, gateway_slug=slug)
            return success_response(
                data=TenantPaymentGatewaySerializer(row).data,
                message="Gateway configuration retrieved.",
            )
        rows = TenantPaymentGateway.objects.all().order_by("gateway_slug")
        return success_response(
            data=TenantPaymentGatewaySerializer(rows, many=True).data,
            message="Gateway configurations retrieved.",
        )

    def post(self, request, slug=None):
        if not slug:
            return success_response(
                data={},
                message="slug required.",
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = TenantPaymentGatewayWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row, _ = TenantPaymentGateway.objects.update_or_create(
            gateway_slug=slug,
            defaults={
                "credentials": serializer.validated_data.get("credentials", {}),
                "is_sandbox": serializer.validated_data.get("is_sandbox", True),
                "is_active": serializer.validated_data.get("is_active", True),
            },
        )
        return success_response(
            data=TenantPaymentGatewaySerializer(row).data,
            message="Gateway configuration saved.",
            http_status=status.HTTP_201_CREATED,
        )

    def delete(self, request, slug=None):
        row = get_object_or_404(TenantPaymentGateway, gateway_slug=slug)
        row.delete()
        return success_response(data={}, message="Gateway configuration removed.")
