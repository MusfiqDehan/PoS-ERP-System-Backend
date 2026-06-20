from django.urls import path

from apps.tenancy.views import ChangePasswordView, CurrentTenantFeaturesView, MeView
from apps.tenancy.views.users import TenantUserListView

app_name = "tenancy"

urlpatterns = [
    path("me/", MeView.as_view(), name="tenant-me"),
    path(
        "me/features/",
        CurrentTenantFeaturesView.as_view(),
        name="current-tenant-features",
    ),
    path("password/change/", ChangePasswordView.as_view(), name="password-change"),
    path("users/", TenantUserListView.as_view(), name="tenant-user-list"),
]
