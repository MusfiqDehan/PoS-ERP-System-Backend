from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0003_backfill_tenant_subscriptions"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="ProductCategory",
            new_name="SoftwareProductCategory",
        ),
    ]
