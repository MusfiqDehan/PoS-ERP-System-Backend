"""Tests for branch provisioning and APIs."""

import pytest
from django_tenants.utils import schema_context

from apps.branch.models import Branch
from apps.tenancy.services.registration import TenantRegistrationService


@pytest.mark.django_db
def test_bootstrap_creates_main_branch(tenant):
    TenantRegistrationService.bootstrap_tenant_schema(tenant)
    with schema_context(tenant.schema_name):
        branch = Branch.objects.get(code="MAIN")
        assert branch.name == "Main Branch"
        assert branch.is_headquarters is True


@pytest.mark.django_db
def test_branch_create_enforces_limit(
    tenant, tenant_domain, tenant_schema, public_schema
):
    from apps.access.models import Role, UserRole
    from apps.billing.models import (
        Package,
        PackageFeature,
        SoftwareProduct,
        TenantProductSubscription,
    )
    from apps.tenancy.models import Feature
    from django.contrib.auth import get_user_model
    from django_tenants.utils import get_public_schema_name, schema_context
    from rest_framework.test import APIClient
    from shared.cache.helpers import invalidate_tenant_features

    User = get_user_model()
    with schema_context(get_public_schema_name()):
        product = SoftwareProduct.objects.create(
            name="Sortorium PoS", slug="sortorium-pos"
        )
        package = Package.objects.create(
            software_product=product, name="Trial", slug="trial", max_branches=1
        )
        feature = Feature.objects.create(key="branches", name="Branches")
        PackageFeature.objects.create(package=package, feature=feature)
        TenantProductSubscription.objects.create(
            tenant=tenant,
            software_product=product,
            package=package,
            status=TenantProductSubscription.STATUS_ACTIVE,
        )
        invalidate_tenant_features(tenant.id)
    with schema_context(tenant.schema_name):
        admin = User.objects.create_user(email="admin@test.com", password="TestPass1!")
        role = Role.objects.create(name="Admin", slug="admin", is_system=True)
        UserRole.objects.create(user_id=admin.id, user_email=admin.email, role=role)
        Branch.objects.create(name="Existing", code="EX1")

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.post(
        "/api/v1/branches/",
        {"name": "Second", "code": "EX2"},
        format="json",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 403
    assert response.data["success"] is False
    assert response.data["error_code"] == "LIMIT_EXCEEDED"
