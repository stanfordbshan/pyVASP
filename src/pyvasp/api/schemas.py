"""HTTP-facing request/response schemas for pyVASP API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SummaryRequestSchema(BaseModel):
    """Request payload for OUTCAR summary endpoint."""

    outcar_path: str = Field(..., description="Path to an OUTCAR file")
    include_history: bool = Field(default=False, description="Include full TOTEN history")


class EnergyPointSchema(BaseModel):
    """Per-step energy sample included when history is requested."""

    ionic_step: int
    total_energy_ev: float


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


class ErrorSchema(BaseModel):
    """Error response model."""

    detail: str
