"""Platform tenant and feature API tests."""

import pytest


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
