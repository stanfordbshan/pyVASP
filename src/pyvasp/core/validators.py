"""Validation helpers shared by API, GUI, and CLI adapters."""

from __future__ import annotations

from pathlib import Path

from pyvasp.core.errors import ValidationError


def validate_outcar_path(path: str) -> Path:
    """Validate that OUTCAR input points to an existing readable file."""

    if not isinstance(path, str) or not path.strip():
        raise ValidationError("outcar_path must be a non-empty string")

    candidate = Path(path).expanduser()
    if not candidate.exists():
        raise ValidationError(f"OUTCAR file does not exist: {candidate}")
    if not candidate.is_file():
        raise ValidationError(f"OUTCAR path is not a file: {candidate}")

    return candidate.resolve()
