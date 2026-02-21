"""HTTP-facing request/response schemas for pyVASP API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SummaryRequestSchema(BaseModel):
    """Request payload for OUTCAR summary endpoint."""

    outcar_path: str = Field(..., description="Path to an OUTCAR file")
    include_history: bool = Field(default=False, description="Include full TOTEN history")


class DiagnosticsRequestSchema(BaseModel):
    """Request payload for OUTCAR diagnostics endpoint."""

    outcar_path: str = Field(..., description="Path to an OUTCAR file")
    energy_tolerance_ev: float = Field(default=1e-4, description="Convergence threshold for |ΔE| in eV")
    force_tolerance_ev_per_a: float = Field(default=0.02, description="Convergence threshold for max force")


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


class ErrorSchema(BaseModel):
    """Error response model."""

    detail: str
