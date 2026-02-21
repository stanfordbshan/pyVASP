from __future__ import annotations

from pathlib import Path

import pytest

from pyvasp.core.errors import AppError, ErrorCode, ParseError, ValidationError, normalize_error
from pyvasp.core.validators import validate_file_path


def test_app_error_to_mapping_includes_optional_details() -> None:
    error = AppError(
        code=ErrorCode.VALIDATION_ERROR,
        message="invalid payload",
        details={"field": "outcar_path"},
    )
    mapped = error.to_mapping()

    assert mapped["code"] == "VALIDATION_ERROR"
    assert mapped["message"] == "invalid payload"
    assert mapped["details"]["field"] == "outcar_path"


def test_normalize_error_from_pyvasp_error_preserves_code() -> None:
    normalized = normalize_error(ParseError("parse failed"))
    assert normalized.code == ErrorCode.PARSE_ERROR
    assert normalized.message == "parse failed"


def test_normalize_error_from_oserror_maps_to_io_error() -> None:
    normalized = normalize_error(OSError("disk unavailable"))
    assert normalized.code == ErrorCode.IO_ERROR
    assert normalized.message == "disk unavailable"


def test_validate_file_path_rejects_empty_input() -> None:
    with pytest.raises(ValidationError) as exc_info:
        validate_file_path("", field_name="outcar_path", label="OUTCAR")

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
    assert exc_info.value.details == {"field": "outcar_path"}


def test_validate_file_path_returns_file_not_found(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.OUTCAR"

    with pytest.raises(ValidationError) as exc_info:
        validate_file_path(str(missing_path), field_name="outcar_path", label="OUTCAR")

    assert exc_info.value.code == ErrorCode.FILE_NOT_FOUND
    assert exc_info.value.details == {"field": "outcar_path", "path": str(missing_path)}


def test_validate_file_path_returns_file_not_file(tmp_path: Path) -> None:
    directory = tmp_path / "folder"
    directory.mkdir()

    with pytest.raises(ValidationError) as exc_info:
        validate_file_path(str(directory), field_name="outcar_path", label="OUTCAR")

    assert exc_info.value.code == ErrorCode.FILE_NOT_FILE
    assert exc_info.value.details == {"field": "outcar_path", "path": str(directory)}
