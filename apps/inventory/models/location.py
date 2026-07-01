from django.db import models

from shared.models import BaseModel


class Warehouse(BaseModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    contact_person = models.CharField(max_length=255, blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    address = models.TextField(blank=True, default="")
    city = models.CharField(max_length=120, blank=True, default="")
    is_central = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
