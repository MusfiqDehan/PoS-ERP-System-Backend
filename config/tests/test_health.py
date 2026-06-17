"""Health endpoint tests."""

import pytest
from django.test import Client


@pytest.mark.django_db
def test_tenant_health_returns_ok():
    client = Client()
    response = client.get("/api/v1/health/tenant/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "schema_name" in payload


@pytest.mark.django_db
def test_readiness_health_returns_checks():
    client = Client()
    response = client.get("/api/v1/health/ready/")
    assert response.status_code in (200, 503)
    payload = response.json()
    assert "checks" in payload
    assert "database" in payload["checks"]
