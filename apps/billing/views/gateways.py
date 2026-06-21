from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.billing.models import PaymentGateway, TenantPaymentGateway
from apps.billing.openapi import (
    PLATFORM_BILLING_TAG,
    TENANT_BILLING_TAG,
    document_crud_view,
    envelope_responses,
)
from apps.billing.serializers.gateway import (
    PaymentGatewaySerializer,
    PaymentGatewayWriteSerializer,
    TenantPaymentGatewaySerializer,
    TenantPaymentGatewayWriteSerializer,
)
from apps.tenancy.permissions import IsPlatformFeaturePermission
from shared.responses import success_response
from shared.views import ModelCRUDView


@document_crud_view(
    tags=[PLATFORM_BILLING_TAG],
    operations={
        "GET": {
            "summary": "List payment gateways (platform admin)",
            "description": (
                "Lists configured payment gateways for the platform. Requires "
                "platform.billing view permission."
            ),
        },
        "POST": {
            "summary": "Create payment gateway (platform admin)",
            "description": (
                "Creates a payment gateway definition. Requires platform.billing edit "
                "permission."
            ),
        },
    },
)
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


@extend_schema(
    methods=["GET"],
    tags=[PLATFORM_BILLING_TAG],
    summary="Retrieve payment gateway (platform admin)",
    description=(
        "Returns a payment gateway by slug. Requires platform.billing view permission."
    ),
    responses=envelope_responses(
        (status.HTTP_200_OK, "Payment gateway envelope."),
        (status.HTTP_404_NOT_FOUND, "Gateway not found."),
    ),
)
@extend_schema(
    methods=["PATCH"],
    tags=[PLATFORM_BILLING_TAG],
    summary="Update payment gateway (platform admin)",
    description=(
        "Partially updates a payment gateway by slug. Requires platform.billing edit "
        "permission."
    ),
    request=PaymentGatewayWriteSerializer,
    responses=envelope_responses(
        (status.HTTP_200_OK, "Updated payment gateway envelope."),
        (status.HTTP_400_BAD_REQUEST, "Validation error."),
        (status.HTTP_404_NOT_FOUND, "Gateway not found."),
    ),
)
@extend_schema(
    methods=["DELETE"],
    tags=[PLATFORM_BILLING_TAG],
    summary="Delete payment gateway (platform admin)",
    description=(
        "Deletes a payment gateway by slug. Requires platform.billing edit permission."
    ),
    responses=envelope_responses(
        (status.HTTP_200_OK, "Gateway deleted envelope."),
        (status.HTTP_404_NOT_FOUND, "Gateway not found."),
    ),
)
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


@extend_schema(
    methods=["GET"],
    tags=[TENANT_BILLING_TAG],
    summary="List or retrieve tenant payment gateway configuration",
    description=(
        "Lists all tenant gateway configurations or returns one configuration when slug "
        "is provided. Requires authentication."
    ),
    responses=envelope_responses(
        (status.HTTP_200_OK, "Gateway configuration envelope."),
        (status.HTTP_404_NOT_FOUND, "Gateway configuration not found."),
    ),
)
@extend_schema(
    methods=["POST"],
    tags=[TENANT_BILLING_TAG],
    summary="Create or update tenant payment gateway configuration",
    description=(
        "Creates or updates tenant-scoped gateway credentials for the slug provided in "
        "the URL. Requires authentication."
    ),
    request=TenantPaymentGatewayWriteSerializer,
    responses=envelope_responses(
        (status.HTTP_201_CREATED, "Gateway configuration saved envelope."),
        (status.HTTP_400_BAD_REQUEST, "Validation error."),
    ),
)
@extend_schema(
    methods=["DELETE"],
    tags=[TENANT_BILLING_TAG],
    summary="Delete tenant payment gateway configuration",
    description=(
        "Removes tenant-scoped gateway credentials for the slug provided in the URL. "
        "Requires authentication."
    ),
    responses=envelope_responses(
        (status.HTTP_200_OK, "Gateway configuration removed envelope."),
        (status.HTTP_404_NOT_FOUND, "Gateway configuration not found."),
    ),
)
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
