from rest_framework import serializers

from apps.tenancy.models import Feature


class PlatformFeatureSerializer(serializers.ModelSerializer):
    parent_key = serializers.SlugField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = Feature
        fields = [
            "key",
            "name",
            "description",
            "parent_key",
            "scope",
            "is_system",
            "sort_order",
        ]
        read_only_fields = ["is_system"]

    def validate_key(self, value):
        return value.strip()

    def to_representation(self, instance):
        from apps.platform_owner.services.features import PlatformFeatureService

        return PlatformFeatureService.serialize(instance)
