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


@dataclass(frozen=True)
class StressTensor:
    """Final stress tensor reported by OUTCAR in kB."""

    xx_kb: float
    yy_kb: float
    zz_kb: float
    xy_kb: float
    yz_kb: float
    zx_kb: float


@dataclass(frozen=True)
class MagnetizationSummary:
    """Final ionic magnetic moments (typically from magnetization (z) table)."""

    axis: str
    total_moment_mu_b: float | None
    site_moments_mu_b: tuple[float, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class OutcarObservables:
    """OUTCAR observables beyond the scalar summary used by diagnostics."""

    source_path: str
    summary: OutcarSummary
    external_pressure_kb: float | None
    stress_tensor_kb: StressTensor | None
    magnetization: MagnetizationSummary | None
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ConvergenceReport:
    """Convergence assessment using user-specified thresholds."""

    energy_tolerance_ev: float
    force_tolerance_ev_per_a: float
    final_energy_change_ev: float | None
    is_energy_converged: bool | None
    is_force_converged: bool | None
    is_converged: bool


@dataclass(frozen=True)
class OutcarDiagnostics:
    """Composite diagnostic view combining observables and convergence."""

    source_path: str
    summary: OutcarSummary
    external_pressure_kb: float | None
    stress_tensor_kb: StressTensor | None
    magnetization: MagnetizationSummary | None
    convergence: ConvergenceReport
    warnings: tuple[str, ...] = field(default_factory=tuple)
