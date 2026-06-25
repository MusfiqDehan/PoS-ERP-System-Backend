from django.urls import path

from apps.branch.views.branches import (
    BranchDetailView,
    BranchListCreateView,
    BranchManagerAssignView,
    BranchSummaryView,
    PublicBranchListView,
    PublicBranchMinimalListView,
)

app_name = "branch"

urlpatterns = [
    path("", BranchListCreateView.as_view(), name="branch-list"),
    path("summary/", BranchSummaryView.as_view(), name="branch-summary"),
    path("public/", PublicBranchListView.as_view(), name="branch-public-list"),
    path(
        "public/minimal/",
        PublicBranchMinimalListView.as_view(),
        name="branch-public-minimal",
    ),
    path("<uuid:pk>/", BranchDetailView.as_view(), name="branch-detail"),
    path(
        "<uuid:pk>/assign-manager/",
        BranchManagerAssignView.as_view(),
        name="branch-assign-manager",
    ),
]
