# pyVASP Developer Manual

## 1. File Tree (Phase 2)

```text
pyVASP/
  docs/
    developer_manual.md
    user_manual.md
  src/
    pyvasp/
      core/
        __init__.py
        analysis.py
        errors.py
        models.py
        payloads.py
        result.py
        validators.py
      application/
        __init__.py
        ports.py
        use_cases.py
      outcar/
        __init__.py
        parser.py
      api/
        __init__.py
        schemas.py
        routes.py
        server.py
      gui/
        __init__.py
        bridge.py
        host.py
        assets/
          index.html
          app.js
          style.css
      cli/
        __init__.py
        main.py
  tests/
    fixtures/
      OUTCAR.sample
      OUTCAR.phase2.sample
      OUTCAR.real.mmm-group
    unit/
      core/
        test_analysis.py
        test_payloads.py
      application/
        test_use_cases.py
      outcar/
        test_parser.py
    integration/
      api/
        test_outcar_summary_api.py
      gui/
        test_bridge_modes.py
      cli/
        test_cli_summary.py
  environment.yml
  pyproject.toml
  README.md
```

## 2. Layer Responsibilities

### core
- Owns domain models (`OutcarSummary`, `OutcarObservables`, `OutcarDiagnostics`, `StressTensor`, `MagnetizationSummary`).
- Owns input validation and shared payload mapping for both summary and diagnostics.
- Owns convergence algorithm (`build_convergence_report`) with no transport dependencies.

### application
- Owns transport-agnostic use-cases:
  - `SummarizeOutcarUseCase`
  - `DiagnoseOutcarUseCase`
- Depends only on parser ports, not on concrete API/GUI details.

### outcar (method module)
- Owns OUTCAR parsing routines.
- Produces core models:
  - summary extraction
  - diagnostics observables extraction (pressure, stress, magnetization)

### api
- HTTP-only adapter (FastAPI).
- Exposes endpoints and maps payloads through core validation/mapping:
  - `/v1/outcar/summary`
  - `/v1/outcar/diagnostics`

### gui
- UI-only adapter.
- Bridge supports `direct/api/auto` for both summary and diagnostics.
- Host exposes UI bridge routes:
  - `/ui/summary`
  - `/ui/diagnostics`

### cli
- Script-oriented adapter.
- Subcommands:
  - `summary`
  - `diagnostics`

## 3. Dependency Rules

Mandatory direction:
- `api/gui/cli -> application -> core/outcar`
- `outcar -> core`
- `core` imports no adapter/framework modules

Practical checks:
- No `fastapi`, `uvicorn`, browser/static modules in `core` or `application`.
- Keep transport schemas (`pydantic`) in adapter packages.

## 4. Shared Payload Contract Strategy

`core/payloads.py` is canonical for adapter request/response mapping.
- Summary:
  - `validate_summary_request()`
  - `SummaryResponsePayload.from_summary()`
- Diagnostics:
  - `validate_diagnostics_request()`
  - `DiagnosticsResponsePayload.from_diagnostics()`

This prevents drift across API, GUI, and CLI response shapes.

## 5. Extension Workflow

1. Add/adjust domain models and algorithms in `core`.
2. Add parser logic in a method module (`outcar`, future `dos`, `band`, etc.).
3. Add port + use-case in `application`.
4. Wire adapters (`api/gui/cli`) to new use-case.
5. Add unit + integration coverage.
6. Update manuals and README.

## 6. Notes on Educational Clarity

- Non-obvious parser logic (force/magnetization/stress extraction) is split into small helper methods.
- Convergence policy is explicit and centralized in core.
