"""Application-layer ports (interfaces) for method modules."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pyvasp.core.models import OutcarSummary


class OutcarSummaryReader(Protocol):
    """Port for method modules that can parse an OUTCAR file."""

    def parse_file(self, outcar_path: Path) -> OutcarSummary:
        """Parse OUTCAR and produce the domain summary model."""
