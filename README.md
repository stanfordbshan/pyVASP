# pyVASP

pyVASP is a layered Python toolkit for VASP input generation, post-processing, and visualization workflows.

Phase 1-4.3 capabilities now include:
- OUTCAR summary and diagnostics (energy/force/pressure/stress/magnetization/convergence)
- convergence profile output for chart-ready visualization
- ionic-step series output for multi-metric visualization:
  - per-step energy, force, external pressure, and Fermi energy
- tabular export for plotting/reporting:
  - CSV export of `ionic_series` and `convergence_profile` datasets
- relaxation input generation (`INCAR`, `KPOINTS`, `POSCAR`)
- VASPKIT-like electronic parsing from standard outputs:
  - band gap metadata from `EIGENVAL`
  - DOS metadata from `DOSCAR`
- hardened structured errors across direct/API/UI flows:
  - stable machine-readable error codes
  - consistent HTTP/detail mapping for adapters

## Architecture (strict layering)

- `src/pyvasp/core`: domain models, validation, payload mapping, analysis
- `src/pyvasp/application`: transport-agnostic use-cases and ports
- `src/pyvasp/outcar`: OUTCAR parser module
- `src/pyvasp/inputgen`: input-generation module
- `src/pyvasp/electronic`: EIGENVAL/DOSCAR parser module
- `src/pyvasp/api`: HTTP adapter only
- `src/pyvasp/gui`: UI adapter only (host + direct/api/auto bridge)
- `src/pyvasp/cli`: CLI adapter

Dependency direction:
- adapters (`api/gui/cli`) -> `application` -> (`core` + method modules)
- `core` and method modules do not import API/UI frameworks

## Install

Conda (recommended):
```bash
conda env create -f environment.yml
conda activate pyvasp
```

`environment.yml` includes `ase` as a standard VASP ecosystem dependency.

Pip (alternative):
```bash
python -m pip install -e .
python -m pip install -e .[dev]
```

## CLI

```bash
pyvasp-cli summary /absolute/path/to/OUTCAR --mode direct --include-history
pyvasp-cli diagnostics /absolute/path/to/OUTCAR --mode direct --energy-tol 1e-4 --force-tol 0.02
pyvasp-cli convergence-profile /absolute/path/to/OUTCAR --mode direct
pyvasp-cli ionic-series /absolute/path/to/OUTCAR --mode direct
pyvasp-cli export-tabular /absolute/path/to/OUTCAR --dataset ionic_series --delimiter comma --mode direct
pyvasp-cli electronic-metadata --eigenval-path /path/to/EIGENVAL --doscar-path /path/to/DOSCAR --mode direct
pyvasp-cli generate-relax-input /absolute/path/to/structure.json --mode direct --output-dir ./vasp_inputs
```

Modes:
- `direct`: in-process backend calls
- `api`: remote HTTP backend calls
- `auto`: direct first, fallback to API

## API

Start backend:
```bash
pyvasp-api
```

Endpoints:
- `POST /v1/outcar/summary`
- `POST /v1/outcar/diagnostics`
- `POST /v1/outcar/convergence-profile`
- `POST /v1/outcar/ionic-series`
- `POST /v1/outcar/export-tabular`
- `POST /v1/electronic/metadata`
- `POST /v1/input/relax-generate`

Error response contract:
- `detail.code`: stable error code (for example `VALIDATION_ERROR`, `FILE_NOT_FOUND`, `PARSE_ERROR`)
- `detail.message`: human-readable explanation
- `detail.details` (optional): structured context (field/path metadata)

Status mapping:
- `400`: request/path validation errors (`VALIDATION_ERROR`, `FILE_NOT_FOUND`, `FILE_NOT_FILE`)
- `422`: parse/semantic operation errors (`PARSE_ERROR`, `IO_ERROR`, `UNSUPPORTED_OPERATION`)
- `500`: unexpected internal failures (`INTERNAL_ERROR`)

## GUI Host

Start GUI host:
```bash
pyvasp-gui
```

Open: `http://127.0.0.1:8080`

Runtime env vars:
- `PYVASP_UI_MODE=direct|api|auto`
- `PYVASP_API_BASE_URL=http://127.0.0.1:8000`

## Tests

```bash
pytest
```

Coverage includes unit/integration tests across core, application, adapters, and method modules.

## Documentation

- Developer manual: `docs/developer_manual.md`
- User manual: `docs/user_manual.md`
