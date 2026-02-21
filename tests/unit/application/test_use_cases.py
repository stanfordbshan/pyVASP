from __future__ import annotations

from pathlib import Path

from pyvasp.application.use_cases import DiagnoseOutcarUseCase, SummarizeOutcarUseCase
from pyvasp.core.errors import ParseError
from pyvasp.core.models import (
    EnergyPoint,
    MagnetizationSummary,
    OutcarObservables,
    OutcarSummary,
    StressTensor,
)
from pyvasp.core.payloads import DiagnosticsRequestPayload, SummaryRequestPayload


FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "OUTCAR.sample"


class WorkingSummaryReader:
    def parse_file(self, outcar_path: Path) -> OutcarSummary:
        return OutcarSummary(
            source_path=str(outcar_path),
            system_name="stub",
            nions=1,
            ionic_steps=1,
            electronic_iterations=3,
            final_total_energy_ev=-1.23,
            final_fermi_energy_ev=2.34,
            max_force_ev_per_a=0.01,
            energy_history=(EnergyPoint(ionic_step=1, total_energy_ev=-1.23),),
            warnings=(),
        )


class BrokenSummaryReader:
    def parse_file(self, outcar_path: Path) -> OutcarSummary:
        raise ParseError("failed")


class WorkingObservablesReader:
    def parse_observables_file(self, outcar_path: Path) -> OutcarObservables:
        summary = OutcarSummary(
            source_path=str(outcar_path),
            system_name="diag",
            nions=2,
            ionic_steps=2,
            electronic_iterations=4,
            final_total_energy_ev=-20.00005,
            final_fermi_energy_ev=4.25,
            max_force_ev_per_a=0.01,
            energy_history=(
                EnergyPoint(ionic_step=1, total_energy_ev=-20.0),
                EnergyPoint(ionic_step=2, total_energy_ev=-20.00005),
            ),
            warnings=(),
        )
        return OutcarObservables(
            source_path=str(outcar_path),
            summary=summary,
            external_pressure_kb=-1.23,
            stress_tensor_kb=StressTensor(9.0, 18.0, 27.0, 0.9, 1.8, 2.7),
            magnetization=MagnetizationSummary(axis="z", total_moment_mu_b=0.3, site_moments_mu_b=(1.1, -0.8)),
            warnings=(),
        )


class BrokenObservablesReader:
    def parse_observables_file(self, outcar_path: Path) -> OutcarObservables:
        raise ParseError("diagnostics failed")


def test_summary_use_case_success() -> None:
    use_case = SummarizeOutcarUseCase(reader=WorkingSummaryReader())
    request = SummaryRequestPayload(outcar_path=str(FIXTURE), include_history=True)

    result = use_case.execute(request)
    assert result.ok is True
    assert result.value is not None
    assert result.value.final_total_energy_ev == -1.23


def test_summary_use_case_failure() -> None:
    use_case = SummarizeOutcarUseCase(reader=BrokenSummaryReader())
    request = SummaryRequestPayload(outcar_path=str(FIXTURE), include_history=False)

    result = use_case.execute(request)
    assert result.ok is False
    assert result.error == "failed"


def test_diagnostics_use_case_success() -> None:
    use_case = DiagnoseOutcarUseCase(reader=WorkingObservablesReader())
    request = DiagnosticsRequestPayload(
        outcar_path=str(FIXTURE),
        energy_tolerance_ev=1e-4,
        force_tolerance_ev_per_a=0.02,
    )

    result = use_case.execute(request)
    assert result.ok is True
    assert result.value is not None
    assert result.value.convergence["is_converged"] is True
    assert result.value.external_pressure_kb == -1.23


def test_diagnostics_use_case_failure() -> None:
    use_case = DiagnoseOutcarUseCase(reader=BrokenObservablesReader())
    request = DiagnosticsRequestPayload(outcar_path=str(FIXTURE))

    result = use_case.execute(request)
    assert result.ok is False
    assert result.error == "diagnostics failed"
