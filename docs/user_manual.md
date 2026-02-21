# pyVASP User Manual

## 1. What pyVASP does (Phase 1)

Phase 1 provides OUTCAR post-processing summary capabilities:
- final total energy (`TOTEN`)
- optional energy history
- final Fermi energy (`E-fermi`)
- ionic step count
- electronic iteration count
- final max force estimate from `TOTAL-FORCE`

## 2. Installation

```bash
python -m pip install -e .
python -m pip install -e .[dev]
```

## 3. CLI Usage

### Direct mode

```bash
pyvasp-cli summary /absolute/path/to/OUTCAR --mode direct
```

### API mode

Start API backend:
```bash
pyvasp-api
```

Run CLI through HTTP:
```bash
pyvasp-cli summary /absolute/path/to/OUTCAR --mode api --api-base-url http://127.0.0.1:8000
```

### Auto mode

```bash
pyvasp-cli summary /absolute/path/to/OUTCAR --mode auto --api-base-url http://127.0.0.1:8000
```

## 4. API Usage

Start API:
```bash
pyvasp-api
```

Request:
```bash
curl -X POST http://127.0.0.1:8000/v1/outcar/summary \
  -H "Content-Type: application/json" \
  -d '{"outcar_path":"/absolute/path/to/OUTCAR","include_history":true}'
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

- `OUTCAR file does not exist`: pass an absolute path to an existing file.
- API mode connection errors: ensure `pyvasp-api` is running and `api_base_url` is correct.
- If no `TOTEN` data appears, verify the OUTCAR contains completed ionic/electronic steps.
