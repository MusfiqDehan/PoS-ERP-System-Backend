from django.urls import path

from apps.tenancy.views import (
    InvitationValidationView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PasswordSetupView,
    PlatformPermissionsAliasView,
    TenantAdminListView,
    TenantAuthenticationView,
    TenantFeatureOverrideView,
    TenantSelfRegistrationView,
    TokenRefreshView,
)

app_name = "tenancy"

urlpatterns = [
    path("register/", TenantSelfRegistrationView.as_view(), name="tenant-register"),
    path("auth/login/", TenantAuthenticationView.as_view(), name="tenant-auth-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="tenant-auth-refresh"),
    path(
        "tokens/validate/",
        InvitationValidationView.as_view(),
        name="tenant-token-validate",
    ),
    path("password/setup/", PasswordSetupView.as_view(), name="tenant-password-setup"),
    path(
        "password/reset/request/",
        PasswordResetRequestView.as_view(),
        name="tenant-password-reset-request",
    ),
    path(
        "password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="tenant-password-reset-confirm",
    ),
    path("admin/tenants/", TenantAdminListView.as_view(), name="tenant-admin-list"),
    path(
        "admin/me/platform-permissions/",
        PlatformPermissionsAliasView.as_view(),
        name="platform-permissions-alias",
    ),
    path(
        "admin/tenants/<uuid:tenant_id>/features/",
        TenantFeatureOverrideView.as_view(),
        name="tenant-feature-overrides",
    ),
]
