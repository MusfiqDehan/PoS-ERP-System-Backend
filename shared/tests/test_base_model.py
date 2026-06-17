import uuid

import pytest
from rest_framework import serializers
from rest_framework.test import APIRequestFactory

from shared.models import BaseModel, generate_uuid7
from shared.views import ModelCRUDView
from shared.testapp.models import SampleItem


def test_generate_uuid7_returns_uuid_v7():
    value = generate_uuid7()
    assert isinstance(value, uuid.UUID)
    assert value.version == 7


def test_generate_uuid7_returns_unique_values():
    first = generate_uuid7()
    second = generate_uuid7()
    assert first != second


def test_base_model_is_abstract():
    assert BaseModel._meta.abstract is True


@pytest.mark.django_db
def test_base_model_auto_assigns_uuid_v7_id(tenant_schema):
    item = SampleItem.objects.create(name="alpha")
    assert item.id is not None
    assert item.id.version == 7


@pytest.mark.django_db
def test_base_model_id_is_non_editable(tenant_schema):
    id_field = SampleItem._meta.get_field("id")
    assert id_field.primary_key is True
    assert id_field.editable is False


@pytest.mark.django_db
def test_base_model_id_unchanged_on_update(tenant_schema):
    item = SampleItem.objects.create(name="alpha")
    original_id = item.id
    item.name = "beta"
    item.save()
    item.refresh_from_db()
    assert item.id == original_id


@pytest.mark.django_db
def test_base_model_soft_delete_preserves_id(tenant_schema):
    item = SampleItem.objects.create(name="alpha")
    original_id = item.id
    item.delete()
    item.refresh_from_db()
    assert item.is_deleted is True
    assert item.deleted_at is not None
    assert item.id == original_id


@pytest.mark.django_db
def test_base_model_restore_preserves_id(tenant_schema):
    item = SampleItem.objects.create(name="alpha")
    original_id = item.id
    item.delete()
    item.restore()
    item.refresh_from_db()
    assert item.is_deleted is False
    assert item.deleted_at is None
    assert item.id == original_id


@pytest.mark.django_db
def test_base_model_audit_fields_present(tenant_schema):
    item = SampleItem.objects.create(name="alpha")
    assert item.created_at is not None
    assert item.updated_at is not None
    assert item.is_active is True
    assert item.is_published is False


@pytest.mark.django_db
def test_subclass_uses_uuid_primary_key(tenant_schema):
    pk_fields = [field for field in SampleItem._meta.local_fields if field.primary_key]
    assert len(pk_fields) == 1
    assert pk_fields[0].name == "id"
    assert pk_fields[0].get_internal_type() == "UUIDField"


@pytest.mark.django_db
def test_cursor_pagination_orders_uuid_models_newest_first(tenant_schema):
    first = SampleItem.objects.create(name="first")
    second = SampleItem.objects.create(name="second")
    third = SampleItem.objects.create(name="third")

    class SampleItemSerializer(serializers.ModelSerializer):
        class Meta:
            model = SampleItem
            fields = ["id", "name"]

    class SampleItemView(ModelCRUDView):
        queryset = SampleItem.objects.all().order_by("-pk")
        serializer_class = SampleItemSerializer

    response = SampleItemView.as_view()(APIRequestFactory().get("/items/"))
    ids = [item["id"] for item in response.data["data"]["items"]]

    assert str(third.id) == ids[0]
    assert str(second.id) == ids[1]
    assert str(first.id) == ids[2]


@pytest.mark.django_db
def test_api_response_exposes_id_as_uuid_string(tenant_schema):
    class SampleItemSerializer(serializers.ModelSerializer):
        class Meta:
            model = SampleItem
            fields = ["id", "name"]

    class SampleItemView(ModelCRUDView):
        queryset = SampleItem.objects.all().order_by("-pk")
        serializer_class = SampleItemSerializer

    create_response = SampleItemView.as_view()(
        APIRequestFactory().post("/items/", {"name": "widget"}, format="json")
    )
    assert create_response.status_code == 201
    created_id = create_response.data["data"]["id"]
    assert isinstance(created_id, str)
    assert uuid.UUID(created_id).version == 7

    item = SampleItem.objects.get(name="widget")
    retrieve_response = SampleItemView.as_view()(
        APIRequestFactory().get(f"/items/{item.pk}/"),
        pk=item.pk,
    )
    assert retrieve_response.data["data"]["id"] == created_id
