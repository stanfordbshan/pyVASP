"""Shared payload mapping and validation for adapter-facing contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from pyvasp.core.errors import ValidationError
from pyvasp.core.models import OutcarDiagnostics, OutcarSummary, StressTensor
from pyvasp.core.validators import validate_outcar_path


@dataclass(frozen=True)
class SummaryRequestPayload:
    """Canonical request payload for OUTCAR summarization."""

    outcar_path: str
    include_history: bool = False

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "SummaryRequestPayload":
        path_value = raw.get("outcar_path")
        include_history = bool(raw.get("include_history", False))

        resolved = validate_outcar_path(str(path_value) if path_value is not None else "")
        return cls(outcar_path=str(resolved), include_history=include_history)

    def validated_path(self) -> Path:
        return validate_outcar_path(self.outcar_path)


@dataclass(frozen=True)
class DiagnosticsRequestPayload:
    """Canonical request payload for OUTCAR diagnostics."""

    outcar_path: str
    energy_tolerance_ev: float = 1e-4
    force_tolerance_ev_per_a: float = 0.02

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "DiagnosticsRequestPayload":
        path_value = raw.get("outcar_path")
        resolved = validate_outcar_path(str(path_value) if path_value is not None else "")

        energy_tolerance_ev = _coerce_positive_float(raw.get("energy_tolerance_ev", 1e-4), "energy_tolerance_ev")
        force_tolerance_ev_per_a = _coerce_positive_float(
            raw.get("force_tolerance_ev_per_a", 0.02),
            "force_tolerance_ev_per_a",
        )

        return cls(
            outcar_path=str(resolved),
            energy_tolerance_ev=energy_tolerance_ev,
            force_tolerance_ev_per_a=force_tolerance_ev_per_a,
        )

    def validated_path(self) -> Path:
        return validate_outcar_path(self.outcar_path)


@dataclass(frozen=True)
class SummaryResponsePayload:
    """Canonical response payload consumed by API/GUI/CLI adapters."""

    source_path: str
    system_name: str | None
    nions: int | None
    ionic_steps: int
    electronic_iterations: int
    final_total_energy_ev: float | None
    final_fermi_energy_ev: float | None
    max_force_ev_per_a: float | None
    energy_history: tuple[dict[str, Any], ...]
    warnings: tuple[str, ...]

    @classmethod
    def from_summary(
        cls,
        summary: OutcarSummary,
        *,
        include_history: bool,
    ) -> "SummaryResponsePayload":
        history: tuple[dict[str, Any], ...] = ()
        if include_history:
            history = tuple(
                {
                    "ionic_step": point.ionic_step,
                    "total_energy_ev": point.total_energy_ev,
                }
                for point in summary.energy_history
            )

        return cls(
            source_path=summary.source_path,
            system_name=summary.system_name,
            nions=summary.nions,
            ionic_steps=summary.ionic_steps,
            electronic_iterations=summary.electronic_iterations,
            final_total_energy_ev=summary.final_total_energy_ev,
            final_fermi_energy_ev=summary.final_fermi_energy_ev,
            max_force_ev_per_a=summary.max_force_ev_per_a,
            energy_history=history,
            warnings=summary.warnings,
        )

    def to_mapping(self) -> dict[str, Any]:
        """Serialize to a transport-neutral mapping for adapters."""

        mapped = asdict(self)
        mapped["warnings"] = list(self.warnings)
        mapped["energy_history"] = list(self.energy_history)
        return mapped


@dataclass(frozen=True)
class DiagnosticsResponsePayload:
    """Canonical diagnostics response consumed by API/GUI/CLI adapters."""

    source_path: str
    system_name: str | None
    nions: int | None
    ionic_steps: int
    electronic_iterations: int
    final_total_energy_ev: float | None
    final_fermi_energy_ev: float | None
    max_force_ev_per_a: float | None
    external_pressure_kb: float | None
    stress_tensor_kb: dict[str, float] | None
    magnetization: dict[str, Any] | None
    convergence: dict[str, Any]
    warnings: tuple[str, ...]

    @classmethod
    def from_diagnostics(cls, diagnostics: OutcarDiagnostics) -> "DiagnosticsResponsePayload":
        stress_tensor = _serialize_stress_tensor(diagnostics.stress_tensor_kb)
        magnetization = _serialize_magnetization(diagnostics)

        return cls(
            source_path=diagnostics.source_path,
            system_name=diagnostics.summary.system_name,
            nions=diagnostics.summary.nions,
            ionic_steps=diagnostics.summary.ionic_steps,
            electronic_iterations=diagnostics.summary.electronic_iterations,
            final_total_energy_ev=diagnostics.summary.final_total_energy_ev,
            final_fermi_energy_ev=diagnostics.summary.final_fermi_energy_ev,
            max_force_ev_per_a=diagnostics.summary.max_force_ev_per_a,
            external_pressure_kb=diagnostics.external_pressure_kb,
            stress_tensor_kb=stress_tensor,
            magnetization=magnetization,
            convergence={
                "energy_tolerance_ev": diagnostics.convergence.energy_tolerance_ev,
                "force_tolerance_ev_per_a": diagnostics.convergence.force_tolerance_ev_per_a,
                "final_energy_change_ev": diagnostics.convergence.final_energy_change_ev,
                "is_energy_converged": diagnostics.convergence.is_energy_converged,
                "is_force_converged": diagnostics.convergence.is_force_converged,
                "is_converged": diagnostics.convergence.is_converged,
            },
            warnings=diagnostics.warnings,
        )

    def to_mapping(self) -> dict[str, Any]:
        mapped = asdict(self)
        mapped["warnings"] = list(self.warnings)
        return mapped


def validate_summary_request(raw: dict[str, Any]) -> SummaryRequestPayload:
    """Map arbitrary adapter payload into canonical summary request object."""

    try:
        return SummaryRequestPayload.from_mapping(raw)
    except ValidationError:
        raise
    except Exception as exc:  # pragma: no cover - defensive normalization
        raise ValidationError(str(exc)) from exc


def validate_diagnostics_request(raw: dict[str, Any]) -> DiagnosticsRequestPayload:
    """Map arbitrary adapter payload into canonical diagnostics request object."""

    try:
        return DiagnosticsRequestPayload.from_mapping(raw)
    except ValidationError:
        raise
    except Exception as exc:  # pragma: no cover - defensive normalization
        raise ValidationError(str(exc)) from exc


def _serialize_stress_tensor(tensor: StressTensor | None) -> dict[str, float] | None:
    if tensor is None:
        return None
    return {
        "xx_kb": tensor.xx_kb,
        "yy_kb": tensor.yy_kb,
        "zz_kb": tensor.zz_kb,
        "xy_kb": tensor.xy_kb,
        "yz_kb": tensor.yz_kb,
        "zx_kb": tensor.zx_kb,
    }


def _serialize_magnetization(diagnostics: OutcarDiagnostics) -> dict[str, Any] | None:
    if diagnostics.magnetization is None:
        return None
    return {
        "axis": diagnostics.magnetization.axis,
        "total_moment_mu_b": diagnostics.magnetization.total_moment_mu_b,
        "site_moments_mu_b": list(diagnostics.magnetization.site_moments_mu_b),
    }


def _coerce_positive_float(value: Any, field_name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field_name} must be a positive number") from exc

    if number <= 0:
        raise ValidationError(f"{field_name} must be > 0")
    return number
