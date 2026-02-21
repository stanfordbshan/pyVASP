# pyVASP Developer Manual

## 1. File Tree (Phase 3 + Electronic Parsing)

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
      EIGENVAL.sample
      DOSCAR.sample
      DOSCAR.spin.sample
      structure.si2.json
    unit/
      core/
        test_analysis.py
        test_payloads.py
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

### application
- Transport-agnostic use-cases:
  - `SummarizeOutcarUseCase`
  - `DiagnoseOutcarUseCase`
  - `BuildConvergenceProfileUseCase`
  - `ParseElectronicMetadataUseCase`
  - `GenerateRelaxInputUseCase`

### method modules
- `outcar`: OUTCAR parsing.
- `electronic`: `EIGENVAL`/`DOSCAR` parsing for band-gap and DOS metadata.
- `inputgen`: INCAR/KPOINTS/POSCAR generation.

### adapters
- `api`: HTTP endpoints only.
- `gui`: host + bridge for direct/api/auto execution.
- `cli`: script-oriented command surface.

## 3. Dependency Rules

Mandatory direction:
- `api/gui/cli -> application -> core/outcar/electronic/inputgen`
- `outcar/electronic/inputgen -> core`
- `core` imports no API/UI framework modules

## 4. Shared Payload Contract Strategy

`core/payloads.py` is canonical for request validation + response mapping.

All adapter entry points call core validators first:
- summary
- diagnostics
- convergence profile
- electronic metadata
- relaxation input generation

## 5. Extension Workflow

1. Add domain model + validation in `core`.
2. Add parsing/generation logic in a method module.
3. Add use-case + port in `application`.
4. Wire API/GUI/CLI adapters.
5. Add unit + integration tests.
6. Update docs.

## 6. Notes on Educational Clarity

- Parsing logic is separated by output type (OUTCAR vs EIGENVAL/DOSCAR).
- Adapter surfaces stay thin; orchestration and mapping happen in application/core.
