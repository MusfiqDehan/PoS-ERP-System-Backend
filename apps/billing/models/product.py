from django.db import models

from shared.models import BaseModel


class SoftwareProductCategory(BaseModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=80, unique=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "software product category"
        verbose_name_plural = "software product categories"

    def __str__(self) -> str:
        return self.name


class SoftwareProduct(BaseModel):
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=80, unique=True)
    description = models.TextField(blank=True, default="")
    category = models.ForeignKey(
        SoftwareProductCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name
