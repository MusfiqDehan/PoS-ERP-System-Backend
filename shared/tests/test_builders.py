from rest_framework import status

from shared.responses.builders import (
    error_response,
    list_success_response,
    omit_empty,
    success_response,
)


def test_omit_empty_removes_none_empty_dict_and_list():
    payload = {
        "a": None,
        "b": {},
        "c": [],
        "d": {"nested": None, "keep": 1},
    }
    assert omit_empty(payload) == {"d": {"keep": 1}}


def test_omit_empty_preserves_falsy_values():
    payload = {"flag": False, "count": 0, "label": ""}
    assert omit_empty(payload) == payload


def test_omit_empty_preserves_empty_items_list():
    payload = {"data": {"items": [], "meta": {}}}
    assert omit_empty(payload) == {"data": {"items": []}}


def test_omit_empty_recurses_nested_meta():
    payload = {
        "data": {
            "items": [1],
            "meta": {
                "filters": {"status": "active"},
                "aggregations": {},
                "summary": None,
            },
        }
    }
    assert omit_empty(payload) == {
        "data": {
            "items": [1],
            "meta": {"filters": {"status": "active"}},
        }
    }


def test_success_response_envelope():
    response = success_response(data={"id": 1}, message="Done.")
    assert response.status_code == status.HTTP_200_OK
    assert response.data == {
        "success": True,
        "message": "Done.",
        "data": {"id": 1},
    }


def test_success_response_created_status():
    response = success_response(
        data={"id": 1},
        message="Created.",
        http_status=status.HTTP_201_CREATED,
    )
    assert response.status_code == status.HTTP_201_CREATED


def test_list_success_response_with_pagination_and_meta():
    response = list_success_response(
        items=[{"id": 1}],
        pagination={
            "next_cursor": "abc",
            "has_next": True,
            "has_previous": False,
            "page_size": 10,
        },
        meta={"filters": {"q": "test"}},
        message="Listed.",
    )
    assert response.data["success"] is True
    assert response.data["data"]["items"] == [{"id": 1}]
    assert response.data["data"]["pagination"]["next_cursor"] == "abc"
    assert response.data["data"]["meta"]["filters"] == {"q": "test"}


def test_list_success_response_omits_empty_meta():
    response = list_success_response(items=[], meta={})
    assert "meta" not in response.data["data"]
    assert response.data["data"]["items"] == []


def test_error_response_with_field_errors():
    response = error_response(
        message="Validation failed.",
        error_code="VALIDATION_ERROR",
        errors={"email": ["This field is required."]},
        http_status=status.HTTP_400_BAD_REQUEST,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {
        "success": False,
        "message": "Validation failed.",
        "error_code": "VALIDATION_ERROR",
        "errors": {"email": ["This field is required."]},
    }


def test_error_response_without_errors_omits_errors_key():
    response = error_response(
        message="Insufficient stock available.",
        error_code="INSUFFICIENT_STOCK",
        errors=None,
        http_status=status.HTTP_409_CONFLICT,
    )
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "errors" not in response.data
