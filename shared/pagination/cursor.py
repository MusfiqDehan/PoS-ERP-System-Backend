from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from rest_framework.exceptions import NotFound
from rest_framework.pagination import CursorPagination as DRFCursorPagination

from shared.responses import list_success_response
from shared.responses.exceptions import InvalidCursorError


class CursorPagination(DRFCursorPagination):
    """Cursor paginator that emits the standard list success envelope."""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100
    ordering = "-pk"
    cursor_query_param = "cursor"

    def decode_cursor(self, request):
        try:
            return super().decode_cursor(request)
        except NotFound as exc:
            if str(exc.detail) == str(self.invalid_cursor_message):
                raise InvalidCursorError() from exc
            raise

    def _extract_cursor(self, link: str | None) -> str | None:
        if not link:
            return None
        query = parse_qs(urlparse(link).query)
        values = query.get(self.cursor_query_param, [])
        return values[0] if values else None

    def get_pagination_metadata(self) -> dict:
        metadata = {
            "has_next": self.has_next,
            "has_previous": self.has_previous,
            "page_size": self.get_page_size(self.request),
        }
        next_cursor = self._extract_cursor(self.get_next_link())
        previous_cursor = self._extract_cursor(self.get_previous_link())
        if next_cursor is not None:
            metadata["next_cursor"] = next_cursor
        if previous_cursor is not None:
            metadata["previous_cursor"] = previous_cursor
        return metadata

    def get_paginated_response(
        self, data, *, meta=None, message="Resources retrieved successfully."
    ):
        return list_success_response(
            items=data,
            pagination=self.get_pagination_metadata(),
            meta=meta,
            message=message,
        )
