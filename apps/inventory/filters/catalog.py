"""Django-filter sets for inventory catalog list endpoints."""

from django_filters import FilterSet

from apps.inventory.models import Product


class ProductFilterSet(FilterSet):
    class Meta:
        model = Product
        fields = {
            "category": ["exact"],
            "brand": ["exact"],
            "is_active": ["exact"],
            "product_type": ["exact"],
        }
