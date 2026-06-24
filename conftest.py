"""Pytest configuration for Sortorium Backend."""

from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django_tenants.utils import get_public_schema_name, schema_context

from apps.tenancy.models import Domain, Tenant

User = get_user_model()


@pytest.fixture(scope="session", autouse=True)
def _ensure_static_root_exists():
    from django.conf import settings

    Path(settings.STATIC_ROOT).mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session")
def django_db_use_migrations():
    return True


@pytest.fixture
def public_schema(db):
    """Run assertions in the public PostgreSQL schema."""
    with schema_context(get_public_schema_name()):
        yield


@pytest.fixture
def tenant(db):
    """Create an isolated tenant schema for tenant-app tests."""
    with schema_context(get_public_schema_name()):
        tenant_obj = Tenant.objects.create(
            schema_name="test_tenant",
            name="Test Tenant",
            slug="test-tenant",
            code="TEST",
            status="active",
            is_trial=False,
            features={"permissions": True, "dashboard": True},
        )
    return tenant_obj


@pytest.fixture
def tenant_schema(tenant):
    """Run test body inside the tenant PostgreSQL schema."""
    with schema_context(tenant.schema_name):
        yield tenant


@pytest.fixture
def tenant_domain(tenant, public_schema):
    domain = Domain.objects.create(
        domain="test-tenant.localhost",
        tenant=tenant,
        is_primary=True,
    )
    return domain


@pytest.fixture
def tenant_user(tenant, tenant_domain):
    with schema_context(tenant.schema_name):
        user = User.objects.create_user(
            email="user@test.com",
            password="TestPass1!",
            full_name="Test User",
        )
    return user
