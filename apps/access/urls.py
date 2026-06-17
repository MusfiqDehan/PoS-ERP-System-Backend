from django.urls import path

from apps.access.views import (
    MyPermissionsView,
    RoleDetailView,
    RoleListCreateView,
    RolePermissionsView,
    TenantFeatureCatalogView,
    UserRoleDetailView,
    UserRoleListCreateView,
)

app_name = "access"

urlpatterns = [
    path("me/", MyPermissionsView.as_view(), name="my-permissions"),
    path("features/", TenantFeatureCatalogView.as_view(), name="feature-catalog"),
    path("roles/", RoleListCreateView.as_view(), name="role-list"),
    path("roles/<uuid:pk>/", RoleDetailView.as_view(), name="role-detail"),
    path(
        "roles/<uuid:role_id>/permissions/",
        RolePermissionsView.as_view(),
        name="role-permissions",
    ),
    path("user-roles/", UserRoleListCreateView.as_view(), name="user-role-list"),
    path(
        "user-roles/<uuid:pk>/", UserRoleDetailView.as_view(), name="user-role-detail"
    ),
]
