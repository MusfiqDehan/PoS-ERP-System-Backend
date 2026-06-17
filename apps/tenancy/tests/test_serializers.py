"""Serializer validation tests."""

import pytest
from rest_framework.test import APIRequestFactory

from apps.access.serializers import RoleSerializer
from apps.tenancy.serializers import (
    TenantAuthSerializer,
    TenantSelfRegistrationSerializer,
)


def test_tenant_auth_requires_domain_or_subdomain():
    serializer = TenantAuthSerializer(data={"email": "a@b.com", "password": "secret"})
    assert serializer.is_valid() is False


def test_tenant_auth_accepts_subdomain():
    serializer = TenantAuthSerializer(
        data={"email": "a@b.com", "password": "secret", "subdomain": "acme"}
    )
    assert serializer.is_valid() is True
    assert serializer.validated_data["subdomain"] == "acme"


def test_registration_rejects_short_subdomain():
    serializer = TenantSelfRegistrationSerializer(
        data={
            "subdomain": "ab",
            "company_name": "Co",
            "admin_email": "owner@co.com",
        }
    )
    assert serializer.is_valid() is False


def test_role_serializer_requires_name():
    serializer = RoleSerializer(data={})
    assert serializer.is_valid() is False
    assert "name" in serializer.errors


@pytest.mark.django_db
def test_registration_accepts_valid_payload(public_schema):
    request = APIRequestFactory().post("/api/v1/tenancy/register/")
    serializer = TenantSelfRegistrationSerializer(
        data={
            "subdomain": "newco",
            "company_name": "New Co",
            "admin_email": "owner@newco.com",
        },
        context={"request": request},
    )
    assert serializer.is_valid() is True
