# pyVASP User Manual

## 1. What pyVASP does (Phase 2)

Current capabilities:
- OUTCAR summary:
  - final total energy (`TOTEN`)
  - optional energy history
  - final Fermi energy (`E-fermi`)
  - ionic step and electronic iteration counts
  - final max force estimate from `TOTAL-FORCE`
- OUTCAR diagnostics:
  - external pressure (`kB`)
  - stress tensor (`in kB` line)
  - final `magnetization (z)` table
  - convergence assessment (`|ΔE|` and max force thresholds)

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

### Summary

```bash
pyvasp-cli summary /absolute/path/to/OUTCAR --mode direct --include-history
```

### Diagnostics

```bash
pyvasp-cli diagnostics /absolute/path/to/OUTCAR --mode direct --energy-tol 1e-4 --force-tol 0.02
```

Modes:
- `direct`: in-process backend
- `api`: call HTTP backend
- `auto`: try direct, fallback to API

## 4. API Usage

Start API:
```bash
pyvasp-api
```

Summary request:
```bash
curl -X POST http://127.0.0.1:8000/v1/outcar/summary \
  -H "Content-Type: application/json" \
  -d '{"outcar_path":"/absolute/path/to/OUTCAR","include_history":true}'
```

Diagnostics request:
```bash
curl -X POST http://127.0.0.1:8000/v1/outcar/diagnostics \
  -H "Content-Type: application/json" \
  -d '{"outcar_path":"/absolute/path/to/OUTCAR","energy_tolerance_ev":0.0001,"force_tolerance_ev_per_a":0.02}'
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

## 6. Troubleshooting

- `OUTCAR file does not exist`: use an absolute path to an existing file.
- API mode connection errors: ensure backend is running and API URL is correct.
- Missing diagnostics fields: some OUTCARs omit stress/magnetization blocks, reported in `warnings`.
