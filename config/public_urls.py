"""URL configuration for the PUBLIC (shared) PostgreSQL schema."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from config.dev_urls import dev_tooling_urlpatterns
from config.health import readiness_health, tenant_health
from apps.billing.views.subscriptions import (
    SubscriptionCancelView,
    SubscriptionFailView,
    SubscriptionIPNView,
    SubscriptionSuccessView,
)
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/tenant/", tenant_health, name="tenant-health"),
    path("api/v1/health/ready/", readiness_health, name="readiness-health"),
    path(
        "api/v1/tenancy/",
        include(("apps.tenancy.urls.public", "tenancy"), namespace="tenancy-public"),
    ),
    path(
        "api/v1/platform-owner/",
        include(
            ("apps.platform_owner.urls.public", "platform_owner"),
            namespace="platform-owner-public",
        ),
    ),
    path(
        "api/v1/billing/",
        include(("apps.billing.urls.public", "billing"), namespace="billing-public"),
    ),
    path(
        "api/v1/billing/subscription/success/",
        SubscriptionSuccessView.as_view(),
        name="billing-subscription-success-public",
    ),
    path(
        "api/v1/billing/subscription/fail/",
        SubscriptionFailView.as_view(),
        name="billing-subscription-fail-public",
    ),
    path(
        "api/v1/billing/subscription/cancel/",
        SubscriptionCancelView.as_view(),
        name="billing-subscription-cancel-public",
    ),
    path(
        "api/v1/billing/subscription/ipn/",
        SubscriptionIPNView.as_view(),
        name="billing-subscription-ipn-public",
    ),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/v1/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"
    ),
]

urlpatterns += dev_tooling_urlpatterns()

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
