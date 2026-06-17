import pytest

from shared.responses.error_codes import (
    DEFAULT_MESSAGES,
    ErrorCode,
    get_default_message,
)

REQUIRED_CODES = [
    ErrorCode.AUTHENTICATION_REQUIRED,
    ErrorCode.INVALID_CREDENTIALS,
    ErrorCode.TOKEN_EXPIRED,
    ErrorCode.PERMISSION_DENIED,
    ErrorCode.TENANT_NOT_FOUND,
    ErrorCode.TENANT_SUSPENDED,
    ErrorCode.PRODUCT_NOT_FOUND,
    ErrorCode.PRODUCT_ALREADY_EXISTS,
    ErrorCode.CUSTOMER_NOT_FOUND,
    ErrorCode.INSUFFICIENT_STOCK,
    ErrorCode.NEGATIVE_STOCK_NOT_ALLOWED,
    ErrorCode.SALE_NOT_FOUND,
    ErrorCode.SALE_ALREADY_CANCELLED,
    ErrorCode.PAYMENT_FAILED,
    ErrorCode.VALIDATION_ERROR,
    ErrorCode.INTERNAL_SERVER_ERROR,
]


@pytest.mark.parametrize("code", REQUIRED_CODES)
def test_error_code_has_default_message(code):
    assert code in DEFAULT_MESSAGES
    assert DEFAULT_MESSAGES[code]
    assert get_default_message(code) == DEFAULT_MESSAGES[code]


def test_unknown_error_code_falls_back_to_internal_server_error():
    assert (
        get_default_message("UNKNOWN_CODE")
        == DEFAULT_MESSAGES[ErrorCode.INTERNAL_SERVER_ERROR]
    )
