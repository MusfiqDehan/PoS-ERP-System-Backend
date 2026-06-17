import pytest
from rest_framework import serializers
from rest_framework.test import APIRequestFactory

from shared.views import ModelCRUDView
from shared.pagination import CursorPagination
from shared.responses.exceptions import InvalidCursorError
from shared.testapp.models import SampleItem


class SampleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SampleItem
        fields = ["id", "name"]


class SampleItemListView(ModelCRUDView):
    queryset = SampleItem.objects.all().order_by("-pk")
    serializer_class = SampleItemSerializer


@pytest.mark.django_db
def test_cursor_pagination_first_page(tenant_schema):
    for index in range(15):
        SampleItem.objects.create(name=f"item{index}")

    factory = APIRequestFactory()
    request = factory.get("/items/")
    view = SampleItemListView.as_view()
    response = view(request)

    assert response.status_code == 200
    assert response.data["success"] is True
    assert len(response.data["data"]["items"]) == 10
    pagination = response.data["data"]["pagination"]
    assert pagination["page_size"] == 10
    assert pagination["has_next"] is True
    assert pagination["has_previous"] is False
    assert "next_cursor" in pagination


@pytest.mark.django_db
def test_cursor_pagination_next_page(tenant_schema):
    for index in range(15):
        SampleItem.objects.create(name=f"next{index}")

    factory = APIRequestFactory()
    view = SampleItemListView.as_view()
    first_response = view(factory.get("/items/"))
    next_cursor = first_response.data["data"]["pagination"]["next_cursor"]

    second_response = view(factory.get("/items/", {"cursor": next_cursor}))
    assert second_response.status_code == 200
    assert len(second_response.data["data"]["items"]) == 5
    pagination = second_response.data["data"]["pagination"]
    assert pagination["has_next"] is False
    assert pagination["has_previous"] is True
    assert "previous_cursor" in pagination


@pytest.mark.django_db
def test_cursor_pagination_custom_page_size_capped(tenant_schema):
    for index in range(5):
        SampleItem.objects.create(name=f"size{index}")

    factory = APIRequestFactory()
    response = SampleItemListView.as_view()(factory.get("/items/", {"page_size": 200}))
    assert response.data["data"]["pagination"]["page_size"] == 100


def test_invalid_cursor_raises_domain_error():
    factory = APIRequestFactory()
    paginator = CursorPagination()
    request = factory.get("/items/", {"cursor": "not-valid"})
    from rest_framework.request import Request

    drf_request = Request(request)
    with pytest.raises(InvalidCursorError):
        paginator.decode_cursor(drf_request)
