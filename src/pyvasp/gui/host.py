"""Web host for pyVASP GUI assets and bridge endpoints."""

from __future__ import annotations

import os
from pathlib import Path
import re
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from pyvasp.gui.bridge import ExecutionMode, GuiBackendBridge


class UiSummaryRequest(BaseModel):
    """GUI summary request schema."""

    outcar_path: str = Field(..., description="Path to OUTCAR")
    include_history: bool = Field(default=False)


class UiDiagnosticsRequest(BaseModel):
    """GUI diagnostics request schema."""

    outcar_path: str = Field(..., description="Path to OUTCAR")
    energy_tolerance_ev: float = Field(default=1e-4)
    force_tolerance_ev_per_a: float = Field(default=0.02)


class UiConvergenceProfileRequest(BaseModel):
    """GUI convergence-profile request schema."""

    outcar_path: str = Field(..., description="Path to OUTCAR")


class UiIonicSeriesRequest(BaseModel):
    """GUI ionic-series request schema."""

    outcar_path: str = Field(..., description="Path to OUTCAR")


class UiElectronicMetadataRequest(BaseModel):
    """GUI electronic metadata request schema."""

    eigenval_path: str | None = Field(default=None)
    doscar_path: str | None = Field(default=None)


class UiRelaxInputRequest(BaseModel):
    """GUI relaxation-input generation request schema."""

    structure: dict[str, Any]
    kmesh: list[int] = Field(default=[6, 6, 6], min_length=3, max_length=3)
    gamma_centered: bool = True
    encut: int = 520
    ediff: float = 1e-5
    ediffg: float = -0.02
    ismear: int = 0
    sigma: float = 0.05
    ibrion: int = 2
    isif: int = 3
    nsw: int = 120
    ispin: int = 2
    magmom: str | None = None
    incar_overrides: dict[str, Any] = Field(default_factory=dict)


class UiConfigResponse(BaseModel):
    """Exposes GUI runtime mode to static frontend."""

    mode: str
    api_base_url: str


ERROR_PREFIX_RE = re.compile(r"^\[([A-Z_]+)\]\s*(.+)$")


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
        mode_value = active_mode.value if isinstance(active_mode, ExecutionMode) else str(active_mode)
        return UiConfigResponse(mode=mode_value, api_base_url=app.state.bridge.api_base_url)

    @app.post("/ui/summary")
    def ui_summary(request: UiSummaryRequest) -> dict:
        try:
            return app.state.bridge.summarize_outcar(
                outcar_path=request.outcar_path,
                include_history=request.include_history,
            )
        except Exception as exc:
            _raise_ui_http_error(exc)

    @app.post("/ui/diagnostics")
    def ui_diagnostics(request: UiDiagnosticsRequest) -> dict:
        try:
            return app.state.bridge.diagnose_outcar(
                outcar_path=request.outcar_path,
                energy_tolerance_ev=request.energy_tolerance_ev,
                force_tolerance_ev_per_a=request.force_tolerance_ev_per_a,
            )
        except Exception as exc:
            _raise_ui_http_error(exc)

    @app.post("/ui/convergence-profile")
    def ui_convergence_profile(request: UiConvergenceProfileRequest) -> dict:
        try:
            return app.state.bridge.build_convergence_profile(outcar_path=request.outcar_path)
        except Exception as exc:
            _raise_ui_http_error(exc)

    @app.post("/ui/ionic-series")
    def ui_ionic_series(request: UiIonicSeriesRequest) -> dict:
        try:
            return app.state.bridge.build_ionic_series(outcar_path=request.outcar_path)
        except Exception as exc:
            _raise_ui_http_error(exc)

    @app.post("/ui/electronic-metadata")
    def ui_electronic_metadata(request: UiElectronicMetadataRequest) -> dict:
        try:
            return app.state.bridge.parse_electronic_metadata(
                eigenval_path=request.eigenval_path,
                doscar_path=request.doscar_path,
            )
        except Exception as exc:
            _raise_ui_http_error(exc)

    @app.post("/ui/generate-relax-input")
    def ui_generate_relax_input(request: UiRelaxInputRequest) -> dict:
        try:
            return app.state.bridge.generate_relax_input(
                structure=request.structure,
                kmesh=(request.kmesh[0], request.kmesh[1], request.kmesh[2]),
                gamma_centered=request.gamma_centered,
                encut=request.encut,
                ediff=request.ediff,
                ediffg=request.ediffg,
                ismear=request.ismear,
                sigma=request.sigma,
                ibrion=request.ibrion,
                isif=request.isif,
                nsw=request.nsw,
                ispin=request.ispin,
                magmom=request.magmom,
                incar_overrides=request.incar_overrides,
            )
        except Exception as exc:
            _raise_ui_http_error(exc)

    return app


def main() -> None:
    """Run GUI host service."""

    import uvicorn

    uvicorn.run("pyvasp.gui.host:create_gui_app", factory=True, host="127.0.0.1", port=8080, reload=False)


def _raise_ui_http_error(exc: Exception) -> None:
    message = str(exc)
    code = "INTERNAL_ERROR"

    prefixed = ERROR_PREFIX_RE.match(message)
    if prefixed:
        code = prefixed.group(1)
        message = prefixed.group(2)

    status_code = 422
    if code in {"VALIDATION_ERROR", "FILE_NOT_FOUND", "FILE_NOT_FILE"}:
        status_code = 400
    elif code == "INTERNAL_ERROR":
        status_code = 500

    raise HTTPException(status_code=status_code, detail={"code": code, "message": message}) from exc


if __name__ == "__main__":
    main()
