"""Transport-agnostic application services for pyVASP workflows."""

from __future__ import annotations

from pyvasp.application.ports import (
    ElectronicMetadataReader,
    OutcarIonicSeriesReader,
    OutcarObservablesReader,
    OutcarSummaryReader,
    RelaxInputBuilder,
)
from pyvasp.core.analysis import build_convergence_profile, build_convergence_report
from pyvasp.core.errors import ParseError, ValidationError, normalize_error
from pyvasp.core.models import OutcarDiagnostics
from pyvasp.core.payloads import (
    BatchSummaryRequestPayload,
    BatchSummaryResponsePayload,
    BatchSummaryRowPayload,
    ConvergenceProfileRequestPayload,
    ConvergenceProfileResponsePayload,
    DiagnosticsRequestPayload,
    DiagnosticsResponsePayload,
    ElectronicMetadataRequestPayload,
    ElectronicMetadataResponsePayload,
    ExportTabularRequestPayload,
    ExportTabularResponsePayload,
    GenerateRelaxInputRequestPayload,
    GenerateRelaxInputResponsePayload,
    IonicSeriesRequestPayload,
    IonicSeriesResponsePayload,
    SummaryRequestPayload,
    SummaryResponsePayload,
)
from pyvasp.core.result import AppResult
from pyvasp.core.tabular import build_csv_text
from pyvasp.core.validators import validate_outcar_path


class SummarizeOutcarUseCase:
    """Orchestrates validation and parser execution for OUTCAR summaries."""

    def __init__(self, reader: OutcarSummaryReader) -> None:
        self._reader = reader

    def execute(self, request: SummaryRequestPayload) -> AppResult[SummaryResponsePayload]:
        """Run summary extraction and return a typed application result."""

        try:
            summary = self._reader.parse_file(request.validated_path())
            payload = SummaryResponsePayload.from_summary(summary, include_history=request.include_history)
            return AppResult.success(payload)
        except (ValidationError, ParseError, OSError) as exc:
            return AppResult.failure(exc)


class BatchSummarizeOutcarUseCase:
    """Summarize multiple OUTCAR files and preserve per-item success/failure rows."""

    def __init__(self, reader: OutcarSummaryReader) -> None:
        self._reader = reader

    def execute(self, request: BatchSummaryRequestPayload) -> AppResult[BatchSummaryResponsePayload]:
        """Run batch summary extraction and return a typed aggregate result."""

        rows: list[BatchSummaryRowPayload] = []
        success_count = 0
        error_count = 0

        for outcar_path in request.outcar_paths:
            try:
                resolved = validate_outcar_path(outcar_path)
                summary = self._reader.parse_file(resolved)
                rows.append(BatchSummaryRowPayload.from_summary(summary))
                success_count += 1
            except Exception as exc:
                rows.append(
                    BatchSummaryRowPayload.from_error(
                        outcar_path=outcar_path,
                        error=normalize_error(exc),
                    )
                )
                error_count += 1
                if request.fail_fast:
                    break

        return AppResult.success(
            BatchSummaryResponsePayload(
                total_count=len(rows),
                success_count=success_count,
                error_count=error_count,
                rows=tuple(rows),
            )
        )


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
            return AppResult.failure(exc)


class BuildConvergenceProfileUseCase:
    """Build chart-ready convergence profile data from OUTCAR energy history."""

    def __init__(self, reader: OutcarSummaryReader) -> None:
        self._reader = reader

    def execute(self, request: ConvergenceProfileRequestPayload) -> AppResult[ConvergenceProfileResponsePayload]:
        """Run convergence-profile extraction and return typed response payload."""

        try:
            summary = self._reader.parse_file(request.validated_path())
            profile = build_convergence_profile(summary)
            payload = ConvergenceProfileResponsePayload.from_profile(profile, summary=summary)
            return AppResult.success(payload)
        except (ValidationError, ParseError, OSError) as exc:
            return AppResult.failure(exc)


class BuildIonicSeriesUseCase:
    """Build multi-metric ionic-step series for OUTCAR visualization workflows."""

    def __init__(self, reader: OutcarIonicSeriesReader) -> None:
        self._reader = reader

    def execute(self, request: IonicSeriesRequestPayload) -> AppResult[IonicSeriesResponsePayload]:
        """Run ionic-series extraction and return typed response payload."""

        try:
            series = self._reader.parse_ionic_series_file(request.validated_path())
            return AppResult.success(IonicSeriesResponsePayload.from_series(series))
        except (ValidationError, ParseError, OSError) as exc:
            return AppResult.failure(exc)


