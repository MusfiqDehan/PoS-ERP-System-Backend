"""Subscription invoice list, PDF, and platform admin views."""

from __future__ import annotations

from decimal import Decimal

from django.core.paginator import EmptyPage, Paginator
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_tenants.utils import get_public_schema_name, schema_context
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.billing.models import TenantSubscriptionInvoice
from apps.billing.openapi import PLATFORM_BILLING_TAG, TENANT_BILLING_TAG
from apps.billing.serializers.subscription import (
    PlatformSubscriptionInvoiceUpdateSerializer,
    TenantSubscriptionInvoiceSerializer,
)
from apps.billing.services.invoice_pdf import render_subscription_invoice_pdf
from apps.tenancy.permissions import IsPlatformFeaturePermission
from shared.responses import error_response, list_success_response, success_response
from shared.responses.error_codes import ErrorCode
from shared.tenancy.helpers import is_tenant_admin_user

_PLATFORM_PAYMENT_ORDERING = {
    "created_at": "created_at",
    "-created_at": "-created_at",
    "amount": "amount",
    "-amount": "-amount",
}


def _serialize_platform_invoices(invoices):
    serialized = TenantSubscriptionInvoiceSerializer(invoices, many=True).data
    rows = []
    for invoice, data in zip(invoices, serialized, strict=True):
        row = dict(data)
        row["tenant_name"] = invoice.tenant.name if invoice.tenant_id else ""
        row["tenant_schema"] = invoice.tenant.schema_name if invoice.tenant_id else ""
        rows.append(row)
    return rows


def _filter_platform_invoices(request):
    ordering = (
        request.query_params.get("ordering", "-created_at").strip() or "-created_at"
    )
    if ordering not in _PLATFORM_PAYMENT_ORDERING:
        ordering = "-created_at"

    invoices_qs = TenantSubscriptionInvoice.objects.select_related("tenant").order_by(
        _PLATFORM_PAYMENT_ORDERING[ordering]
    )

    status_filter = request.query_params.get("status", "").strip()
    search = request.query_params.get("search", "").strip()
    gateway_slug = request.query_params.get("gateway_slug", "").strip()
    from_date = request.query_params.get("from_date", "").strip()
    to_date = request.query_params.get("to_date", "").strip()

    if status_filter:
        invoices_qs = invoices_qs.filter(status=status_filter)
    if gateway_slug:
        invoices_qs = invoices_qs.filter(gateway_slug=gateway_slug)
    if search:
        invoices_qs = invoices_qs.filter(
            Q(tenant__name__icontains=search)
            | Q(tenant__schema_name__icontains=search)
            | Q(tran_id__icontains=search)
            | Q(package_slug__icontains=search)
        )
    if from_date:
        invoices_qs = invoices_qs.filter(created_at__date__gte=from_date)
    if to_date:
        invoices_qs = invoices_qs.filter(created_at__date__lte=to_date)
    return invoices_qs


def _platform_subscription_stats():
    qs = TenantSubscriptionInvoice.objects.all()
    count_by_status = dict(
        qs.values("status").annotate(count=Count("id")).values_list("status", "count")
    )
    success_qs = qs.filter(status=TenantSubscriptionInvoice.STATUS_SUCCESS)
    return {
        "total_revenue": success_qs.aggregate(total=Sum("amount"))["total"]
        or Decimal("0"),
        "successful_payments": count_by_status.get(
            TenantSubscriptionInvoice.STATUS_SUCCESS, 0
        ),
        "failed_payments": count_by_status.get(
            TenantSubscriptionInvoice.STATUS_FAILED, 0
        ),
        "pending_payments": count_by_status.get(
            TenantSubscriptionInvoice.STATUS_PENDING, 0
        ),
        "unique_paying_tenants": success_qs.values("tenant_id").distinct().count(),
    }


def _pdf_response(request, invoice, *, invoice_ref: str) -> HttpResponse:
    generated_by = getattr(request.user, "full_name", "") or getattr(
        request.user, "email", "System"
    )
    pdf_bytes = render_subscription_invoice_pdf(invoice, generated_by=generated_by)
    disposition = (
        "attachment" if request.query_params.get("download") == "1" else "inline"
    )
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'{disposition}; filename="subscription-invoice-{invoice_ref}.pdf"'
    )
    return response


@extend_schema(
    tags=[TENANT_BILLING_TAG],
    summary="List tenant subscription invoices (tenant admin)",
    description=(
        "Lists subscription invoices for the current tenant. Only tenant administrators "
        "can access this endpoint."
    ),
    responses={
        status.HTTP_200_OK: OpenApiResponse(description="Invoice list envelope.")
    },
)
class TenantSubscriptionInvoiceListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_tenant_admin_user(request.user):
            return error_response(
                message="Only tenant administrators can view subscription invoices.",
                error_code=str(ErrorCode.PERMISSION_DENIED),
                http_status=status.HTTP_403_FORBIDDEN,
            )
        tenant = getattr(request, "tenant", None)
        if tenant is None:
            return list_success_response(items=[], message="No tenant context.")

        with schema_context(get_public_schema_name()):
            invoices = TenantSubscriptionInvoice.objects.filter(tenant=tenant).order_by(
                "-created_at"
            )
            data = TenantSubscriptionInvoiceSerializer(invoices, many=True).data
        return list_success_response(
            items=data, message="Subscription invoices retrieved."
        )


