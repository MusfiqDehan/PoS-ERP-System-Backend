from decimal import Decimal

from django.db.models import Sum
from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.billing.models import TenantProductSubscription, TenantSubscriptionInvoice
from apps.billing.serializers.subscription import (
    InitiateSubscriptionChangeSerializer,
    TenantProductSubscriptionSerializer,
)
from apps.billing.services.limits_sync import compute_effective_limits
from apps.billing.services.subscription_billing import (
    activate_tenant_subscription,
    initiate_for_tenant,
)
from apps.tenancy.models import PlatformSettings, Tenant
from shared.responses import error_response, success_response
from shared.responses.error_codes import ErrorCode
from shared.tenancy.helpers import is_tenant_admin_user


class SubscriptionSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_tenant_admin_user(request.user):
            return error_response(
                message="Only tenant administrators can view subscription summary.",
                error_code=str(ErrorCode.PERMISSION_DENIED),
                http_status=status.HTTP_403_FORBIDDEN,
            )
        tenant = getattr(request, "tenant", None)
        if tenant is None:
            return error_response(
                message="Tenant context not found.",
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        with schema_context(get_public_schema_name()):
            live = Tenant.objects.filter(pk=tenant.pk).first()
            if live is None:
                return error_response(
                    message="Tenant not found.",
                    error_code=str(ErrorCode.TENANT_NOT_FOUND),
                    http_status=status.HTTP_404_NOT_FOUND,
                )
            ps = PlatformSettings.objects.first()
            currency = ps.default_currency if ps else "USD"
            subscriptions = TenantProductSubscription.objects.filter(
                tenant=live
            ).select_related("package", "software_product")
            total_paid = TenantSubscriptionInvoice.objects.filter(
                tenant=live,
                status=TenantSubscriptionInvoice.STATUS_SUCCESS,
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
            limits = compute_effective_limits(live)
            payload = {
                "subscriptions": TenantProductSubscriptionSerializer(
                    subscriptions, many=True
                ).data,
                "effective_limits": {
                    "max_branches": limits.max_branches,
                    "max_users": limits.max_users,
                    "max_custom_roles": limits.max_custom_roles,
                    "max_admins": limits.max_admins,
                    "max_staff": limits.max_staff,
                    "per_role_limits": limits.per_role_limits,
                    "feature_keys": sorted(limits.feature_keys),
                },
                "total_paid": total_paid,
                "currency": currency,
                "status": live.status,
                "is_trial": live.is_trial,
            }
        return success_response(data=payload, message="Subscription summary retrieved.")


class InitiateSubscriptionChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not is_tenant_admin_user(request.user):
            return error_response(
                message="Only tenant administrators can change subscription plans.",
                error_code=str(ErrorCode.PERMISSION_DENIED),
                http_status=status.HTTP_403_FORBIDDEN,
            )
        tenant = getattr(request, "tenant", None)
        if tenant is None:
            return error_response(
                message="Tenant context not found.",
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = InitiateSubscriptionChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            gateway_url, tran_id, invoice = initiate_for_tenant(
                tenant=tenant,
                package_slug=data["package_slug"],
                billing_cycle=data["billing_cycle"],
                request=request,
                software_product_slug=data.get("software_product_slug") or None,
            )
        except ValueError as exc:
            return error_response(
                message=str(exc),
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        except RuntimeError as exc:
            return error_response(
                message=str(exc),
                error_code=str(ErrorCode.PAYMENT_FAILED),
                http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return success_response(
            data={
                "gateway_url": gateway_url,
                "tran_id": tran_id,
                "invoice_id": str(invoice.id),
                "status": invoice.status,
            },
            message="Subscription change initiated.",
            http_status=status.HTTP_201_CREATED,
        )


class _SubscriptionCallbackView(APIView):
    permission_classes = [AllowAny]
    final_status = TenantSubscriptionInvoice.STATUS_FAILED

    def _process(self, request, tran_id: str | None = None):
        tran_id = (
            tran_id
            or request.data.get("tran_id")
            or request.query_params.get("tran_id")
        )
        if not tran_id:
            return error_response(
                message="tran_id is required.",
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        with schema_context(get_public_schema_name()):
            invoice = TenantSubscriptionInvoice.objects.filter(tran_id=tran_id).first()
            if invoice is None:
                return error_response(
                    message="Invoice not found.",
                    error_code=str(ErrorCode.NOT_FOUND),
                    http_status=status.HTTP_404_NOT_FOUND,
                )
            if invoice.status == TenantSubscriptionInvoice.STATUS_SUCCESS:
                return success_response(
                    data={"tran_id": tran_id, "status": invoice.status},
                    message="Already processed.",
                )
            invoice.status = self.final_status
            invoice.save(update_fields=["status", "updated_at"])
            if self.final_status == TenantSubscriptionInvoice.STATUS_SUCCESS:
                activate_tenant_subscription(invoice)
        return success_response(
            data={"tran_id": tran_id, "status": self.final_status},
            message="Payment callback processed.",
        )


class SubscriptionIPNView(_SubscriptionCallbackView):
    def post(self, request):
        tran_id = request.data.get("tran_id") or request.POST.get("tran_id")
        val_id = request.data.get("val_id") or request.POST.get("val_id")
        status_text = (
            request.data.get("status") or request.POST.get("status") or ""
        ).upper()

        if status_text == "VALID" and val_id:
            self.final_status = TenantSubscriptionInvoice.STATUS_SUCCESS
        elif status_text in {"FAILED", "CANCELLED"}:
            self.final_status = TenantSubscriptionInvoice.STATUS_FAILED
        else:
            self.final_status = TenantSubscriptionInvoice.STATUS_PENDING
        return self._process(request, tran_id=tran_id)


class SubscriptionSuccessView(_SubscriptionCallbackView):
    final_status = TenantSubscriptionInvoice.STATUS_SUCCESS

    def get(self, request):
        return self._process(request)


class SubscriptionFailView(_SubscriptionCallbackView):
    final_status = TenantSubscriptionInvoice.STATUS_FAILED

    def get(self, request):
        return self._process(request)


class SubscriptionCancelView(_SubscriptionCallbackView):
    final_status = TenantSubscriptionInvoice.STATUS_CANCELLED

    def get(self, request):
        return self._process(request)
