"""Platform SaaS subscription billing helpers."""

from __future__ import annotations

import uuid
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, schema_context

from apps.billing.models import (
    Package,
    PaymentGateway,
    TenantProductSubscription,
    TenantSubscriptionInvoice,
)
from apps.billing.services.factory import get_gateway
from apps.billing.services.limits_sync import (
    ACTIVE_STATUSES,
    compute_effective_limits,
    sync_tenant_denormalized_limits,
)
from apps.billing.services.base import build_callback_urls
from apps.tenancy.models import PlatformSettings, Tenant
from apps.tenancy.services.features import set_tenant_features
from shared.platform.currency import convert_currency


def _resolve_package(
    *, package_slug: str, software_product_slug: str | None = None
) -> Package:
    qs = Package.objects.filter(slug=package_slug, is_active=True).select_related(
        "software_product"
    )
    if software_product_slug:
        qs = qs.filter(software_product__slug=software_product_slug)
    pkg = qs.first()
    if pkg is None:
        raise ValueError(f"Package '{package_slug}' is not available.")
    return pkg


def _sync_tenant_features_from_subscriptions(tenant: Tenant) -> None:
    limits = compute_effective_limits(tenant)
    set_tenant_features(tenant, sorted(limits.feature_keys))


def activate_tenant_subscription(invoice: TenantSubscriptionInvoice) -> None:
    """Activate or update subscription from a successful invoice."""
    tenant = invoice.tenant
    if tenant is None:
        return

    with schema_context(get_public_schema_name()):
        pkg = (
            Package.objects.filter(slug=invoice.package_slug)
            .select_related("software_product")
            .first()
        )
        if pkg is None:
            return

        live_tenant = Tenant.objects.select_for_update().get(pk=tenant.pk)
        now = timezone.now()

        sub = (
            TenantProductSubscription.objects.filter(
                tenant=live_tenant,
                software_product=pkg.software_product,
                status__in=ACTIVE_STATUSES,
            )
            .select_for_update()
            .first()
        )
        if sub is None:
            sub = TenantProductSubscription(
                tenant=live_tenant,
                software_product=pkg.software_product,
            )
        sub.package = pkg
        sub.status = TenantProductSubscription.STATUS_ACTIVE
        sub.billing_cycle = invoice.billing_cycle
        sub.current_period_start = invoice.period_start or now
        sub.current_period_end = invoice.period_end
        sub.cancelled_at = None
        sub.save()

        live_tenant.is_trial = False
        live_tenant.status = "active"
        live_tenant.plan = pkg.slug
        live_tenant.subscription_start = sub.current_period_start
        live_tenant.subscription_end = sub.current_period_end
        live_tenant.save(
            update_fields=[
                "is_trial",
                "status",
                "plan",
                "subscription_start",
                "subscription_end",
                "updated_at",
            ]
        )
        sync_tenant_denormalized_limits(live_tenant)
        _sync_tenant_features_from_subscriptions(live_tenant)


def initiate_for_tenant(
    *,
    tenant,
    package_slug: str,
    billing_cycle: str,
    request,
    software_product_slug: str | None = None,
) -> tuple[str, str, TenantSubscriptionInvoice]:
    """Create pending invoice and initiate gateway. Returns (gateway_url, tran_id, invoice)."""
    public_schema = get_public_schema_name()
    with schema_context(public_schema):
        with transaction.atomic():
            live_tenant = Tenant.objects.select_for_update().get(pk=tenant.pk)
            pkg = _resolve_package(
                package_slug=package_slug,
                software_product_slug=software_product_slug,
            )
            if not pkg.is_public:
                raise ValueError(f"Package '{package_slug}' is not publicly available.")

            if billing_cycle == "yearly":
                amount_usd = pkg.price_yearly
                period_days = 365
            else:
                amount_usd = pkg.price_monthly
                period_days = 30

            now = timezone.now()
            period_end = now + timedelta(days=period_days)

            if amount_usd <= Decimal("0"):
                tran_id = f"TRIAL-{live_tenant.schema_name.upper()}-{uuid.uuid4().hex[:12].upper()}"
                invoice = TenantSubscriptionInvoice.objects.create(
                    tenant=live_tenant,
                    software_product_slug=pkg.software_product.slug,
                    package_slug=pkg.slug,
                    tran_id=tran_id,
                    amount=Decimal("0"),
                    currency="USD",
                    status=TenantSubscriptionInvoice.STATUS_SUCCESS,
                    billing_cycle=billing_cycle,
                    period_start=now,
                    period_end=period_end,
                    gateway_slug="manual",
                    validated_at=now,
                )
                activate_tenant_subscription(invoice)
                return "", tran_id, invoice

            gateway = PaymentGateway.objects.filter(
                is_default_for_subscriptions=True, is_active=True
            ).first()
            if gateway is None or not (gateway.platform_credentials or {}):
                raise RuntimeError("No subscription payment gateway is configured.")

            ps = PlatformSettings.objects.first()
            target_currency = ps.default_currency if ps else "USD"
            amount = convert_currency(amount_usd, "USD", target_currency)

            tran_id = (
                f"SUB-{live_tenant.schema_name.upper()}-{uuid.uuid4().hex[:12].upper()}"
            )
            invoice = TenantSubscriptionInvoice.objects.create(
                tenant=live_tenant,
                software_product_slug=pkg.software_product.slug,
                package_slug=pkg.slug,
                tran_id=tran_id,
                amount=amount,
                currency=target_currency,
                status=TenantSubscriptionInvoice.STATUS_PENDING,
                billing_cycle=billing_cycle,
                period_start=now,
                period_end=period_end,
                gateway_slug=gateway.slug,
            )

        callbacks = build_callback_urls(request)
        svc = get_gateway(
            gateway.slug,
            credentials=gateway.platform_credentials,
            is_sandbox=gateway.is_sandbox,
            **callbacks,
        )
        invoice.tenant = live_tenant
        result = svc.initiate(invoice)
        gateway_url = result.get("gateway_url", "")
        if not gateway_url:
            invoice.status = TenantSubscriptionInvoice.STATUS_CANCELLED
            invoice.save(update_fields=["status", "updated_at"])
            raise RuntimeError("Failed to initiate payment with the gateway.")
        return gateway_url, tran_id, invoice
