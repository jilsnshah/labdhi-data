"""Domain level exceptions mapped to HTTP responses in app.main."""

from typing import Any


class AppError(Exception):
    """Base class for expected, user-facing errors."""

    status_code = 400
    code = "app_error"

    def __init__(
        self, message: str, *, field: str | None = None, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.field = field
        self.details = details or {}

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.field:
            payload["field"] = self.field
        if self.details:
            payload["details"] = self.details
        return payload


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class AuthError(AppError):
    status_code = 401
    code = "unauthorized"


class PermissionError_(AppError):
    status_code = 403
    code = "forbidden"
