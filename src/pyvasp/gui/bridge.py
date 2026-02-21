"""GUI-side backend bridge with direct/api/auto execution modes."""

from __future__ import annotations

import json
from enum import Enum
from urllib import error, request

from pyvasp.application.use_cases import SummarizeOutcarUseCase
from pyvasp.core.payloads import validate_summary_request
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
        use_case: SummarizeOutcarUseCase | None = None,
    ) -> None:
        self.mode = ExecutionMode(mode)
        self.api_base_url = api_base_url.rstrip("/")
        self._use_case = use_case or SummarizeOutcarUseCase(reader=OutcarParser())

    def summarize_outcar(self, *, outcar_path: str, include_history: bool = False) -> dict:
        """Summarize an OUTCAR using the configured execution mode."""

        payload = {
            "outcar_path": outcar_path,
            "include_history": include_history,
        }

        if self.mode is ExecutionMode.DIRECT:
            return self._call_direct(payload)
        if self.mode is ExecutionMode.API:
            return self._call_api(payload)

        direct_error: Exception | None = None
        try:
            return self._call_direct(payload)
        except Exception as exc:  # pragma: no cover - exercised via integration path
            direct_error = exc

        try:
            return self._call_api(payload)
        except Exception as api_exc:
            if direct_error is None:
                raise RuntimeError("Auto mode failed: direct and API execution both failed") from api_exc
            raise RuntimeError(f"Auto mode failed: direct={direct_error}; api={api_exc}") from api_exc

    def _call_direct(self, payload: dict) -> dict:
        canonical = validate_summary_request(payload)
        result = self._use_case.execute(canonical)
        if not result.ok or result.value is None:
            raise RuntimeError(result.error or "Unknown direct execution error")
        return result.value.to_mapping()

    def _call_api(self, payload: dict) -> dict:
        endpoint = f"{self.api_base_url}/v1/outcar/summary"
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
