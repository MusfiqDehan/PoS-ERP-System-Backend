from django.db import models

from shared.models import BaseModel


class Category(BaseModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Brand(BaseModel):
    name = models.CharField(max_length=255)
    logo = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Unit(BaseModel):
    name = models.CharField(max_length=100)
    short_name = models.CharField(max_length=20)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Warranty(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    duration_days = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class VariantAttribute(BaseModel):
    name = models.CharField(max_length=255)
    values = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Product(BaseModel):
    TYPE_SINGLE = "single"
    TYPE_VARIABLE = "variable"
    PRODUCT_TYPE_CHOICES = [
        (TYPE_SINGLE, "Single"),
        (TYPE_VARIABLE, "Variable"),
    ]

    SELLING_RETAIL = "retail"
    SELLING_WHOLESALE = "wholesale"
    SELLING_TYPE_CHOICES = [
        (SELLING_RETAIL, "Retail"),
        (SELLING_WHOLESALE, "Wholesale"),
    ]

    TAX_INCLUSIVE = "inclusive"
    TAX_EXCLUSIVE = "exclusive"
    TAX_NONE = "none"
    TAX_TYPE_CHOICES = [
        (TAX_INCLUSIVE, "Inclusive"),
        (TAX_EXCLUSIVE, "Exclusive"),
        (TAX_NONE, "None"),
    ]

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    sku = models.CharField(max_length=100, unique=True)
    barcode = models.CharField(max_length=100, blank=True, default="")
    description = models.TextField(blank=True, default="")
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name="products",
    )
    warranty = models.ForeignKey(
        Warranty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    product_type = models.CharField(
        max_length=20,
        choices=PRODUCT_TYPE_CHOICES,
        default=TYPE_SINGLE,
    )
    selling_type = models.CharField(
        max_length=20,
        choices=SELLING_TYPE_CHOICES,
        default=SELLING_RETAIL,
    )
    tax_type = models.CharField(
        max_length=20,
        choices=TAX_TYPE_CHOICES,
        default=TAX_EXCLUSIVE,
    )
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    min_qty_alert = models.PositiveIntegerField(default=0)
    manufactured_at = models.DateField(null=True, blank=True)
    expires_at = models.DateField(null=True, blank=True)
    images = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class ProductVariant(BaseModel):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
    )
    sku = models.CharField(max_length=100, unique=True)
    barcode = models.CharField(max_length=100, blank=True, default="")
    attributes = models.JSONField(default=dict, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["sku"]

    def __str__(self) -> str:
        return f"{self.product.name} ({self.sku})"
