from __future__ import annotations

from pathlib import Path

import pytest

from pyvasp.core.errors import ValidationError
from pyvasp.core.models import (
    ConvergenceReport,
    EnergyPoint,
    MagnetizationSummary,
    OutcarDiagnostics,
    OutcarSummary,
    StressTensor,
)
from pyvasp.core.payloads import (
    DiagnosticsResponsePayload,
    SummaryResponsePayload,
    validate_diagnostics_request,
    validate_summary_request,
)


FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "OUTCAR.sample"


def test_validate_summary_request_success() -> None:
    payload = validate_summary_request({"outcar_path": str(FIXTURE), "include_history": True})
    assert payload.outcar_path == str(FIXTURE)
    assert payload.include_history is True


def test_validate_summary_request_missing_file_raises() -> None:
    with pytest.raises(ValidationError):
        validate_summary_request({"outcar_path": "/does/not/exist/OUTCAR"})


def test_validate_diagnostics_request_rejects_non_positive_tolerances() -> None:
    with pytest.raises(ValidationError):
        validate_diagnostics_request(
            {
                "outcar_path": str(FIXTURE),
                "energy_tolerance_ev": 0,
                "force_tolerance_ev_per_a": 0.02,
            }
        )


def test_summary_response_payload_hides_history_when_not_requested() -> None:
    summary = OutcarSummary(
        source_path=str(FIXTURE),
        system_name="Si2 test",
        nions=2,
        ionic_steps=2,
        electronic_iterations=4,
        final_total_energy_ev=-10.5,
        final_fermi_energy_ev=5.2,
        max_force_ev_per_a=0.005,
        energy_history=(EnergyPoint(ionic_step=1, total_energy_ev=-10.0),),
        warnings=(),
    )
    payload = SummaryResponsePayload.from_summary(summary, include_history=False)
    mapped = payload.to_mapping()
    assert mapped["energy_history"] == []


def test_diagnostics_response_payload_serialization() -> None:
    summary = OutcarSummary(
        source_path=str(FIXTURE),
        system_name="Fe2",
        nions=2,
        ionic_steps=2,
        electronic_iterations=2,
        final_total_energy_ev=-20.00005,
        final_fermi_energy_ev=4.25,
        max_force_ev_per_a=0.01,
        energy_history=(
            EnergyPoint(ionic_step=1, total_energy_ev=-20.0),
            EnergyPoint(ionic_step=2, total_energy_ev=-20.00005),
        ),
        warnings=(),
    )
    diagnostics = OutcarDiagnostics(
        source_path=str(FIXTURE),
        summary=summary,
        external_pressure_kb=-1.23,
        stress_tensor_kb=StressTensor(9.0, 18.0, 27.0, 0.9, 1.8, 2.7),
        magnetization=MagnetizationSummary(axis="z", total_moment_mu_b=0.3, site_moments_mu_b=(1.1, -0.8)),
        convergence=ConvergenceReport(
            energy_tolerance_ev=1e-4,
            force_tolerance_ev_per_a=0.02,
            final_energy_change_ev=5e-05,
            is_energy_converged=True,
            is_force_converged=True,
            is_converged=True,
        ),
        warnings=("ok",),
    )

    payload = DiagnosticsResponsePayload.from_diagnostics(diagnostics)
    mapped = payload.to_mapping()

    assert mapped["external_pressure_kb"] == pytest.approx(-1.23)
    assert mapped["stress_tensor_kb"]["xx_kb"] == pytest.approx(9.0)
    assert mapped["magnetization"]["site_moments_mu_b"] == [1.1, -0.8]
    assert mapped["convergence"]["is_converged"] is True
    assert mapped["warnings"] == ["ok"]
