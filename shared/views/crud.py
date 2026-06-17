"""Reusable base view for standard CRUD + action dispatch.

Usage::

    from shared.views import ModelCRUDView

    class ProductView(ModelCRUDView):
        queryset = Product.objects.all()
        serializer_class = ProductSerializer
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, ClassVar, cast

from django.db.models import QuerySet
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer

from shared.pagination import CursorPagination
from shared.responses import error_response, list_success_response, success_response
from shared.responses.error_codes import ErrorCode, get_default_message

ActionHandler = Callable[["ModelCRUDView", Request, Any], Response]


class ModelCRUDView(GenericAPIView):
    """
    Single view handling standard CRUD + resource-specific actions.

    All responses use the global success/error envelope.
    """

    queryset: ClassVar[QuerySet[Any]]
    serializer_class: ClassVar[type[BaseSerializer[Any]]]
    actions: ClassVar[dict[str, ActionHandler]] = {}
    pagination_class: ClassVar[type[CursorPagination] | None] = CursorPagination

    def get_queryset(self) -> QuerySet[Any]:
        return cast(QuerySet[Any], super().get_queryset())

    def get_serializer(self, *args: Any, **kwargs: Any) -> BaseSerializer[Any]:
        return cast(BaseSerializer[Any], super().get_serializer(*args, **kwargs))

    def get_object(self) -> Any:
        return cast(Any, super().get_object())

    def get(self, request: Request, pk: Any | None = None, **kwargs: Any) -> Response:
        if pk is not None:
            return self._retrieve(pk)
        return self._list(request)

    def post(self, request: Request, pk: Any | None = None, **kwargs: Any) -> Response:
        if pk is not None:
            action = cast(str | None, request.query_params.get("action"))
            if action:
                return self._handle_action(pk, action, request)
            return self._update(pk, request, partial=False)
        return self._create(request)

    def put(self, request: Request, pk: Any, **kwargs: Any) -> Response:
        return self._update(pk, request, partial=False)

    def patch(self, request: Request, pk: Any, **kwargs: Any) -> Response:
        action = cast(str | None, request.query_params.get("action"))
        if action:
            return self._handle_action(pk, action, request)
        return self._update(pk, request, partial=True)

    def delete(self, request: Request, pk: Any, **kwargs: Any) -> Response:
        return self._destroy(pk)

    def get_success_message(self, action: str) -> str:
        messages = {
            "list": "Resources retrieved successfully.",
            "create": "Resource created successfully.",
            "retrieve": "Resource retrieved successfully.",
            "update": "Resource updated successfully.",
        }
        return messages.get(action, "Operation successful.")

    def get_list_meta(self, request: Request, queryset: QuerySet[Any]) -> dict[str, Any]:
        return {}

    def _list(self, request: Request) -> Response:
        queryset = self.filter_queryset(self.get_queryset())
        meta = self.get_list_meta(request, queryset)
        message = self.get_success_message("list")
        pagination_key = "pagination_class"
        pagination_cls: Any = getattr(type(self), pagination_key, None)

        if pagination_cls is None:
            serializer = self.get_serializer(queryset, many=True)
            return list_success_response(
                items=cast(list[Any], serializer.data),
                meta=meta or None,
                message=message,
            )

        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        paginator = self.paginator
        assert paginator is not None
        return paginator.get_paginated_response(
            cast(list[Any], serializer.data), meta=meta, message=message
        )

    def _create(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return success_response(
            data=self.get_serializer(instance).data,
            message=self.get_success_message("create"),
            http_status=status.HTTP_201_CREATED,
        )

    def _retrieve(self, pk: Any) -> Response:
        instance = self.get_object()
        return success_response(
            data=self.get_serializer(instance).data,
            message=self.get_success_message("retrieve"),
        )

    def _update(self, pk: Any, request: Request, partial: bool) -> Response:
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return success_response(
            data=self.get_serializer(instance).data,
            message=self.get_success_message("update"),
        )

    def _destroy(self, pk: Any) -> Response:
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _handle_action(self, pk: Any, action: str, request: Request) -> Response:
        handler = self.actions.get(action)
        if not handler:
            return error_response(
                message=get_default_message(ErrorCode.VALIDATION_ERROR),
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        return handler(self, request, pk)
