from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import (
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.views import exception_handler as drf_exception_handler

from shared.responses.error_codes import ErrorCode
from shared.responses.exceptions import DomainAPIException
from shared.responses.handler import custom_exception_handler


def _handle(exc):
    return custom_exception_handler(exc, {"view": None})


def test_validation_error_maps_to_validation_error_code():
    exc = ValidationError({"email": ["This field is required."]})
    response = _handle(exc)
    assert response.status_code == 400
    assert response.data["success"] is False
    assert response.data["error_code"] == str(ErrorCode.VALIDATION_ERROR)
    assert response.data["errors"]["email"] == ["This field is required."]


def test_not_authenticated_maps_to_401():
    response = _handle(NotAuthenticated())
    assert response.status_code == 401
    assert response.data["error_code"] == str(ErrorCode.AUTHENTICATION_REQUIRED)


def test_permission_denied_maps_to_403():
    response = _handle(PermissionDenied())
    assert response.status_code == 403
    assert response.data["error_code"] == str(ErrorCode.PERMISSION_DENIED)


def test_not_found_maps_to_404():
    response = _handle(NotFound())
    assert response.status_code == 404
    assert response.data["error_code"] == str(ErrorCode.NOT_FOUND)


def test_domain_api_exception_uses_custom_code_and_status():
    exc = DomainAPIException(
        error_code=ErrorCode.INSUFFICIENT_STOCK,
        user_message="Insufficient stock available.",
        status_code=409,
    )
    response = _handle(exc)
    assert response.status_code == 409
    assert response.data["error_code"] == str(ErrorCode.INSUFFICIENT_STOCK)
    assert response.data["message"] == "Insufficient stock available."


def test_throttled_includes_retry_after_header():
    exc = Throttled(wait=2.2)
    response = _handle(exc)
    assert response.status_code == 429
    assert response.data["error_code"] == str(ErrorCode.RATE_LIMIT_EXCEEDED)
    assert response["Retry-After"] == "3"


def test_unhandled_exception_returns_500_without_leaking_details():
    response = _handle(RuntimeError("database password leaked"))
    assert response.status_code == 500
    assert response.data["error_code"] == str(ErrorCode.INTERNAL_SERVER_ERROR)
    assert "password" not in response.data["message"]
    assert "password" not in str(response.data)


def test_django_validation_error_maps_to_envelope():
    exc = DjangoValidationError({"name": ["Required"]})
    response = _handle(exc)
    assert response.status_code == 400
    assert response.data["error_code"] == str(ErrorCode.VALIDATION_ERROR)
    assert response.data["errors"]["name"] == ["Required"]


def test_throttle_exception_handler_is_global_handler():
    from shared.api import throttle_exception_handler

    exc = ValidationError({"field": ["bad"]})
    assert throttle_exception_handler(exc, {}) is not None
    assert drf_exception_handler(exc, {}) is not None
