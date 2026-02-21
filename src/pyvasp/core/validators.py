"""Validation helpers shared by API, GUI, and CLI adapters."""

from __future__ import annotations

from pathlib import Path

from pyvasp.core.errors import ErrorCode, ValidationError


def validate_outcar_path(path: str) -> Path:
    """Validate that OUTCAR input points to an existing readable file."""

    return validate_file_path(path, field_name="outcar_path", label="OUTCAR")


def validate_file_path(path: str, *, field_name: str, label: str) -> Path:
    """Validate that a named file path points to an existing regular file."""

    if not isinstance(path, str) or not path.strip():
        raise ValidationError(
            f"{field_name} must be a non-empty string",
            code=ErrorCode.VALIDATION_ERROR,
            details={"field": field_name},
        )

    candidate = Path(path).expanduser()
    if not candidate.exists():
        raise ValidationError(
            f"{label} file does not exist: {candidate}",
            code=ErrorCode.FILE_NOT_FOUND,
            details={"field": field_name, "path": str(candidate)},
        )
    if not candidate.is_file():
        raise ValidationError(
            f"{label} path is not a file: {candidate}",
            code=ErrorCode.FILE_NOT_FILE,
            details={"field": field_name, "path": str(candidate)},
        )

    return candidate.resolve()


def validate_directory_path(path: str, *, field_name: str, label: str) -> Path:
    """Validate that a named directory path points to an existing directory."""

    if not isinstance(path, str) or not path.strip():
        raise ValidationError(
            f"{field_name} must be a non-empty string",
            code=ErrorCode.VALIDATION_ERROR,
            details={"field": field_name},
        )

    candidate = Path(path).expanduser()
    if not candidate.exists():
        raise ValidationError(
            f"{label} does not exist: {candidate}",
            code=ErrorCode.FILE_NOT_FOUND,
            details={"field": field_name, "path": str(candidate)},
        )
    if not candidate.is_dir():
        raise ValidationError(
            f"{label} is not a directory: {candidate}",
            code=ErrorCode.VALIDATION_ERROR,
            details={"field": field_name, "path": str(candidate)},
        )

    return candidate.resolve()
