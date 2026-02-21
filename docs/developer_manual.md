# pyVASP Developer Manual

## 1. File Tree (Phase 1)

```text
pyVASP/
  docs/
    developer_manual.md
    user_manual.md
  src/
    pyvasp/
      __init__.py
      core/
        __init__.py
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
    unit/
      core/
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
  pyproject.toml
  README.md
```

## 2. Layer Responsibilities

### core
- Owns domain model (`OutcarSummary`, `EnergyPoint`), error types, generic result object.
- Owns shared mapping and validation (`SummaryRequestPayload`, `SummaryResponsePayload`).
- No framework imports.

### application
- Owns use-cases/orchestration only (`SummarizeOutcarUseCase`).
- Depends on parser port (`OutcarSummaryReader`) instead of concrete adapter details.

### outcar (method module)
- Owns OUTCAR-specific parsing algorithm.
- Produces pure domain models for application layer.

### api
- HTTP-only adapter.
- Uses FastAPI schemas and routes; maps request/response through core payload module to prevent drift.

### gui
- UI-only adapter.
- `GuiBackendBridge` supports `direct`, `api`, and `auto` execution modes.
- `host.py` serves static assets and delegates to bridge.

### cli
- Script-oriented adapter.
- Reuses GUI bridge contract; no business logic.

## 3. Dependency Rules

Mandatory direction:
- `api/gui/cli -> application -> core/outcar`
- `outcar -> core`
- `core` imports no adapter/framework modules

Practical checks:
- Do not import `fastapi`, `uvicorn`, browser/static toolkits, or CLI libs in `core`/`application`.
- Keep transport schemas (`pydantic`) in adapter packages only.

## 4. Shared Payload Contract Strategy

`core/payloads.py` is the canonical adapter contract.
- `validate_summary_request()` normalizes and validates incoming payloads.
- `SummaryResponsePayload.from_summary()` provides one canonical response mapping.

This prevents contract drift between API, GUI, and CLI adapters.

## 5. Extension Workflow

1. Add a new domain model/result in `core`.
2. Add method logic in a method module (e.g. `src/pyvasp/dos`, `src/pyvasp/band`).
3. Expose a new port/use-case in `application`.
4. Wire adapters:
   - API route/schema in `api`
   - GUI bridge endpoint/view in `gui`
   - CLI command in `cli`
5. Add tests in both unit and integration layers.
6. Document new behavior in README + user manual.

## 6. Notes on Educational Clarity

- Domain and use-case files include focused docstrings.
- Non-obvious parsing logic (force block scanning, regex normalization) is explicitly segmented into helper methods.
