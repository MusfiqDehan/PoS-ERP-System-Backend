"""Platform password API tests."""

import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_platform_password_change(public_schema, platform_auth_client):
    response = platform_auth_client.post(
        "/api/v1/platform-owner/password/change/",
        {
            "current_password": "TestPass1!",
            "new_password": "NewPass123!",
        },
        format="json",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 200

    login = APIClient().post(
        "/api/v1/platform-owner/auth/login/",
        {"email": "platform@test.com", "password": "NewPass123!"},
        format="json",
        HTTP_HOST="localhost",
    )
    assert login.status_code == 200


@pytest.mark.django_db
def test_platform_password_reset_request_returns_generic_success(public_schema):
    client = APIClient()
    response = client.post(
        "/api/v1/platform-owner/password/reset/request/",
        {"email": "unknown@example.com"},
        format="json",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 200
    assert "If the account exists" in response.data["message"]
