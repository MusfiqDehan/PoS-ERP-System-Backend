"""
Standard API response envelope builders.

Success (single resource)::

    {"success": true, "message": "...", "data": {...}}

Success (list)::

    {
        "success": true,
        "message": "...",
        "data": {
            "items": [...],
            "pagination": {...},
            "meta": {...}
        }
    }

Error::

    {"success": false, "message": "...", "error_code": "...", "errors": {...}}
"""

from shared.responses.builders import (
    error_response,
    list_success_response,
    omit_empty,
    success_response,
)
from shared.responses.error_codes import DEFAULT_MESSAGES, ErrorCode
from shared.responses.exceptions import DomainAPIException, InvalidCursorError
from shared.responses.handler import custom_exception_handler

__all__ = [
    "DEFAULT_MESSAGES",
    "DomainAPIException",
    "ErrorCode",
    "InvalidCursorError",
    "custom_exception_handler",
    "error_response",
    "list_success_response",
    "omit_empty",
    "success_response",
]
