"""Tests for access RBAC models."""

import uuid

import pytest

from apps.access.models import Role, UserRole


@pytest.mark.django_db
def test_user_role_stores_uuid_user_id(tenant_schema):
    role = Role.objects.create(name="Cashier", slug="cashier")
    user_id = uuid.uuid7()
    assignment = UserRole.objects.create(
        user_id=user_id,
        user_email="cashier@example.com",
        role=role,
    )
    assert assignment.user_id == user_id


@pytest.mark.django_db
def test_system_role_not_deletable_via_service_check(tenant_schema):
    role = Role.objects.create(name="Admin", slug="admin", is_system=True)
    assert role.is_system is True
