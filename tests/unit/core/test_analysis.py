from __future__ import annotations

import pytest

from pyvasp.core.analysis import build_convergence_report
from pyvasp.core.models import EnergyPoint, OutcarSummary


def test_build_convergence_report_detects_converged_case() -> None:
    summary = OutcarSummary(
        source_path="/tmp/OUTCAR",
        system_name="Fe2",
        nions=2,
        ionic_steps=2,
        electronic_iterations=4,
        final_total_energy_ev=-20.00005,
        final_fermi_energy_ev=4.2,
        max_force_ev_per_a=0.01,
        energy_history=(
            EnergyPoint(ionic_step=1, total_energy_ev=-20.0),
            EnergyPoint(ionic_step=2, total_energy_ev=-20.00005),
        ),
        warnings=(),
    )

    report = build_convergence_report(summary, energy_tolerance_ev=1e-4, force_tolerance_ev_per_a=0.02)

    assert report.final_energy_change_ev == pytest.approx(5e-05)
    assert report.is_energy_converged is True
    assert report.is_force_converged is True
    assert report.is_converged is True


def test_build_convergence_report_handles_missing_data() -> None:
    summary = OutcarSummary(
        source_path="/tmp/OUTCAR",
        system_name="Fe2",
        nions=2,
        ionic_steps=1,
        electronic_iterations=2,
        final_total_energy_ev=-20.0,
        final_fermi_energy_ev=4.0,
        max_force_ev_per_a=None,
        energy_history=(EnergyPoint(ionic_step=1, total_energy_ev=-20.0),),
        warnings=(),
    )

    report = build_convergence_report(summary, energy_tolerance_ev=1e-4, force_tolerance_ev_per_a=0.02)

    assert report.final_energy_change_ev is None
    assert report.is_energy_converged is None
    assert report.is_force_converged is None
    assert report.is_converged is False
