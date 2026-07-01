from rest_framework import serializers

from apps.inventory.models import (
    Brand,
    Category,
    Product,
    ProductVariant,
    Unit,
    VariantAttribute,
    Warranty,
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "parent",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = [
            "id",
            "name",
            "logo",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = [
            "id",
            "name",
            "short_name",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class WarrantySerializer(serializers.ModelSerializer):
    class Meta:
        model = Warranty
        fields = [
            "id",
            "name",
            "description",
            "duration_days",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class VariantAttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VariantAttribute
        fields = [
            "id",
            "name",
            "values",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "sku",
            "barcode",
            "attributes",
            "price",
            "cost",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProductSerializer(serializers.ModelSerializer):
    variants = ProductVariantSerializer(many=True, required=False)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "sku",
            "barcode",
            "description",
            "category",
            "brand",
            "unit",
            "warranty",
            "product_type",
            "selling_type",
            "tax_type",
            "price",
            "cost",
            "min_qty_alert",
            "manufactured_at",
            "expires_at",
            "images",
            "variants",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "created_by"]

    def validate(self, attrs):
        product_type = attrs.get(
            "product_type",
            getattr(self.instance, "product_type", Product.TYPE_SINGLE),
        )
        variants = attrs.get("variants")
        if variants is None and self.instance is not None:
            variants = []
        variants = variants or []

        if product_type == Product.TYPE_VARIABLE and not variants:
            raise serializers.ValidationError(
                {"variants": "Variable products require at least one variant."}
            )

        skus = [variant.get("sku") for variant in variants if variant.get("sku")]
        if len(skus) != len(set(skus)):
            raise serializers.ValidationError(
                {"variants": "Variant SKUs must be unique within the payload."}
            )
        return attrs

    def create(self, validated_data):
        variants_data = validated_data.pop("variants", [])
        product = Product.objects.create(**validated_data)
        for variant_data in variants_data:
            ProductVariant.objects.create(product=product, **variant_data)
        return product

    def update(self, instance, validated_data):
        variants_data = validated_data.pop("variants", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if variants_data is not None:
            instance.variants.all().delete()
            for variant_data in variants_data:
                ProductVariant.objects.create(product=instance, **variant_data)
        return instance
