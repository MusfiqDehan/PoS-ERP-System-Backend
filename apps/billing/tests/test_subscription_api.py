"""Tests for subscription APIs and feature overrides."""

import pytest
from rest_framework.test import APIClient

from apps.billing.models import Package, SoftwareProduct, TenantProductSubscription


@pytest.mark.django_db
def test_subscription_summary_requires_admin(tenant, tenant_domain, tenant_user):
    client = APIClient()
    client.force_authenticate(user=tenant_user)
    response = client.get(
        "/api/v1/billing/subscription/summary/",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 403
    assert response.data["success"] is False


@pytest.mark.django_db
def test_subscription_summary_for_admin(
    tenant, tenant_domain, tenant_schema, public_schema
):
    from apps.access.models import Role, UserRole
    from django.contrib.auth import get_user_model
    from django_tenants.utils import get_public_schema_name, schema_context

    User = get_user_model()
    with schema_context(tenant.schema_name):
        admin = User.objects.create_user(
            email="admin@test.com", password="TestPass1!", full_name="Admin"
        )
        role = Role.objects.create(name="Admin", slug="admin", is_system=True)
        UserRole.objects.create(user_id=admin.id, user_email=admin.email, role=role)

    with schema_context(get_public_schema_name()):
        product = SoftwareProduct.objects.create(
            name="Sortorium PoS", slug="sortorium-pos"
        )
        package = Package.objects.create(
            software_product=product, name="Trial", slug="trial"
        )
        TenantProductSubscription.objects.create(
            tenant=tenant,
            software_product=product,
            package=package,
            status=TenantProductSubscription.STATUS_TRIAL,
        )

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get(
        "/api/v1/billing/subscription/summary/",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 200
    assert response.data["success"] is True
    assert len(response.data["data"]["subscriptions"]) == 1


@pytest.mark.django_db
def test_feature_override_disable(public_schema, tenant):
    from apps.billing.models import PackageFeature
    from apps.tenancy.models import Feature
    from apps.tenancy.services.features import tenant_has_feature

    product = SoftwareProduct.objects.create(name="Sortorium PoS", slug="sortorium-pos")
    package = Package.objects.create(
        software_product=product, name="Trial", slug="trial"
    )
    feature = Feature.objects.create(key="pos", name="Point of Sale")
    PackageFeature.objects.create(package=package, feature=feature)
    TenantProductSubscription.objects.create(
        tenant=tenant,
        software_product=product,
        package=package,
        status=TenantProductSubscription.STATUS_ACTIVE,
    )
    tenant.features = {"pos": {"enabled": False}}
    tenant.save(update_fields=["features"])

    assert tenant_has_feature(tenant, "pos") is False


@pytest.mark.django_db
def test_feature_override_force_enable(public_schema, tenant):
    from apps.tenancy.services.features import tenant_has_feature
    from django_tenants.utils import get_public_schema_name, schema_context
    from shared.cache.helpers import invalidate_tenant_features

    with schema_context(get_public_schema_name()):
        tenant.features = {"pos": {"enabled": False, "force_enable": True}}
        tenant.save(update_fields=["features"])
        invalidate_tenant_features(tenant.id)

    assert tenant_has_feature(tenant, "pos") is True


@pytest.mark.django_db
def test_legacy_boolean_feature_override(public_schema, tenant):
    from apps.tenancy.services.features import tenant_has_feature
    from shared.cache.helpers import invalidate_tenant_features

    tenant.features = {"reports": True}
    tenant.save(update_fields=["features"])
    invalidate_tenant_features(tenant.id)

    assert tenant_has_feature(tenant, "reports") is True
