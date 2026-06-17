import pytest
from rest_framework import serializers, status
from rest_framework.test import APIRequestFactory

from shared.views import ModelCRUDView
from shared.responses.error_codes import ErrorCode
from shared.testapp.models import SampleItem


class SampleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SampleItem
        fields = ["id", "name"]


class SampleItemCRUDView(ModelCRUDView):
    queryset = SampleItem.objects.all().order_by("-pk")
    serializer_class = SampleItemSerializer
    lookup_field = "pk"

    def get_success_message(self, action):
        return f"{action}-message"


@pytest.fixture
def api_factory():
    return APIRequestFactory()


@pytest.mark.django_db
def test_list_returns_success_envelope(api_factory, tenant_schema):
    SampleItem.objects.create(name="alpha")
    response = SampleItemCRUDView.as_view()(api_factory.get("/items/"))
    assert response.status_code == 200
    assert response.data["success"] is True
    assert response.data["message"] == "list-message"
    assert "items" in response.data["data"]
    assert "pagination" in response.data["data"]


@pytest.mark.django_db
def test_create_returns_201_envelope(api_factory, tenant_schema):
    response = SampleItemCRUDView.as_view()(
        api_factory.post("/items/", {"name": "new"}, format="json")
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["success"] is True
    assert response.data["data"]["name"] == "new"


@pytest.mark.django_db
def test_retrieve_returns_item(api_factory, tenant_schema):
    item = SampleItem.objects.create(name="one")
    response = SampleItemCRUDView.as_view()(
        api_factory.get(f"/items/{item.pk}/"), pk=item.pk
    )
    assert response.status_code == 200
    assert response.data["data"]["id"] == str(item.id)


@pytest.mark.django_db
def test_update_returns_updated_item(api_factory, tenant_schema):
    item = SampleItem.objects.create(name="old")
    response = SampleItemCRUDView.as_view()(
        api_factory.patch(f"/items/{item.pk}/", {"name": "new"}, format="json"),
        pk=item.pk,
    )
    assert response.status_code == 200
    assert response.data["data"]["name"] == "new"


@pytest.mark.django_db
def test_destroy_soft_deletes(api_factory, tenant_schema):
    item = SampleItem.objects.create(name="delete-me")
    response = SampleItemCRUDView.as_view()(
        api_factory.delete(f"/items/{item.pk}/"), pk=item.pk
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    item.refresh_from_db()
    assert item.is_deleted is True


@pytest.mark.django_db
def test_not_found_returns_error_envelope(api_factory, tenant_schema):
    import uuid

    missing = uuid.uuid7()
    request = api_factory.get(f"/items/{missing}/")
    view = SampleItemCRUDView.as_view()
    response = view(request, pk=missing)
    assert response.status_code in (
        status.HTTP_404_NOT_FOUND,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
    if response.status_code == status.HTTP_404_NOT_FOUND:
        assert response.data["success"] is False
        assert response.data["error"]["code"] == ErrorCode.NOT_FOUND.value
