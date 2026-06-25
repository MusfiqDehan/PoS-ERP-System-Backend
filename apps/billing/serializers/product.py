from rest_framework import serializers

from apps.billing.models import SoftwareProduct, SoftwareProductCategory


class SoftwareProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SoftwareProductCategory
        fields = [
            "id",
            "name",
            "slug",
            "sort_order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SoftwareProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = SoftwareProduct
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "category",
            "category_name",
            "sort_order",
            "is_active",
            "is_published",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
