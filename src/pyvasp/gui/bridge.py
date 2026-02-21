"""GUI-side backend bridge with direct/api/auto execution modes."""

from __future__ import annotations

import json
from enum import Enum
from typing import Callable
from urllib import error, request

from pyvasp.application.use_cases import (
    BatchDiagnoseOutcarUseCase,
    BatchSummarizeOutcarUseCase,
    BuildBatchInsightsUseCase,
    BuildConvergenceProfileUseCase,
    BuildDosProfileUseCase,
    BuildIonicSeriesUseCase,
    DiagnoseOutcarUseCase,
    DiscoverOutcarRunsUseCase,
    ExportOutcarTabularUseCase,
    GenerateRelaxInputUseCase,
    ParseElectronicMetadataUseCase,
    SummarizeOutcarUseCase,
)
from pyvasp.core.payloads import (
    validate_batch_diagnostics_request,
    validate_batch_insights_request,
    validate_batch_summary_request,
    validate_convergence_profile_request,
    validate_discover_outcar_runs_request,
    validate_diagnostics_request,
    validate_dos_profile_request,
    validate_electronic_metadata_request,
    validate_export_tabular_request,
    validate_generate_relax_input_request,
    validate_ionic_series_request,
    validate_summary_request,
)
from pyvasp.core.errors import AppError, normalize_error
from pyvasp.electronic.parser import ElectronicParser
from pyvasp.inputgen.generator import RelaxInputGenerator
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
        discover_outcar_runs_use_case: DiscoverOutcarRunsUseCase | None = None,
        batch_summary_use_case: BatchSummarizeOutcarUseCase | None = None,
        batch_diagnostics_use_case: BatchDiagnoseOutcarUseCase | None = None,
        batch_insights_use_case: BuildBatchInsightsUseCase | None = None,
        diagnostics_use_case: DiagnoseOutcarUseCase | None = None,
        profile_use_case: BuildConvergenceProfileUseCase | None = None,
        ionic_series_use_case: BuildIonicSeriesUseCase | None = None,
        export_tabular_use_case: ExportOutcarTabularUseCase | None = None,
        electronic_use_case: ParseElectronicMetadataUseCase | None = None,
        dos_profile_use_case: BuildDosProfileUseCase | None = None,
        relax_input_use_case: GenerateRelaxInputUseCase | None = None,
    ) -> None:
        self.mode = ExecutionMode(mode)
        self.api_base_url = api_base_url.rstrip("/")

        outcar_parser = OutcarParser()
        electronic_parser = ElectronicParser()
        self._summary_use_case = summary_use_case or SummarizeOutcarUseCase(reader=outcar_parser)
        self._discover_outcar_runs_use_case = discover_outcar_runs_use_case or DiscoverOutcarRunsUseCase()
        self._batch_summary_use_case = batch_summary_use_case or BatchSummarizeOutcarUseCase(reader=outcar_parser)
        self._batch_diagnostics_use_case = (
            batch_diagnostics_use_case or BatchDiagnoseOutcarUseCase(reader=outcar_parser)
        )
        self._batch_insights_use_case = batch_insights_use_case or BuildBatchInsightsUseCase(reader=outcar_parser)
        self._diagnostics_use_case = diagnostics_use_case or DiagnoseOutcarUseCase(reader=outcar_parser)
        self._profile_use_case = profile_use_case or BuildConvergenceProfileUseCase(reader=outcar_parser)
        self._ionic_series_use_case = ionic_series_use_case or BuildIonicSeriesUseCase(reader=outcar_parser)
        self._export_tabular_use_case = export_tabular_use_case or ExportOutcarTabularUseCase(
            summary_reader=outcar_parser,
            ionic_series_reader=outcar_parser,
        )
        self._electronic_use_case = electronic_use_case or ParseElectronicMetadataUseCase(reader=electronic_parser)
        self._dos_profile_use_case = dos_profile_use_case or BuildDosProfileUseCase(reader=electronic_parser)
        self._relax_input_use_case = relax_input_use_case or GenerateRelaxInputUseCase(builder=RelaxInputGenerator())

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

    def batch_summarize_outcars(
        self,
        *,
        outcar_paths: list[str],
        fail_fast: bool = False,
    ) -> dict:
        """Summarize multiple OUTCAR files in one execution call."""

        payload = {
            "outcar_paths": list(outcar_paths),
            "fail_fast": fail_fast,
        }
        return self._execute(
            payload=payload,
            api_path="/v1/outcar/batch-summary",
            direct_call=self._call_direct_batch_summary,
            operation_label="batch summary",
        )

    def discover_outcar_runs(
        self,
        *,
        root_dir: str,
        recursive: bool = True,
        max_runs: int = 200,
    ) -> dict:
        """Discover OUTCAR run paths from a root directory."""

        payload = {
            "root_dir": root_dir,
            "recursive": recursive,
            "max_runs": max_runs,
        }
        return self._execute(
            payload=payload,
            api_path="/v1/outcar/discover",
            direct_call=self._call_direct_discover_outcar_runs,
            operation_label="OUTCAR discovery",
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

    def batch_diagnose_outcars(
        self,
        *,
        outcar_paths: list[str],
        energy_tolerance_ev: float = 1e-4,
        force_tolerance_ev_per_a: float = 0.02,
        fail_fast: bool = False,
    ) -> dict:
        """Run diagnostics for multiple OUTCAR files in one execution call."""

        payload = {
            "outcar_paths": list(outcar_paths),
            "energy_tolerance_ev": energy_tolerance_ev,
            "force_tolerance_ev_per_a": force_tolerance_ev_per_a,
            "fail_fast": fail_fast,
        }
        return self._execute(
            payload=payload,
            api_path="/v1/outcar/batch-diagnostics",
            direct_call=self._call_direct_batch_diagnostics,
            operation_label="batch diagnostics",
        )

    def batch_insights_outcars(
        self,
        *,
        outcar_paths: list[str],
        energy_tolerance_ev: float = 1e-4,
        force_tolerance_ev_per_a: float = 0.02,
        top_n: int = 5,
        fail_fast: bool = False,
    ) -> dict:
        """Build aggregate screening insights for multiple OUTCAR files."""

        payload = {
            "outcar_paths": list(outcar_paths),
            "energy_tolerance_ev": energy_tolerance_ev,
            "force_tolerance_ev_per_a": force_tolerance_ev_per_a,
            "top_n": top_n,
            "fail_fast": fail_fast,
        }
        return self._execute(
            payload=payload,
            api_path="/v1/outcar/batch-insights",
            direct_call=self._call_direct_batch_insights,
            operation_label="batch insights",
        )

    def build_convergence_profile(self, *, outcar_path: str) -> dict:
        """Build chart-ready convergence profile for an OUTCAR."""

        payload = {"outcar_path": outcar_path}
        return self._execute(
            payload=payload,
            api_path="/v1/outcar/convergence-profile",
            direct_call=self._call_direct_profile,
            operation_label="convergence profile",
        )

    def build_ionic_series(self, *, outcar_path: str) -> dict:
        """Build per-step multi-metric ionic series for an OUTCAR."""

        payload = {"outcar_path": outcar_path}
        return self._execute(
            payload=payload,
            api_path="/v1/outcar/ionic-series",
            direct_call=self._call_direct_ionic_series,
            operation_label="ionic series",
        )

    def parse_electronic_metadata(
        self,
        *,
        eigenval_path: str | None = None,
        doscar_path: str | None = None,
    ) -> dict:
        """Parse VASPKIT-like electronic metadata from EIGENVAL and DOSCAR."""

        payload = {
            "eigenval_path": eigenval_path,
            "doscar_path": doscar_path,
        }
        return self._execute(
            payload=payload,
            api_path="/v1/electronic/metadata",
            direct_call=self._call_direct_electronic_metadata,
            operation_label="electronic metadata",
        )

    def parse_dos_profile(
        self,
        *,
        doscar_path: str,
        energy_window_ev: float = 5.0,
        max_points: int = 400,
    ) -> dict:
        """Parse chart-ready total DOS profile from DOSCAR."""

        payload = {
            "doscar_path": doscar_path,
            "energy_window_ev": energy_window_ev,
            "max_points": max_points,
        }
        return self._execute(
            payload=payload,
            api_path="/v1/electronic/dos-profile",
            direct_call=self._call_direct_dos_profile,
            operation_label="DOS profile",
        )

    def export_outcar_tabular(
        self,
        *,
        outcar_path: str,
        dataset: str = "ionic_series",
        delimiter: str = ",",
    ) -> dict:
        """Export OUTCAR series data as CSV-ready tabular text."""

        payload = {
            "outcar_path": outcar_path,
            "dataset": dataset,
            "delimiter": delimiter,
        }
        return self._execute(
            payload=payload,
            api_path="/v1/outcar/export-tabular",
            direct_call=self._call_direct_export_tabular,
            operation_label="tabular export",
        )

    def generate_relax_input(
        self,
        *,
        structure: dict,
        kmesh: tuple[int, int, int] = (6, 6, 6),
        gamma_centered: bool = True,
        encut: int = 520,
        ediff: float = 1e-5,
        ediffg: float = -0.02,
        ismear: int = 0,
        sigma: float = 0.05,
        ibrion: int = 2,
        isif: int = 3,
        nsw: int = 120,
        ispin: int = 2,
        magmom: str | None = None,
        incar_overrides: dict | None = None,
    ) -> dict:
        """Generate INCAR/KPOINTS/POSCAR relaxation input bundle."""

        payload = {
            "structure": structure,
            "kmesh": list(kmesh),
            "gamma_centered": gamma_centered,
            "encut": encut,
            "ediff": ediff,
            "ediffg": ediffg,
            "ismear": ismear,
            "sigma": sigma,
            "ibrion": ibrion,
            "isif": isif,
            "nsw": nsw,
            "ispin": ispin,
            "magmom": magmom,
            "incar_overrides": incar_overrides or {},
        }
        return self._execute(
            payload=payload,
            api_path="/v1/input/relax-generate",
            direct_call=self._call_direct_relax_input,
            operation_label="relax input generation",
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
        try:
            canonical = validate_summary_request(payload)
        except Exception as exc:
            raise RuntimeError(_format_app_error(normalize_error(exc), "Invalid summary request")) from exc
        result = self._summary_use_case.execute(canonical)
        if not result.ok or result.value is None:
            raise RuntimeError(_format_app_error(result.error, "Unknown direct summary error"))
        return result.value.to_mapping()

    def _call_direct_diagnostics(self, payload: dict) -> dict:
        try:
            canonical = validate_diagnostics_request(payload)
        except Exception as exc:
            raise RuntimeError(_format_app_error(normalize_error(exc), "Invalid diagnostics request")) from exc
        result = self._diagnostics_use_case.execute(canonical)
        if not result.ok or result.value is None:
            raise RuntimeError(_format_app_error(result.error, "Unknown direct diagnostics error"))
        return result.value.to_mapping()

    def _call_direct_batch_summary(self, payload: dict) -> dict:
        try:
            canonical = validate_batch_summary_request(payload)
        except Exception as exc:
            raise RuntimeError(_format_app_error(normalize_error(exc), "Invalid batch summary request")) from exc
        result = self._batch_summary_use_case.execute(canonical)
        if not result.ok or result.value is None:
            raise RuntimeError(_format_app_error(result.error, "Unknown direct batch summary error"))
        return result.value.to_mapping()

    def _call_direct_discover_outcar_runs(self, payload: dict) -> dict:
        try:
            canonical = validate_discover_outcar_runs_request(payload)
        except Exception as exc:
            raise RuntimeError(_format_app_error(normalize_error(exc), "Invalid OUTCAR discovery request")) from exc
        result = self._discover_outcar_runs_use_case.execute(canonical)
        if not result.ok or result.value is None:
            raise RuntimeError(_format_app_error(result.error, "Unknown direct OUTCAR discovery error"))
        return result.value.to_mapping()

    def _call_direct_batch_diagnostics(self, payload: dict) -> dict:
        try:
            canonical = validate_batch_diagnostics_request(payload)
        except Exception as exc:
            raise RuntimeError(_format_app_error(normalize_error(exc), "Invalid batch diagnostics request")) from exc
        result = self._batch_diagnostics_use_case.execute(canonical)
        if not result.ok or result.value is None:
            raise RuntimeError(_format_app_error(result.error, "Unknown direct batch diagnostics error"))
        return result.value.to_mapping()

    def _call_direct_batch_insights(self, payload: dict) -> dict:
        try:
            canonical = validate_batch_insights_request(payload)
        except Exception as exc:
            raise RuntimeError(_format_app_error(normalize_error(exc), "Invalid batch insights request")) from exc
        result = self._batch_insights_use_case.execute(canonical)
        if not result.ok or result.value is None:
            raise RuntimeError(_format_app_error(result.error, "Unknown direct batch insights error"))
        return result.value.to_mapping()

    def _call_direct_profile(self, payload: dict) -> dict:
        try:
            canonical = validate_convergence_profile_request(payload)
        except Exception as exc:
            raise RuntimeError(_format_app_error(normalize_error(exc), "Invalid profile request")) from exc
        result = self._profile_use_case.execute(canonical)
        if not result.ok or result.value is None:
            raise RuntimeError(_format_app_error(result.error, "Unknown direct profile error"))
        return result.value.to_mapping()

    def _call_direct_electronic_metadata(self, payload: dict) -> dict:
        try:
            canonical = validate_electronic_metadata_request(payload)
        except Exception as exc:
            raise RuntimeError(_format_app_error(normalize_error(exc), "Invalid electronic metadata request")) from exc
        result = self._electronic_use_case.execute(canonical)
        if not result.ok or result.value is None:
            raise RuntimeError(_format_app_error(result.error, "Unknown direct electronic metadata error"))
        return result.value.to_mapping()

    def _call_direct_dos_profile(self, payload: dict) -> dict:
        try:
            canonical = validate_dos_profile_request(payload)
        except Exception as exc:
            raise RuntimeError(_format_app_error(normalize_error(exc), "Invalid DOS profile request")) from exc
        result = self._dos_profile_use_case.execute(canonical)
        if not result.ok or result.value is None:
            raise RuntimeError(_format_app_error(result.error, "Unknown direct DOS profile error"))
        return result.value.to_mapping()

    def _call_direct_ionic_series(self, payload: dict) -> dict:
        try:
            canonical = validate_ionic_series_request(payload)
        except Exception as exc:
            raise RuntimeError(_format_app_error(normalize_error(exc), "Invalid ionic series request")) from exc
        result = self._ionic_series_use_case.execute(canonical)
        if not result.ok or result.value is None:
            raise RuntimeError(_format_app_error(result.error, "Unknown direct ionic series error"))
        return result.value.to_mapping()

    def _call_direct_relax_input(self, payload: dict) -> dict:
        try:
            canonical = validate_generate_relax_input_request(payload)
        except Exception as exc:
            raise RuntimeError(_format_app_error(normalize_error(exc), "Invalid relax input request")) from exc
        result = self._relax_input_use_case.execute(canonical)
        if not result.ok or result.value is None:
            raise RuntimeError(_format_app_error(result.error, "Unknown direct relax input error"))
        return result.value.to_mapping()

    def _call_direct_export_tabular(self, payload: dict) -> dict:
        try:
            canonical = validate_export_tabular_request(payload)
        except Exception as exc:
            raise RuntimeError(_format_app_error(normalize_error(exc), "Invalid tabular export request")) from exc
        result = self._export_tabular_use_case.execute(canonical)
        if not result.ok or result.value is None:
            raise RuntimeError(_format_app_error(result.error, "Unknown direct tabular export error"))
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
            parsed = _extract_api_error(detail)
            if parsed is not None:
                raise RuntimeError(f"API request failed ({exc.code}) [{parsed['code']}]: {parsed['message']}") from exc
            raise RuntimeError(f"API request failed ({exc.code}): {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"API request failed: {exc.reason}") from exc

        return json.loads(raw)


def _format_app_error(error: AppError | None, fallback: str) -> str:
    if error is None:
        return fallback
    return f"[{error.code.value}] {error.message}"


def _extract_api_error(raw_detail: str) -> dict[str, str] | None:
    try:
        payload = json.loads(raw_detail)
    except json.JSONDecodeError:
        return None

    detail = payload.get("detail") if isinstance(payload, dict) else None
    if not isinstance(detail, dict):
        return None

    code = detail.get("code")
    message = detail.get("message")
    if not isinstance(code, str) or not isinstance(message, str):
        return None
    return {"code": code, "message": message}
