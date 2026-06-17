"""Tests for User model."""

import pytest

from apps.tenancy.models import User


@pytest.mark.django_db
def test_user_has_no_role_field():
    assert not hasattr(User, "role") or "role" not in {
        f.name for f in User._meta.get_fields()
    }


@pytest.mark.django_db
def test_create_user_with_email():
    user = User.objects.create_user(email="user@example.com", password="TestPass1!")
    assert user.id.version == 7
    assert user.password_set_at is not None


@pytest.mark.django_db
def test_create_superuser():
    user = User.objects.create_superuser(
        email="admin@example.com", password="TestPass1!"
    )
    assert user.is_superuser is True
    assert user.is_staff is True
