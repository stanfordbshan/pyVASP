from __future__ import annotations

from pathlib import Path

import pytest

from pyvasp.core.errors import ParseError
from pyvasp.outcar.parser import OutcarParser


FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "OUTCAR.sample"
FIXTURE_PHASE2 = Path(__file__).resolve().parents[2] / "fixtures" / "OUTCAR.phase2.sample"


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


def test_parse_outcar_observables_fields() -> None:
    parser = OutcarParser()
    observables = parser.parse_observables_file(FIXTURE_PHASE2)

    assert observables.external_pressure_kb == pytest.approx(-1.23)
    assert observables.stress_tensor_kb is not None
    assert observables.stress_tensor_kb.xx_kb == pytest.approx(9.0)
    assert observables.magnetization is not None
    assert observables.magnetization.axis == "z"
    assert observables.magnetization.total_moment_mu_b == pytest.approx(0.3)
    assert observables.magnetization.site_moments_mu_b == pytest.approx((1.1, -0.8))
    assert observables.warnings == ()


def test_parse_outcar_ionic_series_fields() -> None:
    parser = OutcarParser()
    series = parser.parse_ionic_series_file(FIXTURE_PHASE2)

    assert len(series.points) == 2
    assert series.points[0].ionic_step == 1
    assert series.points[0].total_energy_ev == pytest.approx(-20.0)
    assert series.points[1].delta_energy_ev == pytest.approx(-5e-05)
    assert series.points[1].relative_energy_ev == pytest.approx(0.0)
    assert series.points[1].max_force_ev_per_a == pytest.approx(0.01)
    assert series.points[1].external_pressure_kb == pytest.approx(-1.23)
    assert series.points[1].fermi_energy_ev == pytest.approx(4.25)
    assert series.warnings == ()


def test_parse_outcar_rejects_invalid_text() -> None:
    parser = OutcarParser()
    with pytest.raises(ParseError):
        parser.parse_text("not a valid outcar", source_path="bad")
