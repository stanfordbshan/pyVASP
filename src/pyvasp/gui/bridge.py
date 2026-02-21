"""GUI-side backend bridge with direct/api/auto execution modes."""

from __future__ import annotations

import json
from enum import Enum
from typing import Callable
from urllib import error, request

from pyvasp.application.use_cases import DiagnoseOutcarUseCase, SummarizeOutcarUseCase
from pyvasp.core.payloads import validate_diagnostics_request, validate_summary_request
from pyvasp.outcar.parser import OutcarParser


class ExecutionMode(str, Enum):
    """Supported GUI backend connection strategies."""

    DIRECT = "direct"
    API = "api"
    AUTO = "auto"


class GuiBackendBridge:
    """Transport adapter that shields UI code from backend transport details."""

    def __init__(
        self,
        *,
        mode: str = "auto",
        api_base_url: str = "http://127.0.0.1:8000",
        summary_use_case: SummarizeOutcarUseCase | None = None,
        diagnostics_use_case: DiagnoseOutcarUseCase | None = None,
    ) -> None:
        self.mode = ExecutionMode(mode)
        self.api_base_url = api_base_url.rstrip("/")

        parser = OutcarParser()
        self._summary_use_case = summary_use_case or SummarizeOutcarUseCase(reader=parser)
        self._diagnostics_use_case = diagnostics_use_case or DiagnoseOutcarUseCase(reader=parser)

    def summarize_outcar(self, *, outcar_path: str, include_history: bool = False) -> dict:
        """Summarize an OUTCAR using the configured execution mode."""

        payload = {
            "outcar_path": outcar_path,
            "include_history": include_history,
        }
        return self._execute(
            payload=payload,
            api_path="/v1/outcar/summary",
            direct_call=self._call_direct_summary,
            operation_label="summary",
        )

    def diagnose_outcar(
        self,
        *,
        outcar_path: str,
        energy_tolerance_ev: float = 1e-4,
        force_tolerance_ev_per_a: float = 0.02,
    ) -> dict:
        """Run convergence/stress/magnetization diagnostics for an OUTCAR."""

        payload = {
            "outcar_path": outcar_path,
            "energy_tolerance_ev": energy_tolerance_ev,
            "force_tolerance_ev_per_a": force_tolerance_ev_per_a,
        }
        return self._execute(
            payload=payload,
            api_path="/v1/outcar/diagnostics",
            direct_call=self._call_direct_diagnostics,
            operation_label="diagnostics",
        )

    def _execute(
        self,
        *,
        payload: dict,
        api_path: str,
        direct_call: Callable[[dict], dict],
        operation_label: str,
    ) -> dict:
        if self.mode is ExecutionMode.DIRECT:
            return direct_call(payload)
        if self.mode is ExecutionMode.API:
            return self._call_api(api_path=api_path, payload=payload)

        direct_error: Exception | None = None
        try:
            return direct_call(payload)
        except Exception as exc:  # pragma: no cover - exercised via integration path
            direct_error = exc

        try:
            return self._call_api(api_path=api_path, payload=payload)
        except Exception as api_exc:
            if direct_error is None:
                raise RuntimeError(f"Auto mode failed: {operation_label} direct/API execution both failed") from api_exc
            raise RuntimeError(
                f"Auto mode failed for {operation_label}: direct={direct_error}; api={api_exc}"
            ) from api_exc

    def _call_direct_summary(self, payload: dict) -> dict:
        canonical = validate_summary_request(payload)
        result = self._summary_use_case.execute(canonical)
        if not result.ok or result.value is None:
            raise RuntimeError(result.error or "Unknown direct summary error")
        return result.value.to_mapping()

    def _call_direct_diagnostics(self, payload: dict) -> dict:
        canonical = validate_diagnostics_request(payload)
        result = self._diagnostics_use_case.execute(canonical)
        if not result.ok or result.value is None:
            raise RuntimeError(result.error or "Unknown direct diagnostics error")
        return result.value.to_mapping()

    def _call_api(self, *, api_path: str, payload: dict) -> dict:
        endpoint = f"{self.api_base_url}{api_path}"
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=10) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"API request failed ({exc.code}): {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"API request failed: {exc.reason}") from exc

        return json.loads(raw)
