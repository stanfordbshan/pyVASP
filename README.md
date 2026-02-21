# pyVASP

pyVASP is a layered Python toolkit for VASP input generation, post-processing, and visualization workflows.

Phase 1-2 implemented a strict backend-first architecture and common OUTCAR post-processing features inspired by practical VASPKIT workflows:
- energy/iteration summary: `TOTEN`, `E-fermi`, ionic steps, electronic iterations, max force
- diagnostics: external pressure, stress tensor (`in kB`), final `magnetization (z)` table
- convergence assessment using configurable energy/force tolerances

## Architecture (strict layering)

- `src/pyvasp/core`: domain models, validation, result wrappers, shared payload mapping, convergence logic
- `src/pyvasp/application`: transport-agnostic use-cases and ports
- `src/pyvasp/outcar`: OUTCAR method module (parsing algorithms)
- `src/pyvasp/api`: HTTP adapter only (FastAPI schemas/routes/bootstrap)
- `src/pyvasp/gui`: UI adapter only (web host + direct/api/auto bridge)
- `src/pyvasp/gui/assets`: frontend static assets
- `src/pyvasp/cli`: CLI adapter (contract surface for scripting)

Dependency direction:
- adapters (`api/gui/cli`) -> `application` -> (`core` + method modules)
- `core` and method modules do not import API/UI frameworks

## Install

Conda (recommended):
```bash
conda env create -f environment.yml
conda activate pyvasp
```

`environment.yml` includes `ase` because it is a common VASP ecosystem dependency and useful for near-term input-generation/post-processing extensions.

Pip (alternative):
```bash
python -m pip install -e .
python -m pip install -e .[dev]
```

## CLI

Summary:
```bash
pyvasp-cli summary /absolute/path/to/OUTCAR --mode direct --include-history
```

Diagnostics:
```bash
pyvasp-cli diagnostics /absolute/path/to/OUTCAR --mode direct --energy-tol 1e-4 --force-tol 0.02
```

Modes:
- `direct`: in-process backend calls (no HTTP)
- `api`: remote HTTP backend
- `auto`: direct first, fallback to API

## API

Start API backend:
```bash
pyvasp-api
```

Endpoints:
- `POST /v1/outcar/summary`
- `POST /v1/outcar/diagnostics`

Diagnostics request example:
```json
{
  "outcar_path": "/absolute/path/to/OUTCAR",
  "energy_tolerance_ev": 0.0001,
  "force_tolerance_ev_per_a": 0.02
}
```

## GUI Host

Start GUI host:
```bash
pyvasp-gui
```

Open:
- `http://127.0.0.1:8080`

Runtime env vars:
- `PYVASP_UI_MODE=direct|api|auto`
- `PYVASP_API_BASE_URL=http://127.0.0.1:8000`

## Tests

```bash
pytest
```

Coverage includes:
- unit tests for `core`, `application`, and `outcar`
- integration tests for API, GUI bridge/host, and CLI contract paths

## Documentation

- Developer manual: `docs/developer_manual.md`
- User manual: `docs/user_manual.md`
