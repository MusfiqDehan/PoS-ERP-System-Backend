from django.db import migrations
from django.utils import timezone


def backfill_subscriptions(apps, schema_editor):
    Tenant = apps.get_model("tenancy", "Tenant")
    Package = apps.get_model("billing", "Package")
    TenantProductSubscription = apps.get_model("billing", "TenantProductSubscription")

    plan_aliases = {"free": "trial", "": "trial"}
    for tenant in Tenant.objects.all():
        plan_slug = (tenant.plan or "").strip().lower()
        plan_slug = plan_aliases.get(plan_slug, plan_slug)
        if not plan_slug:
            continue
        package = Package.objects.filter(slug=plan_slug, is_active=True).first()
        if package is None:
            continue
        exists = TenantProductSubscription.objects.filter(
            tenant=tenant,
            software_product=package.software_product_id,
            status__in=["trial", "active", "past_due"],
        ).exists()
        if exists:
            continue
        status = "trial" if tenant.is_trial else "active"
        TenantProductSubscription.objects.create(
            tenant=tenant,
            software_product_id=package.software_product_id,
            package=package,
            status=status,
            billing_cycle="monthly",
            current_period_start=tenant.subscription_start or timezone.now(),
            current_period_end=tenant.subscription_end,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0002_paymentgateway_is_sandbox"),
        ("tenancy", "0003_tenant_created_by_tenant_landing_page_enabled_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_subscriptions, migrations.RunPython.noop),
    ]
