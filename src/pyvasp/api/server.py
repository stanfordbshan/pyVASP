"""FastAPI server bootstrap for pyVASP HTTP adapter."""

from __future__ import annotations

from fastapi import FastAPI

from pyvasp.api.routes import create_router
from pyvasp.application.use_cases import (
    BuildConvergenceProfileUseCase,
    BuildIonicSeriesUseCase,
    DiagnoseOutcarUseCase,
    GenerateRelaxInputUseCase,
    ParseElectronicMetadataUseCase,
    SummarizeOutcarUseCase,
)
from pyvasp.electronic.parser import ElectronicParser
from pyvasp.inputgen.generator import RelaxInputGenerator
from pyvasp.outcar.parser import OutcarParser


def create_app() -> FastAPI:
    """Create configured FastAPI application instance."""

    outcar_parser = OutcarParser()
    summary_use_case = SummarizeOutcarUseCase(reader=outcar_parser)
    diagnostics_use_case = DiagnoseOutcarUseCase(reader=outcar_parser)
    profile_use_case = BuildConvergenceProfileUseCase(reader=outcar_parser)
    ionic_series_use_case = BuildIonicSeriesUseCase(reader=outcar_parser)
    electronic_use_case = ParseElectronicMetadataUseCase(reader=ElectronicParser())
    relax_input_use_case = GenerateRelaxInputUseCase(builder=RelaxInputGenerator())

    app = FastAPI(
        title="pyVASP API",
        version="0.1.0",
        description="Layered API for VASP input generation and post-processing workflows.",
    )
    app.include_router(
        create_router(
            summary_use_case,
            diagnostics_use_case,
            profile_use_case,
            ionic_series_use_case,
            electronic_use_case,
            relax_input_use_case,
        )
    )

    return app


def main() -> None:
    """Run API server using uvicorn."""

    import uvicorn

    uvicorn.run("pyvasp.api.server:create_app", factory=True, host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
