"""FastAPI server bootstrap for pyVASP HTTP adapter."""

from __future__ import annotations

from fastapi import FastAPI

from pyvasp.api.routes import create_router
from pyvasp.application.use_cases import DiagnoseOutcarUseCase, SummarizeOutcarUseCase
from pyvasp.outcar.parser import OutcarParser


def create_app() -> FastAPI:
    """Create configured FastAPI application instance."""

    parser = OutcarParser()
    summary_use_case = SummarizeOutcarUseCase(reader=parser)
    diagnostics_use_case = DiagnoseOutcarUseCase(reader=parser)

    app = FastAPI(
        title="pyVASP API",
        version="0.1.0",
        description="Layered API for VASP OUTCAR post-processing and visualization backends.",
    )
    app.include_router(create_router(summary_use_case, diagnostics_use_case))

    return app


def main() -> None:
    """Run API server using uvicorn."""

    import uvicorn

    uvicorn.run("pyvasp.api.server:create_app", factory=True, host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
