from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.views import APIView

from apps.billing.models import Package, PackageFeature, SoftwareProduct
from apps.billing.openapi import (
    PLATFORM_BILLING_TAG,
    document_crud_view,
    envelope_responses,
)
from apps.billing.serializers import PackageFeatureBulkSerializer, PackageSerializer
from apps.billing.serializers.product import SoftwareProductSerializer
from apps.tenancy.permissions import IsPlatformFeaturePermission
from shared.responses import success_response
from shared.views import ModelCRUDView


@document_crud_view(
    tags=[PLATFORM_BILLING_TAG],
    operations={
        "GET": {
            "summary": "List software products (platform admin)",
            "description": (
                "Lists software products in the platform billing catalog. Requires "
                "platform.billing view permission."
            ),
        },
        "POST": {
            "summary": "Create software product (platform admin)",
            "description": (
                "Creates a software product in the platform billing catalog. Requires "
                "platform.billing edit permission."
            ),
        },
    },
)
class SoftwareProductListCreateView(ModelCRUDView):
    queryset = SoftwareProduct.objects.select_related("category").order_by(
        "sort_order", "name"
    )
    serializer_class = SoftwareProductSerializer
    permission_classes = [
        IsPlatformFeaturePermission.require("platform.billing", "view")
    ]
    pagination_class = None

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsPlatformFeaturePermission.require("platform.billing", "edit")()]
        return super().get_permissions()

    def get_success_message(self, action: str) -> str:
        return {
            "list": "Software products retrieved successfully.",
            "create": "Software product created successfully.",
            "retrieve": "Software product retrieved successfully.",
            "update": "Software product updated successfully.",
            "destroy": "Software product deleted successfully.",
        }.get(action, "Operation successful.")


@document_crud_view(
    tags=[PLATFORM_BILLING_TAG],
    operations={
        "GET": {
            "summary": "Retrieve software product (platform admin)",
            "description": (
                "Returns a single software product by ID. Requires platform.billing view "
                "permission."
            ),
        },
        "PUT": {
            "summary": "Replace software product (platform admin)",
            "description": (
                "Replaces a software product by ID. Requires platform.billing edit "
                "permission."
            ),
        },
        "PATCH": {
            "summary": "Update software product (platform admin)",
            "description": (
                "Partially updates a software product by ID. Requires platform.billing "
                "edit permission."
            ),
        },
        "DELETE": {
            "summary": "Delete software product (platform admin)",
            "description": (
                "Deletes a software product by ID. Requires platform.billing edit "
                "permission."
            ),
        },
    },
)
class SoftwareProductDetailView(SoftwareProductListCreateView):
    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsPlatformFeaturePermission.require("platform.billing", "view")()]
        return [IsPlatformFeaturePermission.require("platform.billing", "edit")()]


@document_crud_view(
    tags=[PLATFORM_BILLING_TAG],
    operations={
        "GET": {
            "summary": "List packages (platform admin)",
            "description": (
                "Lists subscription packages in the platform catalog. Requires "
                "platform.packages view permission."
            ),
        },
        "POST": {
            "summary": "Create package (platform admin)",
            "description": (
                "Creates a subscription package. Requires platform.packages edit "
                "permission."
            ),
        },
    },
)
class PackageListCreateView(ModelCRUDView):
    queryset = (
        Package.objects.select_related("software_product")
        .prefetch_related("package_features__feature", "role_limits")
        .order_by("sort_order", "name")
    )
    serializer_class = PackageSerializer
    permission_classes = [
        IsPlatformFeaturePermission.require("platform.packages", "view")
    ]
    pagination_class = None

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsPlatformFeaturePermission.require("platform.packages", "edit")()]
        return super().get_permissions()

    def get_success_message(self, action: str) -> str:
        return {
            "list": "Packages retrieved successfully.",
            "create": "Package created successfully.",
            "retrieve": "Package retrieved successfully.",
            "update": "Package updated successfully.",
            "destroy": "Package deleted successfully.",
        }.get(action, "Operation successful.")


@document_crud_view(
    tags=[PLATFORM_BILLING_TAG],
    operations={
        "GET": {
            "summary": "Retrieve package (platform admin)",
            "description": (
                "Returns a single package by ID. Requires platform.packages view "
                "permission."
            ),
        },
        "PUT": {
            "summary": "Replace package (platform admin)",
            "description": (
                "Replaces a package by ID. Requires platform.packages edit permission."
            ),
        },
        "PATCH": {
            "summary": "Update package (platform admin)",
            "description": (
                "Partially updates a package by ID. Requires platform.packages edit "
                "permission."
            ),
        },
        "DELETE": {
            "summary": "Delete package (platform admin)",
            "description": (
                "Deletes a package by ID. Requires platform.packages edit permission."
            ),
        },
    },
)
class PackageDetailView(PackageListCreateView):
    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsPlatformFeaturePermission.require("platform.packages", "view")()]
        return [IsPlatformFeaturePermission.require("platform.packages", "edit")()]


@extend_schema(
    methods=["GET"],
    tags=[PLATFORM_BILLING_TAG],
    summary="List features assigned to a package",
    description=(
        "Returns feature IDs currently assigned to a package. Requires platform.packages "
        "view permission."
    ),
    responses=envelope_responses(
        (status.HTTP_200_OK, "Package feature IDs envelope."),
    ),
)
@extend_schema(
    methods=["PUT"],
    tags=[PLATFORM_BILLING_TAG],
    summary="Replace features assigned to a package",
    description=(
        "Replaces the full feature assignment set for a package. Requires "
        "platform.packages edit permission."
    ),
    request=PackageFeatureBulkSerializer,
    responses=envelope_responses(
        (status.HTTP_200_OK, "Package features updated envelope."),
        (status.HTTP_400_BAD_REQUEST, "Validation error."),
    ),
)
class PackageFeaturesView(APIView):
    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsPlatformFeaturePermission.require("platform.packages", "view")()]
        return [IsPlatformFeaturePermission.require("platform.packages", "edit")()]

    def get(self, request, pk):
        package = get_object_or_404(Package, pk=pk)
        feature_ids = list(
            package.package_features.values_list("feature_id", flat=True)
        )
        return success_response(
            data={"package_id": str(package.id), "feature_ids": feature_ids},
            message="Package features retrieved.",
        )

    def put(self, request, pk):
        package = get_object_or_404(Package, pk=pk)
        serializer = PackageFeatureBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        wanted = set(serializer.validated_data["feature_ids"])
        with transaction.atomic():
            existing = {pf.feature_id: pf for pf in package.package_features.all()}
            for feature_id in wanted:
                if feature_id not in existing:
                    PackageFeature.objects.create(
                        package=package, feature_id=feature_id
                    )
            for feature_id, pf in existing.items():
                if feature_id not in wanted:
                    pf.delete()
        return success_response(
            data={"feature_count": len(wanted)},
            message="Package features updated.",
            status_code=status.HTTP_200_OK,
        )
