# pyVASP Developer Manual

## 1. File Tree (Phase 6 + Batch Discovery Workflow)

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
        tabular.py
        validators.py
      application/
        __init__.py
        ports.py
        use_cases.py
      outcar/
        __init__.py
        parser.py
      electronic/
        __init__.py
        parser.py
      inputgen/
        __init__.py
        generator.py
      api/
        __init__.py
        schemas.py
        routes.py
        server.py
      gui/
        __init__.py
        bridge.py
        host.py
        launcher.py
        assets/
          index.html
          app.js
          style.css
      cli/
        __init__.py
        main.py
  tests/
    fixtures/
      discovery_root/
        run_a/OUTCAR
        group/run_b/OUTCAR
      OUTCAR.sample
      OUTCAR.phase2.sample
      OUTCAR.real.mmm-group
      EIGENVAL.sample
      DOSCAR.sample
      DOSCAR.spin.sample
      structure.si2.json
    unit/
      core/
        test_analysis.py
        test_errors.py
        test_payloads.py
        test_tabular.py
      application/
        test_use_cases.py
      outcar/
        test_parser.py
      electronic/
        test_electronic_parser.py
      inputgen/
        test_generator.py
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
- Domain models for OUTCAR, electronic metadata, and input generation.
- Shared payload mapping/validation for all adapter contracts.
- Core analysis algorithms for convergence report/profile.
- Canonical error taxonomy (`ErrorCode`, `AppError`) and error normalization.

### application
- Transport-agnostic use-cases:
  - `SummarizeOutcarUseCase`
  - `BatchSummarizeOutcarUseCase`
  - `DiscoverOutcarRunsUseCase`
  - `BatchDiagnoseOutcarUseCase`
  - `DiagnoseOutcarUseCase`
  - `BuildConvergenceProfileUseCase`
  - `BuildIonicSeriesUseCase`
  - `ExportOutcarTabularUseCase`
  - `ParseElectronicMetadataUseCase`
  - `BuildDosProfileUseCase`
  - `GenerateRelaxInputUseCase`
- Use-cases return `AppResult` with structured `AppError` failures; no adapter-specific error format.

### method modules
- `outcar`: OUTCAR parsing.
- `electronic`: `EIGENVAL`/`DOSCAR` parsing for band-gap metadata, DOS metadata, and DOS profile points.
- `inputgen`: INCAR/KPOINTS/POSCAR generation.

### adapters
- `api`: HTTP endpoints only.
- `gui`: host + bridge for direct/api/auto execution.
- `cli`: script-oriented command surface.
- Adapters map `AppError` into transport format (HTTP/JSON or runtime UI/CLI message).

## 3. Dependency Rules

Mandatory direction:
- `api/gui/cli -> application -> core/outcar/electronic/inputgen`
- `outcar/electronic/inputgen -> core`
- `core` imports no API/UI framework modules

## 4. Shared Payload Contract Strategy

`core/payloads.py` is canonical for request validation + response mapping.

All adapter entry points call core validators first:
- summary
- outcar discovery
- batch summary
- batch diagnostics
- diagnostics
- convergence profile
- ionic series
- outcar tabular export
- electronic metadata
- DOS profile
- relaxation input generation

Validation hardening examples:
- finite numeric enforcement
- k-point mesh upper-bound checks
- non-zero lattice vector checks
- constrained INCAR override keys

## 5. Error Contract Strategy

`core/errors.py` defines stable transport-neutral errors:
- `ErrorCode`: machine-readable code enum.
- `AppError`: canonical structured error payload (`code`, `message`, optional `details`).
- `normalize_error(...)`: converts exceptions into stable `AppError`.

Adapter mapping policy:
- API maps `AppError` to `HTTPException(detail={code,message,details?})`.
- GUI host mirrors the same structure and status policy for `/ui/*` endpoints.
- CLI prints message strings, preserving prefixed error code in direct mode.

## 6. Extension Workflow

1. Add domain model + validation in `core`.
2. Add parsing/generation logic in a method module.
3. Add use-case + port in `application`.
4. Wire API/GUI/CLI adapters.
5. Add unit + integration tests.
6. Update docs.

## 7. Notes on Educational Clarity

- Parsing logic is separated by output type (OUTCAR vs EIGENVAL/DOSCAR).
- Adapter surfaces stay thin; orchestration and mapping happen in application/core.
