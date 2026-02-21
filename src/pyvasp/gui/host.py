"""Web host for pyVASP GUI assets and bridge endpoints."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from pyvasp.gui.bridge import ExecutionMode, GuiBackendBridge


class UiSummaryRequest(BaseModel):
    """GUI bridge request schema."""

    outcar_path: str = Field(..., description="Path to OUTCAR")
    include_history: bool = Field(default=False)


class UiDiagnosticsRequest(BaseModel):
    """GUI diagnostics request schema."""

    outcar_path: str = Field(..., description="Path to OUTCAR")
    energy_tolerance_ev: float = Field(default=1e-4)
    force_tolerance_ev_per_a: float = Field(default=0.02)


class UiConfigResponse(BaseModel):
    """Exposes GUI runtime mode to static frontend."""

    mode: str
    api_base_url: str


def create_gui_app(
    *,
    mode: str | None = None,
    api_base_url: str | None = None,
) -> FastAPI:
    """Create GUI host app with configured execution mode."""

    resolved_mode = mode or os.getenv("PYVASP_UI_MODE", "auto")
    resolved_api_base = api_base_url or os.getenv("PYVASP_API_BASE_URL", "http://127.0.0.1:8000")

    bridge = GuiBackendBridge(mode=resolved_mode, api_base_url=resolved_api_base)

    app = FastAPI(title="pyVASP GUI Host", version="0.1.0")
    app.state.bridge = bridge

    assets_dir = Path(__file__).parent / "assets"
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(assets_dir / "index.html")

    @app.get("/ui/config", response_model=UiConfigResponse)
    def ui_config() -> UiConfigResponse:
        active_mode = app.state.bridge.mode
        if isinstance(active_mode, ExecutionMode):
            mode_value = active_mode.value
        else:  # pragma: no cover - defensive fallback
            mode_value = str(active_mode)
        return UiConfigResponse(mode=mode_value, api_base_url=app.state.bridge.api_base_url)

    @app.post("/ui/summary")
    def ui_summary(request: UiSummaryRequest) -> dict:
        try:
            return app.state.bridge.summarize_outcar(
                outcar_path=request.outcar_path,
                include_history=request.include_history,
            )
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/ui/diagnostics")
    def ui_diagnostics(request: UiDiagnosticsRequest) -> dict:
        try:
            return app.state.bridge.diagnose_outcar(
                outcar_path=request.outcar_path,
                energy_tolerance_ev=request.energy_tolerance_ev,
                force_tolerance_ev_per_a=request.force_tolerance_ev_per_a,
            )
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return app


def main() -> None:
    """Run GUI host service."""

    import uvicorn

    uvicorn.run("pyvasp.gui.host:create_gui_app", factory=True, host="127.0.0.1", port=8080, reload=False)


if __name__ == "__main__":
    main()
