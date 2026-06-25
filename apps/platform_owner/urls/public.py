from django.urls import path

from apps.platform_owner.views import (
    PlatformAuthenticationView,
    PlatformChangePasswordView,
    PlatformFeatureDetailView,
    PlatformFeatureListCreateView,
    PlatformInvitationAcceptView,
    PlatformInvitationListCreateView,
    PlatformInvitationRevokeView,
    PlatformInvitationValidateView,
    PlatformMeView,
    PlatformPasswordResetConfirmView,
    PlatformPasswordResetRequestView,
    PlatformPermissionsView,
    PlatformSettingsView,
    PlatformTenantFeatureOverrideView,
    PlatformTenantListView,
    PlatformTokenRefreshView,
    PlatformUserDeactivateView,
    PlatformUserDetailView,
    PlatformUserListView,
    PlatformUserRolesView,
)

app_name = "platform_owner"

urlpatterns = [
    path("auth/login/", PlatformAuthenticationView.as_view(), name="auth-login"),
    path("auth/refresh/", PlatformTokenRefreshView.as_view(), name="auth-refresh"),
    path("me/", PlatformMeView.as_view(), name="me"),
    path("me/permissions/", PlatformPermissionsView.as_view(), name="me-permissions"),
    path(
        "password/change/",
        PlatformChangePasswordView.as_view(),
        name="password-change",
    ),
    path(
        "password/reset/request/",
        PlatformPasswordResetRequestView.as_view(),
        name="password-reset-request",
    ),
    path(
        "password/reset/confirm/",
        PlatformPasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path(
        "invitations/",
        PlatformInvitationListCreateView.as_view(),
        name="invitation-list-create",
    ),
    path(
        "invitations/validate/",
        PlatformInvitationValidateView.as_view(),
        name="invitation-validate",
    ),
    path(
        "invitations/accept/",
        PlatformInvitationAcceptView.as_view(),
        name="invitation-accept",
    ),
    path(
        "invitations/<uuid:invitation_id>/",
        PlatformInvitationRevokeView.as_view(),
        name="invitation-revoke",
    ),
    path("users/", PlatformUserListView.as_view(), name="user-list"),
    path("users/<uuid:user_id>/", PlatformUserDetailView.as_view(), name="user-detail"),
    path(
        "users/<uuid:user_id>/roles/",
        PlatformUserRolesView.as_view(),
        name="user-roles",
    ),
    path(
        "users/<uuid:user_id>/deactivate/",
        PlatformUserDeactivateView.as_view(),
        name="user-deactivate",
    ),
    path("settings/", PlatformSettingsView.as_view(), name="settings"),
    path("features/", PlatformFeatureListCreateView.as_view(), name="feature-list"),
    path(
        "features/<slug:feature_key>/",
        PlatformFeatureDetailView.as_view(),
        name="feature-detail",
    ),
    path("tenants/", PlatformTenantListView.as_view(), name="tenant-list"),
    path(
        "tenants/<uuid:tenant_id>/features/",
        PlatformTenantFeatureOverrideView.as_view(),
        name="tenant-feature-overrides",
    ),
]
