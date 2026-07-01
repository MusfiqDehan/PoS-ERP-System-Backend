from django.urls import path

from apps.tenancy.views import (
    ChangePasswordView,
    CurrentTenantFeaturesView,
    MeView,
    ProfilePictureView,
    TenantBrandingView,
    TenantCompanyLogoView,
    TenantEmployeeInvitationListCreateView,
    TenantEmployeeInvitationRevokeView,
    TenantUserDeactivateView,
    TenantUserDetailView,
    TenantUserListView,
    TenantUserRolesView,
)

app_name = "tenancy"

urlpatterns = [
    path("me/", MeView.as_view(), name="tenant-me"),
    path(
        "me/profile-picture/",
        ProfilePictureView.as_view(),
        name="tenant-profile-picture",
    ),
    path(
        "me/features/",
        CurrentTenantFeaturesView.as_view(),
        name="current-tenant-features",
    ),
    path("password/change/", ChangePasswordView.as_view(), name="password-change"),
    path("users/", TenantUserListView.as_view(), name="tenant-user-list"),
    path(
        "users/<uuid:user_id>/",
        TenantUserDetailView.as_view(),
        name="tenant-user-detail",
    ),
    path(
        "users/<uuid:user_id>/roles/",
        TenantUserRolesView.as_view(),
        name="tenant-user-roles",
    ),
    path(
        "users/<uuid:user_id>/deactivate/",
        TenantUserDeactivateView.as_view(),
        name="tenant-user-deactivate",
    ),
    path(
        "invitations/",
        TenantEmployeeInvitationListCreateView.as_view(),
        name="tenant-employee-invitation-list",
    ),
    path(
        "invitations/<uuid:invitation_id>/",
        TenantEmployeeInvitationRevokeView.as_view(),
        name="tenant-employee-invitation-revoke",
    ),
    path(
        "settings/branding/",
        TenantBrandingView.as_view(),
        name="tenant-branding",
    ),
    path(
        "settings/branding/logo/",
        TenantCompanyLogoView.as_view(),
        name="tenant-company-logo",
    ),
]
