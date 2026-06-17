from django.apps import AppConfig


class SharedTestappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "shared.testapp"
    label = "shared_testapp"
