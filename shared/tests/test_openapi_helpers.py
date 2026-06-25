"""Unit tests for shared OpenAPI helper contracts."""

from __future__ import annotations

import inspect

import pytest

from shared.openapi import document_api_view, document_crud_view


def test_document_api_view_requires_description_parameter():
    signature = inspect.signature(document_api_view)
    assert "description" in signature.parameters
    assert signature.parameters["description"].default is inspect.Parameter.empty


def test_document_crud_view_operations_must_include_description():
    from unittest.mock import MagicMock

    from shared.views import ModelCRUDView

    class DummySerializer:
        pass

    with pytest.raises(KeyError):
        document_crud_view(
            tags=["Test"],
            operations={"GET": {"summary": "List items"}},
        )(
            type(
                "_BrokenView",
                (ModelCRUDView,),
                {
                    "queryset": MagicMock(),
                    "serializer_class": DummySerializer,
                    "pagination_class": None,
                },
            )
        )
