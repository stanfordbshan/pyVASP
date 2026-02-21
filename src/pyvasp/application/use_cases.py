"""Transport-agnostic application services for pyVASP workflows."""

from __future__ import annotations

from pyvasp.application.ports import OutcarObservablesReader, OutcarSummaryReader
from pyvasp.core.analysis import build_convergence_report
from pyvasp.core.errors import ParseError, ValidationError
from pyvasp.core.models import OutcarDiagnostics
from pyvasp.core.payloads import (
    DiagnosticsRequestPayload,
    DiagnosticsResponsePayload,
    SummaryRequestPayload,
    SummaryResponsePayload,
)
from pyvasp.core.result import AppResult


class SummarizeOutcarUseCase:
    """Orchestrates validation and parser execution for OUTCAR summaries."""

    def __init__(self, reader: OutcarSummaryReader) -> None:
        self._reader = reader

    def execute(self, request: SummaryRequestPayload) -> AppResult[SummaryResponsePayload]:
        """Run summary extraction and return a typed application result."""

        try:
            summary = self._reader.parse_file(request.validated_path())
            payload = SummaryResponsePayload.from_summary(
                summary,
                include_history=request.include_history,
            )
            return AppResult.success(payload)
        except (ValidationError, ParseError, OSError) as exc:
            return AppResult.failure(str(exc))


class DiagnoseOutcarUseCase:
    """Builds convergence-focused diagnostics from parsed OUTCAR observables."""

    def __init__(self, reader: OutcarObservablesReader) -> None:
        self._reader = reader

    def execute(self, request: DiagnosticsRequestPayload) -> AppResult[DiagnosticsResponsePayload]:
        """Run diagnostics extraction and return a typed application result."""

        try:
            observables = self._reader.parse_observables_file(request.validated_path())
            convergence = build_convergence_report(
                observables.summary,
                energy_tolerance_ev=request.energy_tolerance_ev,
                force_tolerance_ev_per_a=request.force_tolerance_ev_per_a,
            )

            warnings = list(observables.summary.warnings)
            warnings.extend(observables.warnings)
            if convergence.is_energy_converged is None:
                warnings.append("Energy convergence could not be evaluated (insufficient TOTEN history)")
            if convergence.is_force_converged is None:
                warnings.append("Force convergence could not be evaluated (missing force table)")

            diagnostics = OutcarDiagnostics(
                source_path=observables.source_path,
                summary=observables.summary,
                external_pressure_kb=observables.external_pressure_kb,
                stress_tensor_kb=observables.stress_tensor_kb,
                magnetization=observables.magnetization,
                convergence=convergence,
                warnings=tuple(dict.fromkeys(warnings)),
            )

            return AppResult.success(DiagnosticsResponsePayload.from_diagnostics(diagnostics))
        except (ValidationError, ParseError, OSError) as exc:
            return AppResult.failure(str(exc))
