from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from pyvasp.api.server import create_app


FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "OUTCAR.sample"
FIXTURE_PHASE2 = Path(__file__).resolve().parents[2] / "fixtures" / "OUTCAR.phase2.sample"
STRUCTURE_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "structure.si2.json"
EIGENVAL_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "EIGENVAL.sample"
DOSCAR_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "DOSCAR.sample"


def test_api_summarize_outcar_success() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/outcar/summary",
        json={"outcar_path": str(FIXTURE), "include_history": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_path"] == str(FIXTURE)
    assert body["final_total_energy_ev"] == -10.5
    assert len(body["energy_history"]) == 2


def test_api_summarize_outcar_bad_path() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/outcar/summary",
        json={"outcar_path": "/missing/OUTCAR", "include_history": False},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "FILE_NOT_FOUND"
    assert "does not exist" in detail["message"]
    assert detail["details"]["field"] == "outcar_path"


def test_api_summarize_outcar_parse_error(tmp_path: Path) -> None:
    invalid_outcar = tmp_path / "OUTCAR.invalid"
    invalid_outcar.write_text("this file is not a valid OUTCAR\n", encoding="utf-8")

    client = TestClient(create_app())
    response = client.post(
        "/v1/outcar/summary",
        json={"outcar_path": str(invalid_outcar), "include_history": False},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "PARSE_ERROR"
    assert "valid VASP OUTCAR" in detail["message"]


def test_api_batch_summary_mixed_results() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/outcar/batch-summary",
        json={
            "outcar_paths": [str(FIXTURE), "/missing/OUTCAR"],
            "fail_fast": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 2
    assert body["success_count"] == 1
    assert body["error_count"] == 1
    assert body["rows"][0]["status"] == "ok"
    assert body["rows"][1]["status"] == "error"
    assert body["rows"][1]["error"]["code"] == "FILE_NOT_FOUND"


def test_api_batch_summary_bad_request() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/outcar/batch-summary",
        json={"outcar_paths": []},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "VALIDATION_ERROR"
    assert "outcar_paths" in detail["message"]


def test_api_batch_diagnostics_mixed_results() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/outcar/batch-diagnostics",
        json={
            "outcar_paths": [str(FIXTURE_PHASE2), "/missing/OUTCAR"],
            "energy_tolerance_ev": 1e-4,
            "force_tolerance_ev_per_a": 0.02,
            "fail_fast": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 2
    assert body["success_count"] == 1
    assert body["error_count"] == 1
    assert body["rows"][0]["status"] == "ok"
    assert body["rows"][0]["is_converged"] is True
    assert body["rows"][1]["status"] == "error"
    assert body["rows"][1]["error"]["code"] == "FILE_NOT_FOUND"


def test_api_batch_diagnostics_bad_request() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/outcar/batch-diagnostics",
        json={"outcar_paths": []},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "VALIDATION_ERROR"
    assert "outcar_paths" in detail["message"]


def test_api_diagnostics_success() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/outcar/diagnostics",
        json={
            "outcar_path": str(FIXTURE_PHASE2),
            "energy_tolerance_ev": 1e-4,
            "force_tolerance_ev_per_a": 0.02,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["external_pressure_kb"] == -1.23
    assert body["stress_tensor_kb"]["xx_kb"] == 9.0
    assert body["magnetization"]["axis"] == "z"
    assert body["convergence"]["is_converged"] is True


def test_api_diagnostics_bad_tolerance() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/outcar/diagnostics",
        json={
            "outcar_path": str(FIXTURE_PHASE2),
            "energy_tolerance_ev": -1.0,
            "force_tolerance_ev_per_a": 0.02,
        },
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "VALIDATION_ERROR"
    assert "energy_tolerance_ev" in detail["message"]


def test_api_convergence_profile_success() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/outcar/convergence-profile",
        json={"outcar_path": str(FIXTURE)},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_path"] == str(FIXTURE)
    assert len(body["points"]) == 2
    assert body["points"][0]["delta_energy_ev"] is None


def test_api_ionic_series_success() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/outcar/ionic-series",
        json={"outcar_path": str(FIXTURE_PHASE2)},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_path"] == str(FIXTURE_PHASE2)
    assert body["n_steps"] == 2
    assert body["points"][1]["relative_energy_ev"] == 0.0
    assert body["points"][1]["external_pressure_kb"] == -1.23


def test_api_export_tabular_success() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/outcar/export-tabular",
        json={
            "outcar_path": str(FIXTURE_PHASE2),
            "dataset": "ionic_series",
            "delimiter": ",",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["dataset"] == "ionic_series"
    assert body["format"] == "csv"
    assert body["n_rows"] == 2
    assert "external_pressure_kb" in body["content"]


def test_api_export_tabular_bad_dataset() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/outcar/export-tabular",
        json={"outcar_path": str(FIXTURE_PHASE2), "dataset": "bad"},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "VALIDATION_ERROR"
    assert "dataset" in detail["message"]


def test_api_electronic_metadata_success() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/electronic/metadata",
        json={
            "eigenval_path": str(EIGENVAL_FIXTURE),
            "doscar_path": str(DOSCAR_FIXTURE),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["band_gap"]["fundamental_gap_ev"] == 1.3
    assert body["dos_metadata"]["nedos"] == 5


def test_api_electronic_metadata_requires_one_file() -> None:
    client = TestClient(create_app())
    response = client.post("/v1/electronic/metadata", json={})

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "VALIDATION_ERROR"
    assert "At least one" in detail["message"]


def test_api_generate_relax_input_success() -> None:
    client = TestClient(create_app())
    structure = json.loads(STRUCTURE_FIXTURE.read_text(encoding="utf-8"))

    response = client.post(
        "/v1/input/relax-generate",
        json={"structure": structure, "kmesh": [4, 4, 4]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["system_name"] == "Si2 cubic"
    assert body["n_atoms"] == 2
    assert "ENCUT = 520" in body["incar_text"]
    assert "Automatic mesh" in body["kpoints_text"]
    assert "Direct" in body["poscar_text"]
