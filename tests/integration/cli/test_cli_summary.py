from __future__ import annotations

import json
from pathlib import Path

from pyvasp.cli.main import main


FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "OUTCAR.sample"
FIXTURE_PHASE2 = Path(__file__).resolve().parents[2] / "fixtures" / "OUTCAR.phase2.sample"
STRUCTURE_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "structure.si2.json"
EIGENVAL_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "EIGENVAL.sample"
DOSCAR_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "DOSCAR.sample"


def test_cli_summary_direct_mode(capsys) -> None:
    exit_code = main(["summary", str(FIXTURE), "--mode", "direct"])
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["final_total_energy_ev"] == -10.5


def test_cli_batch_summary_direct_mode(capsys) -> None:
    exit_code = main(
        [
            "batch-summary",
            str(FIXTURE),
            "/missing/OUTCAR",
            "--mode",
            "direct",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["total_count"] == 2
    assert payload["success_count"] == 1
    assert payload["error_count"] == 1


def test_cli_batch_diagnostics_direct_mode(capsys) -> None:
    exit_code = main(
        [
            "batch-diagnostics",
            str(FIXTURE_PHASE2),
            "/missing/OUTCAR",
            "--mode",
            "direct",
            "--energy-tol",
            "1e-4",
            "--force-tol",
            "0.02",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["total_count"] == 2
    assert payload["success_count"] == 1
    assert payload["rows"][0]["is_converged"] is True
    assert payload["rows"][1]["error"]["code"] == "FILE_NOT_FOUND"


def test_cli_diagnostics_direct_mode(capsys) -> None:
    exit_code = main(["diagnostics", str(FIXTURE_PHASE2), "--mode", "direct"])
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["convergence"]["is_converged"] is True
    assert payload["external_pressure_kb"] == -1.23


def test_cli_convergence_profile_direct_mode(capsys) -> None:
    exit_code = main(["convergence-profile", str(FIXTURE), "--mode", "direct"])
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    assert len(payload["points"]) == 2


def test_cli_ionic_series_direct_mode(capsys) -> None:
    exit_code = main(["ionic-series", str(FIXTURE_PHASE2), "--mode", "direct"])
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["n_steps"] == 2
    assert payload["points"][1]["external_pressure_kb"] == -1.23


def test_cli_export_tabular_direct_mode(tmp_path: Path, capsys) -> None:
    output_file = tmp_path / "ionic_series.csv"
    exit_code = main(
        [
            "export-tabular",
            str(FIXTURE_PHASE2),
            "--mode",
            "direct",
            "--dataset",
            "ionic_series",
            "--delimiter",
            "comma",
            "--output-file",
            str(output_file),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["dataset"] == "ionic_series"
    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert "external_pressure_kb" in content


def test_cli_electronic_metadata_direct_mode(capsys) -> None:
    exit_code = main(
        [
            "electronic-metadata",
            "--eigenval-path",
            str(EIGENVAL_FIXTURE),
            "--doscar-path",
            str(DOSCAR_FIXTURE),
            "--mode",
            "direct",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["band_gap"]["fundamental_gap_ev"] == 1.3
    assert payload["dos_metadata"]["nedos"] == 5


def test_cli_dos_profile_direct_mode(capsys) -> None:
    exit_code = main(
        [
            "dos-profile",
            str(DOSCAR_FIXTURE),
            "--energy-window",
            "2.0",
            "--max-points",
            "100",
            "--mode",
            "direct",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["source_path"] == str(DOSCAR_FIXTURE)
    assert payload["n_points"] > 0


def test_cli_generate_relax_input_and_write_files(tmp_path: Path, capsys) -> None:
    output_dir = tmp_path / "vasp_inputs"
    exit_code = main(
        [
            "generate-relax-input",
            str(STRUCTURE_FIXTURE),
            "--mode",
            "direct",
            "--output-dir",
            str(output_dir),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["n_atoms"] == 2
    assert (output_dir / "INCAR").exists()
    assert (output_dir / "KPOINTS").exists()
    assert (output_dir / "POSCAR").exists()


def test_cli_summary_missing_file_fails(capsys) -> None:
    exit_code = main(["summary", "/missing/OUTCAR", "--mode", "direct"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "does not exist" in captured.err
