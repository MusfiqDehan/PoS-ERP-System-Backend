from django.contrib import admin

from apps.inventory import models

for model in [
    models.Category,
    models.Brand,
    models.Unit,
    models.Warranty,
    models.VariantAttribute,
    models.Product,
    models.ProductVariant,
    models.Warehouse,
    models.Supplier,
    models.StockLevel,
    models.StockMovement,
    models.StockAdjustment,
    models.StockTransfer,
    models.StockTransferLine,
    models.StockRequest,
    models.StockRequestLine,
    models.PurchaseOrder,
    models.PurchaseOrderLine,
    models.GoodsReceipt,
    models.GoodsReceiptLine,
    models.Customer,
    models.LoyaltyAccount,
    models.Promotion,
    models.Coupon,
    models.GiftVoucher,
    models.Sale,
    models.SaleLine,
    models.SalePayment,
    models.SaleDiscount,
]:
    admin.site.register(model)
