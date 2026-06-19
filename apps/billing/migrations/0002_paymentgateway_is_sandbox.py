from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymentgateway",
            name="is_sandbox",
            field=models.BooleanField(default=True),
        ),
    ]
