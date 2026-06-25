from django.urls import path

from apps.tenancy.views import (
    InvitationValidationView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PasswordSetupView,
    TenantAuthenticationView,
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
]
