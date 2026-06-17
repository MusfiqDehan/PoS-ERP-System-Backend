from enum import StrEnum


class ErrorCode(StrEnum):
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"

    PERMISSION_DENIED = "PERMISSION_DENIED"

    TENANT_NOT_FOUND = "TENANT_NOT_FOUND"
    TENANT_SUSPENDED = "TENANT_SUSPENDED"

    PRODUCT_NOT_FOUND = "PRODUCT_NOT_FOUND"
    PRODUCT_ALREADY_EXISTS = "PRODUCT_ALREADY_EXISTS"

    CUSTOMER_NOT_FOUND = "CUSTOMER_NOT_FOUND"

    INSUFFICIENT_STOCK = "INSUFFICIENT_STOCK"
    NEGATIVE_STOCK_NOT_ALLOWED = "NEGATIVE_STOCK_NOT_ALLOWED"

    SALE_NOT_FOUND = "SALE_NOT_FOUND"
    SALE_ALREADY_CANCELLED = "SALE_ALREADY_CANCELLED"

    PAYMENT_FAILED = "PAYMENT_FAILED"

    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INVALID_CURSOR = "INVALID_CURSOR"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"


DEFAULT_MESSAGES: dict[str, str] = {
    ErrorCode.AUTHENTICATION_REQUIRED: "Authentication required.",
    ErrorCode.INVALID_CREDENTIALS: "Invalid credentials.",
    ErrorCode.TOKEN_EXPIRED: "Your session has expired. Please sign in again.",
    ErrorCode.PERMISSION_DENIED: "You do not have permission to perform this action.",
    ErrorCode.TENANT_NOT_FOUND: "The requested tenant was not found.",
    ErrorCode.TENANT_SUSPENDED: "This tenant account is suspended.",
    ErrorCode.PRODUCT_NOT_FOUND: "The requested product was not found.",
    ErrorCode.PRODUCT_ALREADY_EXISTS: "A product with these details already exists.",
    ErrorCode.CUSTOMER_NOT_FOUND: "The requested customer was not found.",
    ErrorCode.INSUFFICIENT_STOCK: "Insufficient stock available.",
    ErrorCode.NEGATIVE_STOCK_NOT_ALLOWED: "Stock quantity cannot be negative.",
    ErrorCode.SALE_NOT_FOUND: "The requested sale was not found.",
    ErrorCode.SALE_ALREADY_CANCELLED: "This sale has already been cancelled.",
    ErrorCode.PAYMENT_FAILED: "Payment could not be processed.",
    ErrorCode.VALIDATION_ERROR: "Validation failed.",
    ErrorCode.NOT_FOUND: "The requested resource was not found.",
    ErrorCode.RATE_LIMIT_EXCEEDED: "Too many requests. Please try again later.",
    ErrorCode.INVALID_CURSOR: "Invalid pagination cursor.",
    ErrorCode.INTERNAL_SERVER_ERROR: "An unexpected error occurred.",
}


def get_default_message(error_code: str | ErrorCode) -> str:
    return DEFAULT_MESSAGES.get(
        str(error_code), DEFAULT_MESSAGES[ErrorCode.INTERNAL_SERVER_ERROR]
    )
