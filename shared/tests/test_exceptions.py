from rest_framework import status

from shared.responses.error_codes import ErrorCode
from shared.responses.exceptions import DomainAPIException, InvalidCursorError


def test_domain_api_exception_defaults():
    exc = DomainAPIException()
    assert exc.error_code == str(ErrorCode.INTERNAL_SERVER_ERROR)
    assert exc.status_code == 400
    assert exc.user_message
    assert exc.errors is None


def test_domain_api_exception_custom_fields():
    exc = DomainAPIException(
        error_code=ErrorCode.INSUFFICIENT_STOCK,
        user_message="Insufficient stock available.",
        errors=None,
        status_code=status.HTTP_409_CONFLICT,
    )
    assert exc.error_code == str(ErrorCode.INSUFFICIENT_STOCK)
    assert exc.user_message == "Insufficient stock available."
    assert exc.status_code == status.HTTP_409_CONFLICT


def test_domain_api_exception_with_field_errors():
    errors = {"quantity": ["Must be greater than zero."]}
    exc = DomainAPIException(
        error_code=ErrorCode.VALIDATION_ERROR,
        errors=errors,
    )
    assert exc.errors == errors


def test_invalid_cursor_error():
    exc = InvalidCursorError()
    assert exc.error_code == str(ErrorCode.INVALID_CURSOR)
    assert exc.status_code == status.HTTP_400_BAD_REQUEST
