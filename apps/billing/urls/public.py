from django.urls import path

from apps.billing.views.catalog import (
    PackageDetailView,
    PackageFeaturesView,
    PackageListCreateView,
    SoftwareProductDetailView,
    SoftwareProductListCreateView,
)
from apps.billing.views.public_catalog import PublicPackageListView
from apps.billing.views.gateways import (
    PaymentGatewayDetailView,
    PaymentGatewayListCreateView,
)
from apps.billing.views.invoices import (
    PlatformSubscriptionInvoiceDetailView,
    PlatformSubscriptionInvoiceListView,
    PlatformSubscriptionInvoicePdfView,
)
from apps.billing.views.subscriptions import (
    InitiateSubscriptionChangeView,
    SubscriptionCancelView,
    SubscriptionFailView,
    SubscriptionIPNView,
    SubscriptionSuccessView,
    SubscriptionSummaryView,
)

app_name = "billing"

urlpatterns = [
    path(
        "public/packages/",
        PublicPackageListView.as_view(),
        name="public-package-list",
    ),
    path("products/", SoftwareProductListCreateView.as_view(), name="product-list"),
    path(
        "products/<uuid:pk>/",
        SoftwareProductDetailView.as_view(),
        name="product-detail",
    ),
    path("packages/", PackageListCreateView.as_view(), name="package-list"),
    path("packages/<uuid:pk>/", PackageDetailView.as_view(), name="package-detail"),
    path(
        "packages/<uuid:pk>/features/",
        PackageFeaturesView.as_view(),
        name="package-features",
    ),
    path("gateways/", PaymentGatewayListCreateView.as_view(), name="gateway-list"),
    path(
        "gateways/<slug:slug>/",
        PaymentGatewayDetailView.as_view(),
        name="gateway-detail",
    ),
    path(
        "subscription/summary/",
        SubscriptionSummaryView.as_view(),
        name="subscription-summary",
    ),
    path(
        "subscription/initiate-change/",
        InitiateSubscriptionChangeView.as_view(),
        name="subscription-initiate-change",
    ),
    path("subscription/ipn/", SubscriptionIPNView.as_view(), name="subscription-ipn"),
    path(
        "subscription/success/",
        SubscriptionSuccessView.as_view(),
        name="subscription-success",
    ),
    path(
        "subscription/fail/", SubscriptionFailView.as_view(), name="subscription-fail"
    ),
    path(
        "subscription/cancel/",
        SubscriptionCancelView.as_view(),
        name="subscription-cancel",
    ),
    path(
        "subscription/invoices/",
        PlatformSubscriptionInvoiceListView.as_view(),
        name="platform-subscription-invoices",
    ),
    path(
        "subscription/invoices/<uuid:pk>/",
        PlatformSubscriptionInvoiceDetailView.as_view(),
        name="platform-subscription-invoice-detail",
    ),
    path(
        "subscription/invoices/<uuid:pk>/pdf/",
        PlatformSubscriptionInvoicePdfView.as_view(),
        name="platform-subscription-invoice-pdf",
    ),
]