@extend_schema(
    tags=[TENANT_BILLING_TAG],
    summary="Download tenant subscription invoice PDF",
    description=(
        "Downloads a subscription invoice PDF for the current tenant. Returns binary "
        "application/pdf content. Only tenant administrators can access this endpoint."
    ),
    responses={status.HTTP_200_OK: OpenApiResponse(description="application/pdf")},
)
class TenantSubscriptionInvoicePdfView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not is_tenant_admin_user(request.user):
            return error_response(
                message="Only tenant administrators can download subscription invoices.",
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
            invoice = get_object_or_404(
                TenantSubscriptionInvoice.objects.select_related("tenant"),
                pk=pk,
                tenant=tenant,
            )
            invoice_ref = f"SUB-{str(invoice.id).replace('-', '')[:8].upper()}"
            return _pdf_response(request, invoice, invoice_ref=invoice_ref)


@extend_schema(
    tags=[PLATFORM_BILLING_TAG],
    summary="List subscription invoices across tenants (platform admin)",
    description=(
        "Returns paginated subscription invoices across all tenants with aggregate "
        "payment statistics. Requires platform.billing view permission."
    ),
    responses={
        status.HTTP_200_OK: OpenApiResponse(description="Paginated invoice list.")
    },
)
class PlatformSubscriptionInvoiceListView(APIView):
    permission_classes = [
        IsPlatformFeaturePermission.require("platform.billing", "view")
    ]

    def get(self, request):
        with schema_context(get_public_schema_name()):
            invoices_qs = _filter_platform_invoices(request)
            stats = _platform_subscription_stats()

            try:
                page = max(int(request.query_params.get("page", 1)), 1)
            except (TypeError, ValueError):
                page = 1
            try:
                page_size = min(
                    max(int(request.query_params.get("page_size", 10)), 1), 100
                )
            except (TypeError, ValueError):
                page_size = 10

            paginator = Paginator(invoices_qs, page_size)
            try:
                page_obj = paginator.page(page)
            except EmptyPage:
                page_obj = paginator.page(paginator.num_pages or 1)

            rows = _serialize_platform_invoices(page_obj.object_list)

        return success_response(
            data={
                "stats": stats,
                "items": rows,
                "pagination": {
                    "count": paginator.count,
                    "page": page_obj.number,
                    "page_size": page_size,
                    "total_pages": paginator.num_pages,
                },
            },
            message="Platform subscription invoices retrieved.",
        )


@extend_schema(
    tags=[PLATFORM_BILLING_TAG],
    summary="Update subscription invoice (platform admin)",
    description=(
        "Partially updates a subscription invoice record. Requires platform.billing "
        "edit permission."
    ),
    request=PlatformSubscriptionInvoiceUpdateSerializer,
    responses={status.HTTP_200_OK: OpenApiResponse(description="Updated invoice.")},
)
class PlatformSubscriptionInvoiceDetailView(APIView):
    def get_permissions(self):
        return [IsPlatformFeaturePermission.require("platform.billing", "edit")()]

    def patch(self, request, pk):
        with schema_context(get_public_schema_name()):
            invoice = get_object_or_404(
                TenantSubscriptionInvoice.objects.select_related("tenant"), pk=pk
            )
            serializer = PlatformSubscriptionInvoiceUpdateSerializer(
                invoice,
                data=request.data,
                partial=True,
                context={"actor": request.user},
            )
            serializer.is_valid(raise_exception=True)
            invoice = serializer.save()
            row = dict(TenantSubscriptionInvoiceSerializer(invoice).data)
            row["tenant_name"] = invoice.tenant.name if invoice.tenant_id else ""
            row["tenant_schema"] = (
                invoice.tenant.schema_name if invoice.tenant_id else ""
            )
        return success_response(data=row, message="Subscription invoice updated.")


@extend_schema(
    tags=[PLATFORM_BILLING_TAG],
    summary="Download subscription invoice PDF (platform admin)",
    description=(
        "Downloads a subscription invoice PDF for any tenant. Returns binary "
        "application/pdf content. Requires platform.billing view permission."
    ),
    responses={status.HTTP_200_OK: OpenApiResponse(description="application/pdf")},
)
class PlatformSubscriptionInvoicePdfView(APIView):
    permission_classes = [
        IsPlatformFeaturePermission.require("platform.billing", "view")
    ]

    def get(self, request, pk):
        with schema_context(get_public_schema_name()):
            invoice = get_object_or_404(
                TenantSubscriptionInvoice.objects.select_related("tenant"), pk=pk
            )
            invoice_ref = f"SUB-{str(invoice.id).replace('-', '')[:8].upper()}"
            return _pdf_response(request, invoice, invoice_ref=invoice_ref)
