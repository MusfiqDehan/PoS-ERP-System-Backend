from __future__ import annotations

from apps.tenancy.models import Feature


class PlatformFeatureService:
    @staticmethod
    def list_features():
        return Feature.objects.all().select_related("parent").order_by("sort_order", "key")

    @staticmethod
    def create_feature(*, data: dict) -> Feature:
        parent_key = data.pop("parent_key", None)
        parent = None
        if parent_key:
            parent = Feature.objects.filter(key=parent_key).first()
            if parent is None:
                raise ValueError("Parent feature not found.")
        if Feature.objects.filter(key=data["key"]).exists():
            raise ValueError("Feature key already exists.")
        return Feature.objects.create(parent=parent, is_system=False, **data)

    @staticmethod
    def update_feature(feature: Feature, *, data: dict) -> Feature:
        if feature.is_system:
            blocked = {"key", "scope", "is_system"}
            if blocked.intersection(data.keys()):
                raise ValueError("Cannot change key, scope, or is_system on system features.")
        parent_key = data.pop("parent_key", None)
        if parent_key is not None:
            if parent_key == "":
                feature.parent = None
            else:
                parent = Feature.objects.filter(key=parent_key).first()
                if parent is None:
                    raise ValueError("Parent feature not found.")
                feature.parent = parent
        for field, value in data.items():
            setattr(feature, field, value)
        feature.save()
        return feature

    @staticmethod
    def serialize(feature: Feature) -> dict:
        return {
            "key": feature.key,
            "name": feature.name,
            "description": feature.description,
            "parent_key": feature.parent.key if feature.parent_id else None,
            "scope": feature.scope,
            "is_system": feature.is_system,
            "sort_order": feature.sort_order,
        }
