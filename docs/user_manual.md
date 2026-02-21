# pyVASP User Manual

## 1. What pyVASP does

Current capabilities:
- OUTCAR summary:
  - final energy (`TOTEN`), optional history, `E-fermi`, ionic/electronic iteration counts, final max force
- OUTCAR batch summary:
  - summarize multiple OUTCAR paths in one request with per-row error reporting
- OUTCAR batch diagnostics:
  - run convergence diagnostics over multiple OUTCAR paths in one request
- OUTCAR diagnostics:
  - external pressure, stress tensor, magnetization (`z`), convergence report
- Convergence profile:
  - per-step energy deltas and relative energies for plotting
- Ionic series profile:
  - per-step energy, force, external pressure, and Fermi energy for visualization
- Tabular export:
  - CSV export of ionic-series or convergence-profile datasets for downstream plotting
- Electronic metadata (VASPKIT-like):
  - band gap metadata from `EIGENVAL`
  - DOS metadata from `DOSCAR`
- Input generation:
  - generate `INCAR`, `KPOINTS`, `POSCAR` for relaxation from structure JSON
- Structured failure reporting:
  - stable error codes across API/UI/direct modes
  - consistent validation/parse/internal failure classes

## 2. Installation

Conda (recommended):
```bash
conda env create -f environment.yml
conda activate pyvasp
```

Pip (alternative):
```bash
python -m pip install -e .
python -m pip install -e .[dev]
```

## 3. CLI Usage

```bash
pyvasp-cli summary /absolute/path/to/OUTCAR --mode direct --include-history
pyvasp-cli batch-summary /path/A/OUTCAR /path/B/OUTCAR --mode direct
pyvasp-cli batch-diagnostics /path/A/OUTCAR /path/B/OUTCAR --mode direct --energy-tol 1e-4 --force-tol 0.02
pyvasp-cli diagnostics /absolute/path/to/OUTCAR --mode direct --energy-tol 1e-4 --force-tol 0.02
pyvasp-cli convergence-profile /absolute/path/to/OUTCAR --mode direct
pyvasp-cli ionic-series /absolute/path/to/OUTCAR --mode direct
pyvasp-cli export-tabular /absolute/path/to/OUTCAR --dataset ionic_series --delimiter comma --mode direct
pyvasp-cli electronic-metadata --eigenval-path /absolute/path/to/EIGENVAL --doscar-path /absolute/path/to/DOSCAR --mode direct
pyvasp-cli generate-relax-input /absolute/path/to/structure.json --mode direct --output-dir ./vasp_inputs
```

Execution modes:
- `direct`: in-process backend
- `api`: HTTP backend
- `auto`: direct first, fallback to API

## 4. API Usage

Start API:
```bash
pyvasp-api
```

Endpoints:
- `POST /v1/outcar/summary`
- `POST /v1/outcar/batch-summary`
- `POST /v1/outcar/batch-diagnostics`
- `POST /v1/outcar/diagnostics`
- `POST /v1/outcar/convergence-profile`
- `POST /v1/outcar/ionic-series`
- `POST /v1/outcar/export-tabular`
- `POST /v1/electronic/metadata`
- `POST /v1/input/relax-generate`

Electronic metadata request example:
```json
{
  "eigenval_path": "/absolute/path/to/EIGENVAL",
  "doscar_path": "/absolute/path/to/DOSCAR"
}
```

## 5. GUI Host Usage

Start GUI host:
```bash
pyvasp-gui
```

Open browser:
- `http://127.0.0.1:8080`

Optional runtime environment:
- `PYVASP_UI_MODE=direct|api|auto`
- `PYVASP_API_BASE_URL=http://127.0.0.1:8000`

## 6. Error Responses

API/UI error payload format:
```json
{
  "detail": {
    "code": "FILE_NOT_FOUND",
    "message": "OUTCAR file does not exist: /missing/OUTCAR",
    "details": {"field": "outcar_path", "path": "/missing/OUTCAR"}
  }
}
```

Status mapping:
- `400`: input/path validation issues
- `422`: parse or unsupported-operation issues
- `500`: unexpected internal errors

Direct CLI mode mirrors the same code via message prefix:
- `"[FILE_NOT_FOUND] OUTCAR file does not exist: ..."`

## 7. Structure JSON Format (input generation)

```json
{
  "comment": "Si2 cubic",
  "lattice_vectors": [[5.43, 0, 0], [0, 5.43, 0], [0, 0, 5.43]],
  "atoms": [
    {"element": "Si", "frac_coords": [0, 0, 0]},
    {"element": "Si", "frac_coords": [0.25, 0.25, 0.25]}
  ]
}
```

## 8. Troubleshooting

- Missing files: pass absolute paths to existing files.
- Electronic metadata requires at least one of `EIGENVAL` or `DOSCAR`.
- API mode errors: ensure backend service is running at configured URL.
