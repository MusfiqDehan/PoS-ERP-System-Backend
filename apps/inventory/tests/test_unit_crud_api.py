"""API tests for inventory unit CRUD endpoints."""

import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_list_units_requires_auth(tenant_domain):
    client = APIClient()
    response = client.get(
        "/api/v1/inventory/units/",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_unit_crud_lifecycle(tenant_domain, tenant_schema, tenant_admin):
    from apps.inventory.models import Unit

    client = APIClient()
    client.force_authenticate(user=tenant_admin)

    create_resp = client.post(
        "/api/v1/inventory/units/",
        {
            "name": "Kilogram",
            "short_name": "kg",
            "is_active": True,
        },
        format="json",
        HTTP_HOST="test-tenant.localhost",
    )
    assert create_resp.status_code == 201
    assert create_resp.data["success"] is True
    unit_id = create_resp.data["data"]["id"]
    assert create_resp.data["data"]["short_name"] == "kg"

    list_resp = client.get(
        "/api/v1/inventory/units/",
        HTTP_HOST="test-tenant.localhost",
    )
    assert list_resp.status_code == 200
    assert list_resp.data["success"] is True
    assert len(list_resp.data["data"]["items"]) == 1
    assert list_resp.data["data"]["items"][0]["name"] == "Kilogram"

    patch_resp = client.patch(
        f"/api/v1/inventory/units/{unit_id}/",
        {"short_name": "KG"},
        format="json",
        HTTP_HOST="test-tenant.localhost",
    )
    assert patch_resp.status_code == 200
    assert patch_resp.data["data"]["short_name"] == "KG"

    delete_resp = client.delete(
        f"/api/v1/inventory/units/{unit_id}/",
        HTTP_HOST="test-tenant.localhost",
    )
    assert delete_resp.status_code == 204
    assert not Unit.objects.filter(id=unit_id).exists()
    assert Unit.all_objects.filter(id=unit_id, is_deleted=True).exists()