class ExportOutcarTabularUseCase:
    """Export chart-ready OUTCAR datasets as transport-neutral tabular text."""

    def __init__(
        self,
        *,
        summary_reader: OutcarSummaryReader,
        ionic_series_reader: OutcarIonicSeriesReader,
    ) -> None:
        self._summary_reader = summary_reader
        self._ionic_series_reader = ionic_series_reader

    def execute(self, request: ExportTabularRequestPayload) -> AppResult[ExportTabularResponsePayload]:
        """Export selected OUTCAR dataset (`convergence_profile` or `ionic_series`) as CSV text."""

        try:
            if request.dataset == "convergence_profile":
                summary = self._summary_reader.parse_file(request.validated_path())
                profile = build_convergence_profile(summary)
                rows = [
                    [
                        point.ionic_step,
                        point.total_energy_ev,
                        point.delta_energy_ev,
                        point.relative_energy_ev,
                    ]
                    for point in profile.points
                ]
                csv_text = build_csv_text(
                    headers=(
                        "ionic_step",
                        "total_energy_ev",
                        "delta_energy_ev",
                        "relative_energy_ev",
                    ),
                    rows=rows,
                    delimiter=request.delimiter,
                )
                return AppResult.success(
                    ExportTabularResponsePayload(
                        source_path=summary.source_path,
                        dataset=request.dataset,
                        format="csv",
                        delimiter=request.delimiter,
                        filename_hint="convergence_profile.csv",
                        n_rows=len(rows),
                        content=csv_text,
                        warnings=summary.warnings,
                    )
                )

            series = self._ionic_series_reader.parse_ionic_series_file(request.validated_path())
            rows = [
                [
                    point.ionic_step,
                    point.total_energy_ev,
                    point.delta_energy_ev,
                    point.relative_energy_ev,
                    point.max_force_ev_per_a,
                    point.external_pressure_kb,
                    point.fermi_energy_ev,
                ]
                for point in series.points
            ]
            csv_text = build_csv_text(
                headers=(
                    "ionic_step",
                    "total_energy_ev",
                    "delta_energy_ev",
                    "relative_energy_ev",
                    "max_force_ev_per_a",
                    "external_pressure_kb",
                    "fermi_energy_ev",
                ),
                rows=rows,
                delimiter=request.delimiter,
            )
            return AppResult.success(
                ExportTabularResponsePayload(
                    source_path=series.source_path,
                    dataset=request.dataset,
                    format="csv",
                    delimiter=request.delimiter,
                    filename_hint="ionic_series.csv",
                    n_rows=len(rows),
                    content=csv_text,
                    warnings=series.warnings,
                )
            )
        except (ValidationError, ParseError, OSError) as exc:
            return AppResult.failure(exc)


class ParseElectronicMetadataUseCase:
    """Extract VASPKIT-like band gap and DOS metadata from VASP outputs."""

    def __init__(self, reader: ElectronicMetadataReader) -> None:
        self._reader = reader

    def execute(self, request: ElectronicMetadataRequestPayload) -> AppResult[ElectronicMetadataResponsePayload]:
        """Run EIGENVAL/DOSCAR parsing and return typed metadata payload."""

        try:
            eigenval_path, doscar_path = request.validated_paths()
            metadata = self._reader.parse_metadata(
                eigenval_path=eigenval_path,
                doscar_path=doscar_path,
            )
            return AppResult.success(ElectronicMetadataResponsePayload.from_metadata(metadata))
        except (ValidationError, ParseError, OSError, ValueError) as exc:
            return AppResult.failure(exc)


class GenerateRelaxInputUseCase:
    """Generate standard VASP relaxation input files from structure + settings."""

    def __init__(self, builder: RelaxInputBuilder) -> None:
        self._builder = builder

    def execute(self, request: GenerateRelaxInputRequestPayload) -> AppResult[GenerateRelaxInputResponsePayload]:
        """Run input rendering and return generated INCAR/KPOINTS/POSCAR payload."""

        try:
            spec = request.to_spec()
            bundle = self._builder.generate_relax_input(spec)
            return AppResult.success(GenerateRelaxInputResponsePayload.from_bundle(bundle))
        except (ValidationError, OSError, ValueError) as exc:
            return AppResult.failure(exc)
