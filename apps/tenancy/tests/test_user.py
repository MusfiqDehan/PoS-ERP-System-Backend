"""Tests for User model."""

import pytest
from django.contrib.auth.hashers import check_password

from apps.tenancy.models import PlatformUserRole, User


@pytest.mark.django_db
def test_user_has_no_role_field():
    assert not hasattr(User, "role") or "role" not in {
        f.name for f in User._meta.get_fields()
    }


@pytest.mark.django_db
def test_user_base_model_fields():
    field_names = {f.name for f in User._meta.get_fields()}
    assert "updated_at" in field_names
    assert "is_deleted" in field_names
    assert "created_by" in field_names
    assert "is_staff" not in field_names
    assert "is_superuser" not in field_names
    assert "groups" not in field_names
    assert "user_permissions" not in field_names


@pytest.mark.django_db
def test_create_user_with_email():
    user = User.objects.create_user(email="user@example.com", password="TestPass1!")
    assert user.id.version == 7
    assert user.password_set_at is not None
    assert check_password("TestPass1!", user.password)


@pytest.mark.django_db
def test_user_manager_requires_email_or_phone():
    with pytest.raises(ValueError, match="either email or phone"):
        User.objects.create_user(password="TestPass1!")


@pytest.mark.django_db
def test_create_superadmin_assigns_role(public_schema):
    user = User.objects.create_superadmin(
        email="admin@example.com", password="TestPass1!"
    )
    assert PlatformUserRole.objects.filter(user=user, role__slug="superadmin").exists()


@pytest.mark.django_db
def test_user_password_protocol():
    user = User.objects.create_user(email="pw@example.com", password="secret")
    assert user.check_password("secret") is True
    assert user.check_password("wrong") is False
    user.set_password("newsecret")
    assert user.check_password("newsecret") is True
    assert user.is_authenticated is True
    assert user.is_anonymous is False
