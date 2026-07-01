"""Remove redundant active/inactive status fields from inventory master data."""

from django.db import migrations

MASTER_DATA_MODELS = (
    "Category",
    "Brand",
    "Unit",
    "Warranty",
    "VariantAttribute",
    "Warehouse",
    "Supplier",
    "Promotion",
    "GiftVoucher",
)


def sync_is_active_from_status(apps, schema_editor):
    for model_name in MASTER_DATA_MODELS:
        model = apps.get_model("inventory", model_name)
        model.objects.filter(status="inactive").update(is_active=False)
        model.objects.filter(status="active").update(is_active=True)


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0003_stock_level_null_variant_unique"),
    ]

    operations = [
        migrations.RunPython(sync_is_active_from_status, migrations.RunPython.noop),
        migrations.RemoveField(model_name="brand", name="status"),
        migrations.RemoveField(model_name="category", name="status"),
        migrations.RemoveField(model_name="giftvoucher", name="status"),
        migrations.RemoveField(model_name="promotion", name="status"),
        migrations.RemoveField(model_name="supplier", name="status"),
        migrations.RemoveField(model_name="unit", name="status"),
        migrations.RemoveField(model_name="variantattribute", name="status"),
        migrations.RemoveField(model_name="warehouse", name="status"),
        migrations.RemoveField(model_name="warranty", name="status"),
    ]
