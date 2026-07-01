from django.urls import path

from apps.inventory.views.pos import (
    POSCartValidateView,
    POSCheckoutView,
    POSOrderDetailView,
    POSOrderListView,
    POSProductListView,
)

app_name = "pos"

urlpatterns = [
    path("products/", POSProductListView.as_view(), name="pos-product-list"),
    path("cart/validate/", POSCartValidateView.as_view(), name="pos-cart-validate"),
    path("checkout/", POSCheckoutView.as_view(), name="pos-checkout"),
    path("orders/", POSOrderListView.as_view(), name="pos-order-list"),
    path("orders/<uuid:pk>/", POSOrderDetailView.as_view(), name="pos-order-detail"),
]
