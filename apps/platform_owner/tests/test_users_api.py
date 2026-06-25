"""Platform user service and API tests."""

import pytest
from django.contrib.auth import get_user_model
from django_tenants.utils import get_public_schema_name, schema_context

from apps.platform_owner.services.users import PlatformUserService
from apps.tenancy.models import PlatformRole, PlatformUserRole

User = get_user_model()


@pytest.mark.django_db
def test_list_platform_users_queryset(public_schema, platform_superadmin):
    users = list(PlatformUserService.queryset())
    assert any(u.email == "platform@test.com" for u in users)


@pytest.mark.django_db
def test_replace_roles_blocks_last_superadmin_self_demotion(public_schema, platform_superadmin):
    with pytest.raises(ValueError, match="last superadmin"):
        PlatformUserService.replace_roles(
            actor=platform_superadmin,
            user=platform_superadmin,
            role_slugs=["platform_manager"],
        )


@pytest.mark.django_db
def test_platform_users_list_and_detail_api(public_schema, platform_auth_client):
    listing = platform_auth_client.get(
        "/api/v1/platform-owner/users/",
        HTTP_HOST="localhost",
    )
    assert listing.status_code == 200
    user_id = listing.data["data"]["items"][0]["id"]
    detail = platform_auth_client.get(
        f"/api/v1/platform-owner/users/{user_id}/",
        HTTP_HOST="localhost",
    )
    assert detail.status_code == 200


@pytest.mark.django_db
def test_deactivate_blocks_last_superadmin(public_schema, platform_superadmin, platform_auth_client):
    response = platform_auth_client.post(
        f"/api/v1/platform-owner/users/{platform_superadmin.id}/deactivate/",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_patch_roles_assigns_platform_manager(
    public_schema, platform_superadmin, platform_manager
):
    with schema_context(get_public_schema_name()):
        role = PlatformRole.objects.get(slug="support_agent")
        PlatformUserRole.objects.filter(user=platform_manager).delete()
        PlatformUserRole.objects.create(user=platform_manager, role=role)

    client = __import__("rest_framework.test", fromlist=["APIClient"]).APIClient()
    login = client.post(
        "/api/v1/platform-owner/auth/login/",
        {"email": "platform@test.com", "password": "TestPass1!"},
        format="json",
        HTTP_HOST="localhost",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['data']['access']}")
    response = client.patch(
        f"/api/v1/platform-owner/users/{platform_manager.id}/roles/",
        {"role_slugs": ["platform_manager"]},
        format="json",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 200
    assert response.data["data"]["platform_roles"] == ["platform_manager"]
