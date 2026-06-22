from django.urls import path

from apps.billing.views.gateways import TenantPaymentGatewayView
from apps.billing.views.invoices import (
    TenantSubscriptionInvoiceListView,
    TenantSubscriptionInvoicePdfView,
)
from apps.billing.views.subscriptions import (
    InitiateSubscriptionChangeView,
    SubscriptionSummaryView,
)

app_name = "billing"

urlpatterns = [
    path(
        "subscription/summary/",
        SubscriptionSummaryView.as_view(),
        name="tenant-subscription-summary",
    ),
    path(
        "subscription/initiate-change/",
        InitiateSubscriptionChangeView.as_view(),
        name="tenant-subscription-initiate-change",
    ),
    path(
        "subscription/invoices/",
        TenantSubscriptionInvoiceListView.as_view(),
        name="tenant-subscription-invoices",
    ),
    path(
        "subscription/invoices/<uuid:pk>/pdf/",
        TenantSubscriptionInvoicePdfView.as_view(),
        name="tenant-subscription-invoice-pdf",
    ),
    path(
        "payments/gateways/",
        TenantPaymentGatewayView.as_view(),
        name="tenant-gateway-list",
    ),
    path(
        "payments/gateways/<slug:slug>/",
        TenantPaymentGatewayView.as_view(),
        name="tenant-gateway-detail",
    ),
]
