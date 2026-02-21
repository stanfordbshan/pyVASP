from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from pyvasp.api.server import create_app


FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "OUTCAR.sample"


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
    assert "does not exist" in response.json()["detail"]
