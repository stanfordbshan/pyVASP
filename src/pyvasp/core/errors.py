"""Domain-level error taxonomy and normalization utilities."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    """Stable machine-readable error codes across adapters."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_NOT_FILE = "FILE_NOT_FILE"
    PARSE_ERROR = "PARSE_ERROR"
    IO_ERROR = "IO_ERROR"
    UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass(frozen=True)
class AppError:
    """Transport-neutral structured error payload."""

    code: ErrorCode
    message: str
    details: dict[str, Any] | None = None

    def to_mapping(self) -> dict[str, Any]:
        mapped: dict[str, Any] = {
            "code": self.code.value,
            "message": self.message,
        }
        if self.details:
            mapped["details"] = self.details
        return mapped


class PyVaspError(Exception):
    """Base exception for pyVASP with structured error metadata."""

    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = details

    def to_app_error(self) -> AppError:
        return AppError(code=self.code, message=str(self), details=self.details)


class ValidationError(PyVaspError):
    """Raised when incoming payload data is invalid."""

    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode = ErrorCode.VALIDATION_ERROR,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code=code, details=details)


class ParseError(PyVaspError):
    """Raised when a VASP output file cannot be parsed reliably."""

    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode = ErrorCode.PARSE_ERROR,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code=code, details=details)


def normalize_error(error: AppError | Exception | str) -> AppError:
    """Normalize arbitrary failures into a stable structured AppError."""

    if isinstance(error, AppError):
        return error

    if isinstance(error, PyVaspError):
        return error.to_app_error()

    if isinstance(error, OSError):
        return AppError(code=ErrorCode.IO_ERROR, message=str(error))

    if isinstance(error, Exception):
        message = str(error) or error.__class__.__name__
        return AppError(code=ErrorCode.INTERNAL_ERROR, message=message)

    return AppError(code=ErrorCode.INTERNAL_ERROR, message=str(error))
