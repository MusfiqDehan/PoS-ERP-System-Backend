from __future__ import annotations

import logging
import math
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.views import exception_handler as drf_exception_handler

from shared.responses.builders import error_response
from shared.responses.error_codes import ErrorCode, get_default_message
from shared.responses.exceptions import DomainAPIException

logger = logging.getLogger(__name__)

EXCEPTION_CODE_MAP: dict[type[APIException], ErrorCode] = {
    NotAuthenticated: ErrorCode.AUTHENTICATION_REQUIRED,
    AuthenticationFailed: ErrorCode.INVALID_CREDENTIALS,
    PermissionDenied: ErrorCode.PERMISSION_DENIED,
    NotFound: ErrorCode.NOT_FOUND,
    ValidationError: ErrorCode.VALIDATION_ERROR,
    Throttled: ErrorCode.RATE_LIMIT_EXCEEDED,
}


def _listify(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return [str(value)]


def _normalize_errors(detail: Any) -> dict[str, list[str]] | list[str] | None:
    if isinstance(detail, dict):
        return {str(key): _listify(value) for key, value in detail.items()}
    if isinstance(detail, list):
        return {"non_field_errors": _listify(detail)}
    if detail is None:
        return None
    return {"non_field_errors": _listify(detail)}


def _resolve_error_code(exc: Exception) -> str:
    if isinstance(exc, DomainAPIException):
        return exc.error_code

    mapped = EXCEPTION_CODE_MAP.get(type(exc))
    if mapped is not None:
        return str(mapped)

    if isinstance(exc, APIException) and exc.get_codes() == "token_not_valid":
        return str(ErrorCode.TOKEN_EXPIRED)

    return str(ErrorCode.INTERNAL_SERVER_ERROR)


def _resolve_message(exc: Exception, error_code: str) -> str:
    if isinstance(exc, DomainAPIException):
        return exc.user_message
    return get_default_message(error_code)


def _resolve_status_code(exc: Exception) -> int:
    if isinstance(exc, DomainAPIException):
        return exc.status_code
    if isinstance(exc, APIException):
        return exc.status_code
    if isinstance(exc, DjangoValidationError):
        return status.HTTP_400_BAD_REQUEST
    return status.HTTP_500_INTERNAL_SERVER_ERROR


def _resolve_errors(exc: Exception) -> dict[str, list[str]] | list[str] | None:
    if isinstance(exc, DomainAPIException) and exc.errors is not None:
        normalized = _normalize_errors(exc.errors)
        return normalized

    if isinstance(exc, ValidationError):
        return _normalize_errors(exc.detail)

    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            return _normalize_errors(exc.message_dict)
        return _normalize_errors(exc.messages)

    return None


def custom_exception_handler(exc: Exception, context: dict[str, Any]):
    if isinstance(exc, DjangoValidationError) and not isinstance(exc, ValidationError):
        error_code = str(ErrorCode.VALIDATION_ERROR)
        response = error_response(
            message=get_default_message(error_code),
            error_code=error_code,
            errors=_resolve_errors(exc),
            http_status=status.HTTP_400_BAD_REQUEST,
        )
        return response

    response = drf_exception_handler(exc, context)

    if response is None:
        logger.exception("Unhandled exception during API request", exc_info=exc)
        return error_response(
            message=get_default_message(ErrorCode.INTERNAL_SERVER_ERROR),
            error_code=str(ErrorCode.INTERNAL_SERVER_ERROR),
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    error_code = _resolve_error_code(exc)
    message = _resolve_message(exc, error_code)
    errors = _resolve_errors(exc)
    http_status = _resolve_status_code(exc)

    built = error_response(
        message=message,
        error_code=error_code,
        errors=errors,
        http_status=http_status,
    )

    if isinstance(exc, Throttled):
        wait = exc.wait
        retry_after = math.ceil(wait) if wait is not None else 1
        built["Retry-After"] = str(retry_after)

    return built
