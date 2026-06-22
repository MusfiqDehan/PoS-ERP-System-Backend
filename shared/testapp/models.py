from django.db import models

from shared.models import BaseModel


class SampleItem(BaseModel):
    name = models.CharField(max_length=50)

    class Meta:
        app_label = "shared_testapp"

    def __str__(self) -> str:
        return self.name
