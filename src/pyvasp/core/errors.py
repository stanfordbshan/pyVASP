"""Domain-level errors and validation exceptions."""

from __future__ import annotations


class PyVaspError(Exception):
    """Base exception for pyVASP."""


class ValidationError(PyVaspError):
    """Raised when incoming payload data is invalid."""


class ParseError(PyVaspError):
    """Raised when an OUTCAR file cannot be parsed reliably."""
