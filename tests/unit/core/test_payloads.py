from __future__ import annotations

from pathlib import Path

import pytest

from pyvasp.core.errors import ValidationError
from pyvasp.core.models import EnergyPoint, OutcarSummary
from pyvasp.core.payloads import SummaryResponsePayload, validate_summary_request


FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "OUTCAR.sample"


def test_validate_summary_request_success() -> None:
    payload = validate_summary_request({"outcar_path": str(FIXTURE), "include_history": True})
    assert payload.outcar_path == str(FIXTURE)
    assert payload.include_history is True


def test_validate_summary_request_missing_file_raises() -> None:
    with pytest.raises(ValidationError):
        validate_summary_request({"outcar_path": "/does/not/exist/OUTCAR"})


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
