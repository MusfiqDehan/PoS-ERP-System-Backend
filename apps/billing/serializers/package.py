from rest_framework import serializers

from apps.billing.models import Package, PackageFeature, PackageRoleLimit
from apps.tenancy.models import Feature


class PackageFeatureSerializer(serializers.ModelSerializer):
    feature_key = serializers.CharField(source="feature.key", read_only=True)
    feature_name = serializers.CharField(source="feature.name", read_only=True)

    class Meta:
        model = PackageFeature
        fields = ["id", "feature", "feature_key", "feature_name", "limit_value"]


class PackageRoleLimitSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageRoleLimit
        fields = ["id", "role_slug", "max_users"]


class PackageSerializer(serializers.ModelSerializer):
    software_product_slug = serializers.CharField(
        source="software_product.slug", read_only=True
    )
    package_features = PackageFeatureSerializer(many=True, read_only=True)
    role_limits = PackageRoleLimitSerializer(many=True, read_only=True)
    feature_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
    )
    role_limits_data = PackageRoleLimitSerializer(
        many=True, write_only=True, required=False
    )

    class Meta:
        model = Package
        fields = [
            "id",
            "software_product",
            "software_product_slug",
            "name",
            "slug",
            "description",
            "price_monthly",
            "price_yearly",
            "is_public",
            "is_trial",
            "sort_order",
            "max_branches",
            "max_users",
            "max_custom_roles",
            "max_admins",
            "max_staff",
            "is_active",
            "package_features",
            "role_limits",
            "feature_ids",
            "role_limits_data",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def _sync_features(self, package: Package, feature_ids: list) -> None:
        wanted = set(feature_ids)
        existing = {pf.feature_id: pf for pf in package.package_features.all()}
        for feature_id in wanted:
            if feature_id not in existing:
                PackageFeature.objects.create(package=package, feature_id=feature_id)
        for feature_id, pf in existing.items():
            if feature_id not in wanted:
                pf.delete()

    def _sync_role_limits(self, package: Package, limits_data: list) -> None:
        wanted = {item["role_slug"]: item["max_users"] for item in limits_data}
        existing = {rl.role_slug: rl for rl in package.role_limits.all()}
        for role_slug, max_users in wanted.items():
            rl = existing.get(role_slug)
            if rl is None:
                PackageRoleLimit.objects.create(
                    package=package, role_slug=role_slug, max_users=max_users
                )
            elif rl.max_users != max_users:
                rl.max_users = max_users
                rl.save(update_fields=["max_users", "updated_at"])
        for role_slug, rl in existing.items():
            if role_slug not in wanted:
                rl.delete()

    def create(self, validated_data):
        feature_ids = validated_data.pop("feature_ids", None)
        role_limits_data = validated_data.pop("role_limits_data", None)
        package = Package.objects.create(**validated_data)
        if feature_ids is not None:
            self._sync_features(package, feature_ids)
        if role_limits_data is not None:
            self._sync_role_limits(package, role_limits_data)
        return package

    def update(self, instance, validated_data):
        feature_ids = validated_data.pop("feature_ids", None)
        role_limits_data = validated_data.pop("role_limits_data", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if feature_ids is not None:
            self._sync_features(instance, feature_ids)
        if role_limits_data is not None:
            self._sync_role_limits(instance, role_limits_data)
        return instance


class PackageFeatureBulkSerializer(serializers.Serializer):
    feature_ids = serializers.ListField(child=serializers.UUIDField())

    def validate_feature_ids(self, value):
        existing = set(
            Feature.objects.filter(id__in=value).values_list("id", flat=True)
        )
        missing = set(value) - existing
        if missing:
            raise serializers.ValidationError(
                f"Unknown feature ids: {sorted(str(m) for m in missing)}"
            )
        return value
