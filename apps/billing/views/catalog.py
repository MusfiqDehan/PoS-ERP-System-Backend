from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView

from apps.billing.models import Package, PackageFeature, SoftwareProduct
from apps.billing.serializers import PackageFeatureBulkSerializer, PackageSerializer
from apps.billing.serializers.product import SoftwareProductSerializer
from apps.tenancy.permissions import IsPlatformFeaturePermission
from shared.responses import success_response
from shared.views import ModelCRUDView


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


class SoftwareProductDetailView(SoftwareProductListCreateView):
    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsPlatformFeaturePermission.require("platform.billing", "view")()]
        return [IsPlatformFeaturePermission.require("platform.billing", "edit")()]


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


class PackageDetailView(PackageListCreateView):
    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsPlatformFeaturePermission.require("platform.packages", "view")()]
        return [IsPlatformFeaturePermission.require("platform.packages", "edit")()]


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
