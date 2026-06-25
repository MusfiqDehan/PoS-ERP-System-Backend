"""URL configuration for tenant schemas."""

from django.contrib import admin
from django.urls import include, path

from config.dev_urls import dev_tooling_urlpatterns
from config.health import readiness_health, tenant_health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/tenant/", tenant_health, name="tenant-health"),
    path("api/v1/health/ready/", readiness_health, name="readiness-health"),
    path(
        "api/v1/tenancy/",
        include(("apps.tenancy.urls.tenant", "tenancy"), namespace="tenancy-tenant"),
    ),
    path("api/v1/access/", include(("apps.access.urls", "access"), namespace="access")),
    path(
        "api/v1/billing/",
        include(("apps.billing.urls.tenant", "billing"), namespace="billing-tenant"),
    ),
    path(
        "api/v1/branches/",
        include(("apps.branch.urls.tenant", "branch"), namespace="branch"),
    ),
]

urlpatterns += dev_tooling_urlpatterns()
