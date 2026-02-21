"""Core domain models for VASP post-processing and input generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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


@dataclass(frozen=True)
class ConvergenceProfilePoint:
    """Per-step convergence profile point for chart-friendly visualization."""

    ionic_step: int
    total_energy_ev: float
    delta_energy_ev: float | None
    relative_energy_ev: float


@dataclass(frozen=True)
class ConvergenceProfile:
    """Energy convergence profile derived from OUTCAR history."""

    points: tuple[ConvergenceProfilePoint, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class OutcarIonicSeriesPoint:
    """Per-step OUTCAR series point for multi-metric visualization."""

    ionic_step: int
    total_energy_ev: float | None
    delta_energy_ev: float | None
    relative_energy_ev: float | None
    max_force_ev_per_a: float | None
    external_pressure_kb: float | None
    fermi_energy_ev: float | None


@dataclass(frozen=True)
class OutcarIonicSeries:
    """Chart-ready ionic-step series composed from OUTCAR step histories."""

    source_path: str
    points: tuple[OutcarIonicSeriesPoint, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class StructureAtom:
    """Atomic site in fractional coordinates."""

    element: str
    frac_coords: tuple[float, float, float]


@dataclass(frozen=True)
class RelaxStructure:
    """Minimal structure representation for POSCAR generation."""

    comment: str
    lattice_vectors: tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]
    atoms: tuple[StructureAtom, ...]


@dataclass(frozen=True)
class RelaxInputSpec:
    """Canonical VASP relaxation input specification."""

    structure: RelaxStructure
    kmesh: tuple[int, int, int]
    gamma_centered: bool
    encut: int
    ediff: float
    ediffg: float
    ismear: int
    sigma: float
    ibrion: int
    isif: int
    nsw: int
    ispin: int
    magmom: str | None
    incar_overrides: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GeneratedInputBundle:
    """Rendered VASP input files for a workflow."""

    system_name: str
    n_atoms: int
    incar_text: str
    kpoints_text: str
    poscar_text: str
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class BandGapChannel:
    """Band-gap details for a single spin channel."""

    spin: str
    gap_ev: float
    vbm_ev: float
    cbm_ev: float
    is_direct: bool
    kpoint_index_vbm: int
    kpoint_index_cbm: int
    is_metal: bool


@dataclass(frozen=True)
class BandGapSummary:
    """Fundamental band-gap summary derived from EIGENVAL."""

    is_spin_polarized: bool
    is_metal: bool
    fundamental_gap_ev: float
    vbm_ev: float
    cbm_ev: float
    is_direct: bool
    channel: str
    channels: tuple[BandGapChannel, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DosMetadata:
    """Total DOS metadata derived from DOSCAR."""

    energy_min_ev: float
    energy_max_ev: float
    nedos: int
    efermi_ev: float
    is_spin_polarized: bool
    has_integrated_dos: bool
    energy_step_ev: float | None
    total_dos_at_fermi: float | None


@dataclass(frozen=True)
class DosProfilePoint:
    """One total-DOS sample used for plotting against energy."""

    index: int
    energy_ev: float
    energy_relative_ev: float
    dos_total: float


@dataclass(frozen=True)
class DosProfile:
    """Chart-ready DOS profile derived from DOSCAR total DOS rows."""

    source_path: str
    efermi_ev: float
    energy_window_ev: float
    points: tuple[DosProfilePoint, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ElectronicStructureMetadata:
    """Combined electronic metadata extracted from standard VASP outputs."""

    eigenval_path: str | None
    doscar_path: str | None
    band_gap: BandGapSummary | None
    dos_metadata: DosMetadata | None
    warnings: tuple[str, ...] = field(default_factory=tuple)
