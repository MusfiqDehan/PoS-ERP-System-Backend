from rest_framework.exceptions import APIException

from shared.responses.error_codes import ErrorCode, get_default_message


class DomainAPIException(APIException):
    """Domain-level API error with a machine-readable code and user-safe message."""

    status_code = 400
    default_code = ErrorCode.INTERNAL_SERVER_ERROR
    default_detail = get_default_message(ErrorCode.INTERNAL_SERVER_ERROR)

    def __init__(
        self,
        *,
        error_code: str | ErrorCode | None = None,
        user_message: str | None = None,
        errors: dict | list | None = None,
        status_code: int | None = None,
        detail: str | None = None,
    ):
        self.error_code = str(error_code or self.default_code)
        self.user_message = user_message or get_default_message(self.error_code)
        self.errors = errors
        if status_code is not None:
            self.status_code = status_code
        super().__init__(detail=detail or self.user_message, code=self.error_code)


class InvalidCursorError(DomainAPIException):
    status_code = 400
    default_code = ErrorCode.INVALID_CURSOR
    default_detail = get_default_message(ErrorCode.INVALID_CURSOR)
