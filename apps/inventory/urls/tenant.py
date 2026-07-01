from django.urls import path

from apps.inventory.views.catalog import (
    BrandDetailView,
    BrandListCreateView,
    CategoryDetailView,
    CategoryListCreateView,
    ExpiredProductListView,
    LowStockProductListView,
    ProductDetailView,
    ProductListCreateView,
    SubCategoryListView,
    UnitDetailView,
    UnitListCreateView,
    VariantAttributeDetailView,
    VariantAttributeListCreateView,
    WarrantyDetailView,
    WarrantyListCreateView,
)
from apps.inventory.views.dashboard import (
    DashboardLowStockView,
    DashboardPendingActionsView,
    DashboardSummaryView,
)
from apps.inventory.views.locations import (
    SupplierDetailView,
    SupplierListCreateView,
    WarehouseDetailView,
    WarehouseListCreateView,
)
from apps.inventory.views.procurement import (
    GoodsReceiptCreateView,
    PurchaseOrderDetailView,
    PurchaseOrderListCreateView,
)
from apps.inventory.views.promotions import (
    CouponDetailView,
    CouponListCreateView,
    CouponValidateView,
    CustomerDetailView,
    CustomerListCreateView,
    CustomerLoyaltyView,
    GiftVoucherDetailView,
    GiftVoucherListCreateView,
    GiftVoucherValidateView,
    PromotionDetailView,
    PromotionListCreateView,
)
from apps.inventory.views.stock import (
    ReplenishmentOptionsView,
    StockAdjustmentDetailView,
    StockAdjustmentListCreateView,
    StockLevelDetailView,
    StockLevelListCreateView,
    StockMovementListView,
    StockRequestDetailView,
    StockRequestListCreateView,
    StockTransferDetailView,
    StockTransferListCreateView,
)

app_name = "inventory"

urlpatterns = [
    path("categories/", CategoryListCreateView.as_view(), name="category-list"),
    path("categories/<uuid:pk>/", CategoryDetailView.as_view(), name="category-detail"),
    path("sub-categories/", SubCategoryListView.as_view(), name="sub-category-list"),
    path("brands/", BrandListCreateView.as_view(), name="brand-list"),
    path("brands/<uuid:pk>/", BrandDetailView.as_view(), name="brand-detail"),
    path("units/", UnitListCreateView.as_view(), name="unit-list"),
    path("units/<uuid:pk>/", UnitDetailView.as_view(), name="unit-detail"),
    path("warranties/", WarrantyListCreateView.as_view(), name="warranty-list"),
    path("warranties/<uuid:pk>/", WarrantyDetailView.as_view(), name="warranty-detail"),
    path(
        "variant-attributes/",
        VariantAttributeListCreateView.as_view(),
        name="variant-attribute-list",
    ),
    path(
        "variant-attributes/<uuid:pk>/",
        VariantAttributeDetailView.as_view(),
        name="variant-attribute-detail",
    ),
    path("products/", ProductListCreateView.as_view(), name="product-list"),
    path("products/expired/", ExpiredProductListView.as_view(), name="product-expired"),
    path(
        "products/low-stock/",
        LowStockProductListView.as_view(),
        name="product-low-stock",
    ),
    path("products/<uuid:pk>/", ProductDetailView.as_view(), name="product-detail"),
    path("warehouses/", WarehouseListCreateView.as_view(), name="warehouse-list"),
    path(
        "warehouses/<uuid:pk>/", WarehouseDetailView.as_view(), name="warehouse-detail"
    ),
    path("suppliers/", SupplierListCreateView.as_view(), name="supplier-list"),
    path("suppliers/<uuid:pk>/", SupplierDetailView.as_view(), name="supplier-detail"),
    path("stock-levels/", StockLevelListCreateView.as_view(), name="stock-level-list"),
    path(
        "stock-levels/<uuid:pk>/",
        StockLevelDetailView.as_view(),
        name="stock-level-detail",
    ),
    path(
        "stock-adjustments/",
        StockAdjustmentListCreateView.as_view(),
        name="stock-adjustment-list",
    ),
    path(
        "stock-adjustments/<uuid:pk>/",
        StockAdjustmentDetailView.as_view(),
        name="stock-adjustment-detail",
    ),
    path(
        "stock-transfers/",
        StockTransferListCreateView.as_view(),
        name="stock-transfer-list",
    ),
    path(
        "stock-transfers/<uuid:pk>/",
        StockTransferDetailView.as_view(),
        name="stock-transfer-detail",
    ),
    path(
        "stock-requests/",
        StockRequestListCreateView.as_view(),
        name="stock-request-list",
    ),
    path(
        "stock-requests/<uuid:pk>/",
        StockRequestDetailView.as_view(),
        name="stock-request-detail",
    ),
    path(
        "stock-movements/", StockMovementListView.as_view(), name="stock-movement-list"
    ),
    path(
        "replenishment-options/",
        ReplenishmentOptionsView.as_view(),
        name="replenishment-options",
    ),
    path(
        "purchase-orders/",
        PurchaseOrderListCreateView.as_view(),
        name="purchase-order-list",
    ),
    path(
        "purchase-orders/<uuid:pk>/",
        PurchaseOrderDetailView.as_view(),
        name="purchase-order-detail",
    ),
    path(
        "goods-receipts/", GoodsReceiptCreateView.as_view(), name="goods-receipt-create"
    ),
    path("customers/", CustomerListCreateView.as_view(), name="customer-list"),
    path("customers/<uuid:pk>/", CustomerDetailView.as_view(), name="customer-detail"),
    path(
        "customers/<uuid:pk>/loyalty/",
        CustomerLoyaltyView.as_view(),
        name="customer-loyalty",
    ),
    path("promotions/", PromotionListCreateView.as_view(), name="promotion-list"),
    path(
        "promotions/<uuid:pk>/", PromotionDetailView.as_view(), name="promotion-detail"
    ),
    path("coupons/", CouponListCreateView.as_view(), name="coupon-list"),
    path("coupons/<uuid:pk>/", CouponDetailView.as_view(), name="coupon-detail"),
    path("coupons/validate/", CouponValidateView.as_view(), name="coupon-validate"),
    path(
        "gift-vouchers/", GiftVoucherListCreateView.as_view(), name="gift-voucher-list"
    ),
    path(
        "gift-vouchers/<uuid:pk>/",
        GiftVoucherDetailView.as_view(),
        name="gift-voucher-detail",
    ),
    path(
        "gift-vouchers/validate/",
        GiftVoucherValidateView.as_view(),
        name="gift-voucher-validate",
    ),
    path(
        "dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"
    ),
    path(
        "dashboard/low-stock/",
        DashboardLowStockView.as_view(),
        name="dashboard-low-stock",
    ),
    path(
        "dashboard/pending-actions/",
        DashboardPendingActionsView.as_view(),
        name="dashboard-pending-actions",
    ),
]
