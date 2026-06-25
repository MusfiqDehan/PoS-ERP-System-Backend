"""Platform tenant and feature API tests."""

import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_platform_tenant_list_requires_auth(public_schema):
    client = APIClient()
    response = client.get("/api/v1/platform-owner/tenants/", HTTP_HOST="localhost")
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_platform_tenant_list(public_schema, platform_auth_client, tenant):
    response = platform_auth_client.get(
        "/api/v1/platform-owner/tenants/",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 200
    assert response.data["success"] is True


@pytest.mark.django_db
def test_platform_feature_list(public_schema, platform_auth_client):
    response = platform_auth_client.get(
        "/api/v1/platform-owner/features/",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_platform_tenant_feature_overrides_get(
    public_schema, platform_auth_client, tenant
):
    tenant.features = {"pos.offline": True}
    tenant.save(update_fields=["features"])

    response = platform_auth_client.get(
        f"/api/v1/platform-owner/tenants/{tenant.id}/features/",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 200
    assert response.data["data"]["features"] == {"pos.offline": True}


@pytest.mark.django_db
def test_platform_tenant_feature_overrides_patch(
    public_schema, platform_auth_client, tenant
):
    tenant.features = {}
    tenant.save(update_fields=["features"])

    response = platform_auth_client.patch(
        f"/api/v1/platform-owner/tenants/{tenant.id}/features/",
        {"features": {"dashboard": True}},
        format="json",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 200
    assert response.data["data"]["features"] == {"dashboard": True}
    tenant.refresh_from_db()
    assert tenant.features == {"dashboard": True}


@pytest.mark.django_db
def test_platform_tenant_feature_overrides_not_found(public_schema, platform_auth_client):
    import uuid

    response = platform_auth_client.get(
        f"/api/v1/platform-owner/tenants/{uuid.uuid4()}/features/",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 404
