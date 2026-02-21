from __future__ import annotations

from pathlib import Path

from pyvasp.application.use_cases import SummarizeOutcarUseCase
from pyvasp.core.errors import ParseError
from pyvasp.core.models import EnergyPoint, OutcarSummary
from pyvasp.core.payloads import SummaryRequestPayload


FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "OUTCAR.sample"


class WorkingReader:
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


class BrokenReader:
    def parse_file(self, outcar_path: Path) -> OutcarSummary:
        raise ParseError("failed")


def test_use_case_success() -> None:
    use_case = SummarizeOutcarUseCase(reader=WorkingReader())
    request = SummaryRequestPayload(outcar_path=str(FIXTURE), include_history=True)

    result = use_case.execute(request)
    assert result.ok is True
    assert result.value is not None
    assert result.value.final_total_energy_ev == -1.23


def test_use_case_failure() -> None:
    use_case = SummarizeOutcarUseCase(reader=BrokenReader())
    request = SummaryRequestPayload(outcar_path=str(FIXTURE), include_history=False)

    result = use_case.execute(request)
    assert result.ok is False
    assert result.error == "failed"
