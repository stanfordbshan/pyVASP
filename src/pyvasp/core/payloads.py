"""Shared payload mapping and validation for adapter-facing contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from pyvasp.core.errors import ValidationError
from pyvasp.core.models import OutcarSummary
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


def validate_summary_request(raw: dict[str, Any]) -> SummaryRequestPayload:
    """Map arbitrary adapter payload into canonical request object."""

    try:
        return SummaryRequestPayload.from_mapping(raw)
    except ValidationError:
        raise
    except Exception as exc:  # pragma: no cover - defensive normalization
        raise ValidationError(str(exc)) from exc
