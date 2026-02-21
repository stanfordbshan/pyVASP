"""Application-independent result wrapper used across layers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from pyvasp.core.errors import AppError, normalize_error

T = TypeVar("T")


@dataclass(frozen=True)
class AppResult(Generic[T]):
    """Typed result object to avoid transport-specific exception contracts."""

    ok: bool
    value: T | None = None
    error: AppError | None = None

    @classmethod
    def success(cls, value: T) -> "AppResult[T]":
        return cls(ok=True, value=value)

    @classmethod
    def failure(cls, error: AppError | Exception | str) -> "AppResult[T]":
        return cls(ok=False, error=normalize_error(error))
