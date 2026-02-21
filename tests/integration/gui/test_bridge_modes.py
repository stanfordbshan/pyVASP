from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from pyvasp.gui.bridge import GuiBackendBridge
from pyvasp.gui.host import create_gui_app


FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "OUTCAR.sample"


def test_bridge_direct_mode_uses_local_use_case() -> None:
    bridge = GuiBackendBridge(mode="direct")
    response = bridge.summarize_outcar(outcar_path=str(FIXTURE), include_history=False)

    assert response["final_total_energy_ev"] == -10.5
    assert response["energy_history"] == []


def test_bridge_auto_mode_falls_back_to_api(monkeypatch) -> None:
    bridge = GuiBackendBridge(mode="auto")

    def fail_direct(payload: dict) -> dict:
        raise RuntimeError("direct failed")

    def succeed_api(payload: dict) -> dict:
        return {"source_path": payload["outcar_path"], "via": "api"}

    monkeypatch.setattr(bridge, "_call_direct", fail_direct)
    monkeypatch.setattr(bridge, "_call_api", succeed_api)

    response = bridge.summarize_outcar(outcar_path=str(FIXTURE), include_history=False)
    assert response["via"] == "api"


def test_gui_host_ui_summary_endpoint() -> None:
    app = create_gui_app(mode="direct")
    client = TestClient(app)

    response = client.post(
        "/ui/summary",
        json={"outcar_path": str(FIXTURE), "include_history": False},
    )

    assert response.status_code == 200
    assert response.json()["final_total_energy_ev"] == -10.5
