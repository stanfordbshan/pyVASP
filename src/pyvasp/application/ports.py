"""Application-layer ports (interfaces) for method modules."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pyvasp.core.models import (
    DosProfile,
    ElectronicStructureMetadata,
    GeneratedInputBundle,
    OutcarIonicSeries,
    OutcarObservables,
    OutcarSummary,
    RelaxInputSpec,
)


class OutcarSummaryReader(Protocol):
    """Port for method modules that can parse an OUTCAR file."""

    def parse_file(self, outcar_path: Path) -> OutcarSummary:
        """Parse OUTCAR and produce the domain summary model."""


class OutcarObservablesReader(Protocol):
    """Port for method modules that can parse OUTCAR diagnostics observables."""

    def parse_observables_file(self, outcar_path: Path) -> OutcarObservables:
        """Parse OUTCAR and produce diagnostics observables."""


class OutcarIonicSeriesReader(Protocol):
    """Port for method modules that can parse per-step OUTCAR series data."""

    def parse_ionic_series_file(self, outcar_path: Path) -> OutcarIonicSeries:
        """Parse OUTCAR and produce per-step series metrics."""


class RelaxInputBuilder(Protocol):
    """Port for method modules that can render VASP relaxation inputs."""

    def generate_relax_input(self, spec: RelaxInputSpec) -> GeneratedInputBundle:
        """Render INCAR/KPOINTS/POSCAR bundle for the given spec."""


class ElectronicMetadataReader(Protocol):
    """Port for method modules that parse EIGENVAL/DOSCAR metadata."""

    def parse_metadata(
        self,
        *,
        eigenval_path: Path | None,
        doscar_path: Path | None,
    ) -> ElectronicStructureMetadata:
        """Parse electronic-structure metadata from standard VASP outputs."""


class DosProfileReader(Protocol):
    """Port for method modules that can parse chart-ready DOS profile data."""

    def parse_dos_profile(
        self,
        *,
        doscar_path: Path,
        energy_window_ev: float,
        max_points: int,
    ) -> DosProfile:
        """Parse DOSCAR and return a filtered total-DOS profile."""
