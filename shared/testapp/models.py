from django.db import models

from shared.models import BaseModel


class SampleItem(BaseModel):
    name = models.CharField(max_length=50)

    def __str__(self) -> str:
        return self.name
