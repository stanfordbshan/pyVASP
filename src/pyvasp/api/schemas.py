"""HTTP-facing request/response schemas for pyVASP API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SummaryRequestSchema(BaseModel):
    """Request payload for OUTCAR summary endpoint."""

    outcar_path: str = Field(..., description="Path to an OUTCAR file")
    include_history: bool = Field(default=False, description="Include full TOTEN history")


class BatchSummaryRequestSchema(BaseModel):
    """Request payload for batch OUTCAR summary endpoint."""

    outcar_paths: list[str] = Field(..., description="List of OUTCAR file paths")
    fail_fast: bool = Field(default=False, description="Stop processing after the first failed item")


class DiagnosticsRequestSchema(BaseModel):
    """Request payload for OUTCAR diagnostics endpoint."""

    outcar_path: str = Field(..., description="Path to an OUTCAR file")
    energy_tolerance_ev: float = Field(default=1e-4, description="Convergence threshold for |ΔE| in eV")
    force_tolerance_ev_per_a: float = Field(default=0.02, description="Convergence threshold for max force")


class ConvergenceProfileRequestSchema(BaseModel):
    """Request payload for OUTCAR convergence profile endpoint."""

    outcar_path: str = Field(..., description="Path to an OUTCAR file")


class IonicSeriesRequestSchema(BaseModel):
    """Request payload for OUTCAR ionic-series endpoint."""

    outcar_path: str = Field(..., description="Path to an OUTCAR file")


class ExportTabularRequestSchema(BaseModel):
    """Request payload for OUTCAR tabular export endpoint."""

    outcar_path: str = Field(..., description="Path to an OUTCAR file")
    dataset: str = Field(default="ionic_series", description="Dataset: convergence_profile or ionic_series")
    delimiter: str = Field(default=",", description="Delimiter token or character")


class ElectronicMetadataRequestSchema(BaseModel):
    """Request payload for EIGENVAL/DOSCAR metadata endpoint."""

    eigenval_path: str | None = Field(default=None, description="Path to EIGENVAL")
    doscar_path: str | None = Field(default=None, description="Path to DOSCAR")


class StructureAtomSchema(BaseModel):
    """Atomic site for relaxation input generation."""

    element: str
    frac_coords: list[float] = Field(..., min_length=3, max_length=3)


class RelaxStructureSchema(BaseModel):
    """Structure payload for POSCAR generation."""

    comment: str
    lattice_vectors: list[list[float]] = Field(..., min_length=3, max_length=3)
    atoms: list[StructureAtomSchema] = Field(..., min_length=1)


class GenerateRelaxInputRequestSchema(BaseModel):
    """Request payload for generating relaxation input files."""

    structure: RelaxStructureSchema
    kmesh: list[int] = Field(default=[6, 6, 6], min_length=3, max_length=3)
    gamma_centered: bool = True
    encut: int = 520
    ediff: float = 1e-5
    ediffg: float = -0.02
    ismear: int = 0
    sigma: float = 0.05
    ibrion: int = 2
    isif: int = 3
    nsw: int = 120
    ispin: int = 2
    magmom: str | None = None
    incar_overrides: dict[str, Any] = Field(default_factory=dict)


class EnergyPointSchema(BaseModel):
    """Per-step energy sample included when history is requested."""

    ionic_step: int
    total_energy_ev: float


class StressTensorSchema(BaseModel):
    """Stress tensor components in kB."""

    xx_kb: float
    yy_kb: float
    zz_kb: float
    xy_kb: float
    yz_kb: float
    zx_kb: float


class MagnetizationSchema(BaseModel):
    """Final magnetization snapshot for selected axis."""

    axis: str
    total_moment_mu_b: float | None
    site_moments_mu_b: list[float]


class ConvergenceSchema(BaseModel):
    """Convergence report for OUTCAR diagnostics."""

    energy_tolerance_ev: float
    force_tolerance_ev_per_a: float
    final_energy_change_ev: float | None
    is_energy_converged: bool | None
    is_force_converged: bool | None
    is_converged: bool


class ConvergenceProfilePointSchema(BaseModel):
    """Chart-ready convergence point."""

    ionic_step: int
    total_energy_ev: float
    delta_energy_ev: float | None
    relative_energy_ev: float


class IonicSeriesPointSchema(BaseModel):
    """Per-step multi-metric series point for visualization."""

    ionic_step: int
    total_energy_ev: float | None
    delta_energy_ev: float | None
    relative_energy_ev: float | None
    max_force_ev_per_a: float | None
    external_pressure_kb: float | None
    fermi_energy_ev: float | None


class BandGapChannelSchema(BaseModel):
    """Band-gap metadata for one spin channel."""

    spin: str
    gap_ev: float
    vbm_ev: float
    cbm_ev: float
    is_direct: bool
    kpoint_index_vbm: int
    kpoint_index_cbm: int
    is_metal: bool


class BandGapSchema(BaseModel):
    """Fundamental band-gap metadata summary."""

    is_spin_polarized: bool
    is_metal: bool
    fundamental_gap_ev: float
    vbm_ev: float
    cbm_ev: float
    is_direct: bool
    channel: str
    channels: list[BandGapChannelSchema]


class DosMetadataSchema(BaseModel):
    """DOS metadata summary parsed from DOSCAR."""

    energy_min_ev: float
    energy_max_ev: float
    nedos: int
    efermi_ev: float
    is_spin_polarized: bool
    has_integrated_dos: bool
    energy_step_ev: float | None
    total_dos_at_fermi: float | None


class SummaryResponseSchema(BaseModel):
    """Response schema for OUTCAR summary endpoint."""

    source_path: str
    system_name: str | None
    nions: int | None
    ionic_steps: int
    electronic_iterations: int
    final_total_energy_ev: float | None
    final_fermi_energy_ev: float | None
    max_force_ev_per_a: float | None
    energy_history: list[EnergyPointSchema]
    warnings: list[str]


class BatchSummaryRowSchema(BaseModel):
    """Per-OUTCAR summary row for batch endpoint responses."""

    outcar_path: str
    status: str
    system_name: str | None
    nions: int | None
    ionic_steps: int | None
    electronic_iterations: int | None
    final_total_energy_ev: float | None
    final_fermi_energy_ev: float | None
    max_force_ev_per_a: float | None
    warnings: list[str]
    error: dict[str, Any] | None


class BatchSummaryResponseSchema(BaseModel):
    """Response schema for batch OUTCAR summary endpoint."""

    total_count: int
    success_count: int
    error_count: int
    rows: list[BatchSummaryRowSchema]


class DiagnosticsResponseSchema(BaseModel):
    """Response schema for OUTCAR diagnostics endpoint."""

    source_path: str
    system_name: str | None
    nions: int | None
    ionic_steps: int
    electronic_iterations: int
    final_total_energy_ev: float | None
    final_fermi_energy_ev: float | None
    max_force_ev_per_a: float | None
    external_pressure_kb: float | None
    stress_tensor_kb: StressTensorSchema | None
    magnetization: MagnetizationSchema | None
    convergence: ConvergenceSchema
    warnings: list[str]


class ConvergenceProfileResponseSchema(BaseModel):
    """Response schema for OUTCAR convergence profile endpoint."""

    source_path: str
    points: list[ConvergenceProfilePointSchema]
    final_total_energy_ev: float | None
    max_force_ev_per_a: float | None
    warnings: list[str]


class IonicSeriesResponseSchema(BaseModel):
    """Response schema for OUTCAR ionic-series endpoint."""

    source_path: str
    points: list[IonicSeriesPointSchema]
    n_steps: int
    warnings: list[str]


class ExportTabularResponseSchema(BaseModel):
    """Response schema for OUTCAR tabular export endpoint."""

    source_path: str
    dataset: str
    format: str
    delimiter: str
    filename_hint: str
    n_rows: int
    content: str
    warnings: list[str]


class ElectronicMetadataResponseSchema(BaseModel):
    """Response schema for EIGENVAL/DOSCAR metadata endpoint."""

    eigenval_path: str | None
    doscar_path: str | None
    band_gap: BandGapSchema | None
    dos_metadata: DosMetadataSchema | None
    warnings: list[str]


class GenerateRelaxInputResponseSchema(BaseModel):
    """Response schema for generated relaxation input files."""

    system_name: str
    n_atoms: int
    incar_text: str
    kpoints_text: str
    poscar_text: str
    warnings: list[str]


class ErrorSchema(BaseModel):
    """Error response model."""

    detail: dict[str, Any]
