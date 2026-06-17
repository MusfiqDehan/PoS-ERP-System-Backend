"""Tests for platform RBAC and Feature models."""

import pytest

from apps.tenancy.models import (
    Feature,
    PlatformRole,
    PlatformRolePermission,
    PlatformUserRole,
    User,
)


@pytest.mark.django_db
def test_platform_role_permission_unique(public_schema):
    role = PlatformRole.objects.create(name="Manager", slug="manager")
    PlatformRolePermission.objects.create(
        role=role, module_key="tenants", permission_level="edit"
    )
    with pytest.raises(Exception):
        PlatformRolePermission.objects.create(
            role=role, module_key="tenants", permission_level="view"
        )


@pytest.mark.django_db
def test_feature_unique_key(public_schema):
    Feature.objects.create(key="dashboard", name="Dashboard")
    with pytest.raises(Exception):
        Feature.objects.create(key="dashboard", name="Dashboard Duplicate")


@pytest.mark.django_db
def test_platform_user_role_assignment(public_schema):
    role = PlatformRole.objects.create(name="Support", slug="support")
    user = User.objects.create_user(email="support@example.com", password="TestPass1!")
    assignment = PlatformUserRole.objects.create(user=user, role=role)
    assert assignment.user_id == user.id
    assert assignment.role.slug == "support"
