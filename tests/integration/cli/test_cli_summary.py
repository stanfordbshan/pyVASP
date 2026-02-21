from __future__ import annotations

import json
from pathlib import Path

from pyvasp.cli.main import main


FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "OUTCAR.sample"


def test_cli_summary_direct_mode(capsys) -> None:
    exit_code = main(["summary", str(FIXTURE), "--mode", "direct"])
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["final_total_energy_ev"] == -10.5


def test_cli_summary_missing_file_fails(capsys) -> None:
    exit_code = main(["summary", "/missing/OUTCAR", "--mode", "direct"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "does not exist" in captured.err
