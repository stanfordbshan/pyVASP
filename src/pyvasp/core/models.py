"""Core domain models for VASP OUTCAR post-processing."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EnergyPoint:
    """Energy sample extracted from one ionic step."""

    ionic_step: int
    total_energy_ev: float


@dataclass(frozen=True)
class OutcarSummary:
    """Transport-agnostic summary for common OUTCAR diagnostics."""

    source_path: str
    system_name: str | None
    nions: int | None
    ionic_steps: int
    electronic_iterations: int
    final_total_energy_ev: float | None
    final_fermi_energy_ev: float | None
    max_force_ev_per_a: float | None
    energy_history: tuple[EnergyPoint, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
