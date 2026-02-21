from __future__ import annotations

import json
from pathlib import Path

from pyvasp.cli.main import main


FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "OUTCAR.sample"
FIXTURE_PHASE2 = Path(__file__).resolve().parents[2] / "fixtures" / "OUTCAR.phase2.sample"


def test_cli_summary_direct_mode(capsys) -> None:
    exit_code = main(["summary", str(FIXTURE), "--mode", "direct"])
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["final_total_energy_ev"] == -10.5


def test_cli_diagnostics_direct_mode(capsys) -> None:
    exit_code = main(["diagnostics", str(FIXTURE_PHASE2), "--mode", "direct"])
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["convergence"]["is_converged"] is True
    assert payload["external_pressure_kb"] == -1.23


def test_cli_summary_missing_file_fails(capsys) -> None:
    exit_code = main(["summary", "/missing/OUTCAR", "--mode", "direct"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "does not exist" in captured.err
