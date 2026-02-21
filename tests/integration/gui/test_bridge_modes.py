from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from pyvasp.gui.bridge import GuiBackendBridge
from pyvasp.gui.host import create_gui_app


FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "OUTCAR.sample"
FIXTURE_PHASE2 = Path(__file__).resolve().parents[2] / "fixtures" / "OUTCAR.phase2.sample"
STRUCTURE_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "structure.si2.json"
EIGENVAL_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "EIGENVAL.sample"
DOSCAR_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "DOSCAR.sample"


def test_bridge_direct_mode_uses_local_use_case() -> None:
    bridge = GuiBackendBridge(mode="direct")
    response = bridge.summarize_outcar(outcar_path=str(FIXTURE), include_history=False)

    assert response["final_total_energy_ev"] == -10.5
    assert response["energy_history"] == []


def test_bridge_direct_mode_diagnostics() -> None:
    bridge = GuiBackendBridge(mode="direct")
    response = bridge.diagnose_outcar(outcar_path=str(FIXTURE_PHASE2))

    assert response["external_pressure_kb"] == -1.23
    assert response["convergence"]["is_converged"] is True


def test_bridge_direct_mode_profile_electronic_and_input_generation() -> None:
    bridge = GuiBackendBridge(mode="direct")

    profile = bridge.build_convergence_profile(outcar_path=str(FIXTURE))
    assert len(profile["points"]) == 2

    ionic_series = bridge.build_ionic_series(outcar_path=str(FIXTURE_PHASE2))
    assert ionic_series["n_steps"] == 2
    assert ionic_series["points"][1]["external_pressure_kb"] == -1.23

    electronic = bridge.parse_electronic_metadata(
        eigenval_path=str(EIGENVAL_FIXTURE),
        doscar_path=str(DOSCAR_FIXTURE),
    )
    assert electronic["band_gap"]["fundamental_gap_ev"] == 1.3

    structure = json.loads(STRUCTURE_FIXTURE.read_text(encoding="utf-8"))
    generated = bridge.generate_relax_input(structure=structure)
    assert generated["n_atoms"] == 2
    assert "ENCUT = 520" in generated["incar_text"]


def test_bridge_auto_mode_falls_back_to_api(monkeypatch) -> None:
    bridge = GuiBackendBridge(mode="auto")

    def fail_direct(payload: dict) -> dict:
        raise RuntimeError("direct failed")

    def succeed_api(*, api_path: str, payload: dict) -> dict:
        return {"source_path": payload.get("outcar_path", "n/a"), "via": api_path}

    monkeypatch.setattr(bridge, "_call_direct_summary", fail_direct)
    monkeypatch.setattr(bridge, "_call_api", succeed_api)

    response = bridge.summarize_outcar(outcar_path=str(FIXTURE), include_history=False)
    assert response["via"] == "/v1/outcar/summary"


def test_gui_host_ui_summary_endpoint() -> None:
    app = create_gui_app(mode="direct")
    client = TestClient(app)

    response = client.post(
        "/ui/summary",
        json={"outcar_path": str(FIXTURE), "include_history": False},
    )

    assert response.status_code == 200
    assert response.json()["final_total_energy_ev"] == -10.5


def test_gui_host_ui_diagnostics_endpoint() -> None:
    app = create_gui_app(mode="direct")
    client = TestClient(app)

    response = client.post(
        "/ui/diagnostics",
        json={"outcar_path": str(FIXTURE_PHASE2)},
    )

    assert response.status_code == 200
    assert response.json()["magnetization"]["axis"] == "z"


def test_gui_host_ui_summary_missing_file_returns_structured_error() -> None:
    app = create_gui_app(mode="direct")
    client = TestClient(app)

    response = client.post(
        "/ui/summary",
        json={"outcar_path": "/missing/OUTCAR", "include_history": False},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "FILE_NOT_FOUND"
    assert "does not exist" in detail["message"]


def test_gui_host_ui_profile_electronic_and_input_endpoints() -> None:
    app = create_gui_app(mode="direct")
    client = TestClient(app)

    profile = client.post("/ui/convergence-profile", json={"outcar_path": str(FIXTURE)})
    assert profile.status_code == 200
    assert len(profile.json()["points"]) == 2

    ionic_series = client.post("/ui/ionic-series", json={"outcar_path": str(FIXTURE_PHASE2)})
    assert ionic_series.status_code == 200
    assert ionic_series.json()["n_steps"] == 2

    electronic = client.post(
        "/ui/electronic-metadata",
        json={"eigenval_path": str(EIGENVAL_FIXTURE), "doscar_path": str(DOSCAR_FIXTURE)},
    )
    assert electronic.status_code == 200
    assert electronic.json()["dos_metadata"]["nedos"] == 5

    structure = json.loads(STRUCTURE_FIXTURE.read_text(encoding="utf-8"))
    generated = client.post("/ui/generate-relax-input", json={"structure": structure})
    assert generated.status_code == 200
    assert generated.json()["system_name"] == "Si2 cubic"
