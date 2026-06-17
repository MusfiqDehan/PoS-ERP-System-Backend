"""Tests for Branch model."""

import pytest

from apps.branch.models import Branch


@pytest.mark.django_db
def test_branch_has_uuid_primary_key(tenant_schema):
    branch = Branch.objects.create(name="Main", code="MAIN", is_headquarters=True)
    assert branch.id is not None
    assert branch.id.version == 7


@pytest.mark.django_db
def test_branch_code_unique(tenant_schema):
    Branch.objects.create(name="A", code="A1")
    with pytest.raises(Exception):
        Branch.objects.create(name="B", code="A1")


@pytest.mark.django_db
def test_branch_soft_delete(tenant_schema):
    branch = Branch.objects.create(name="Temp", code="TMP")
    branch.delete()
    assert Branch.objects.filter(pk=branch.pk).count() == 0
    assert Branch.all_objects.filter(pk=branch.pk, is_deleted=True).exists()
