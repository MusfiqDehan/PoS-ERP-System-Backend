import pytest
from django.contrib.auth import get_user_model
from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework.test import APIClient

from apps.tenancy.models import PlatformRole, PlatformUserRole

User = get_user_model()


@pytest.fixture(autouse=True)
def _seed_platform_roles(public_schema, db):
    from django.core.management import call_command

    call_command("seed_platform_roles")


@pytest.fixture
def platform_superadmin(public_schema):
    return User.objects.create_superadmin(
        email="platform@test.com",
        password="TestPass1!",
    )


@pytest.fixture
def platform_auth_client(platform_superadmin):
    client = APIClient()
    response = client.post(
        "/api/v1/platform-owner/auth/login/",
        {"email": "platform@test.com", "password": "TestPass1!"},
        format="json",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 200
    access = response.data["data"]["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


@pytest.fixture
def platform_manager(public_schema):
    with schema_context(get_public_schema_name()):
        role, _ = PlatformRole.objects.get_or_create(
            slug="platform_manager",
            defaults={"name": "Platform Manager", "is_system": True},
        )
        user = User.objects.create_user(
            email="manager@test.com",
            password="TestPass1!",
            full_name="Manager",
            tenant=None,
            email_verified=True,
        )
        user.password_set_at = user.created_at
        user.save(update_fields=["password_set_at"])
        PlatformUserRole.objects.create(user=user, role=role)
    return user
