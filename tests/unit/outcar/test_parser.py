from __future__ import annotations

from pathlib import Path

import pytest

from pyvasp.core.errors import ParseError
from pyvasp.outcar.parser import OutcarParser


FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "OUTCAR.sample"


def test_parse_outcar_summary_fields() -> None:
    parser = OutcarParser()
    summary = parser.parse_file(FIXTURE)

    assert summary.system_name == "Si2 test"
    assert summary.nions == 2
    assert summary.ionic_steps == 2
    assert summary.electronic_iterations == 4
    assert summary.final_total_energy_ev == pytest.approx(-10.5)
    assert summary.final_fermi_energy_ev == pytest.approx(5.2)
    assert summary.max_force_ev_per_a == pytest.approx(0.005)
    assert len(summary.energy_history) == 2
    assert summary.warnings == ()


def test_parse_outcar_rejects_invalid_text() -> None:
    parser = OutcarParser()
    with pytest.raises(ParseError):
        parser.parse_text("not a valid outcar", source_path="bad")
