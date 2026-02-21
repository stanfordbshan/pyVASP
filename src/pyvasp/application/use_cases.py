"""Transport-agnostic application services for pyVASP workflows."""

from __future__ import annotations

from itertools import chain

from pyvasp.application.ports import (
    DosProfileReader,
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
    BatchDiagnosticsRequestPayload,
    BatchDiagnosticsResponsePayload,
    BatchDiagnosticsRowPayload,
    BatchInsightsRequestPayload,
    BatchInsightsResponsePayload,
    BatchInsightsRowPayload,
    BatchInsightsTopRunPayload,
    BatchSummaryRequestPayload,
    BatchSummaryResponsePayload,
    BatchSummaryRowPayload,
    ConvergenceProfileRequestPayload,
    ConvergenceProfileResponsePayload,
    DiscoverOutcarRunsRequestPayload,
    DiscoverOutcarRunsResponsePayload,
    DiagnosticsRequestPayload,
    DosProfileRequestPayload,
    DosProfileResponsePayload,
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


class DiscoverOutcarRunsUseCase:
    """Discover OUTCAR files below a root directory for batch workflows."""

    def execute(self, request: DiscoverOutcarRunsRequestPayload) -> AppResult[DiscoverOutcarRunsResponsePayload]:
        """Scan filesystem and return discovered OUTCAR paths and run directories."""

        try:
            root_dir = request.validated_root_dir()

            if request.recursive:
                candidates = root_dir.rglob("OUTCAR")
            else:
                direct_candidates = chain(
                    [root_dir / "OUTCAR"],
                    ((entry / "OUTCAR") for entry in root_dir.iterdir() if entry.is_dir()),
                )
                candidates = direct_candidates

            discovered = sorted({str(path.resolve()) for path in candidates if path.is_file()})
            selected = discovered[: request.max_runs]

            warnings: list[str] = []
            if len(discovered) > len(selected):
                warnings.append(
                    f"Discovery truncated: found {len(discovered)} OUTCAR files, returning first {len(selected)}"
                )

            run_dirs = tuple(str(validate_outcar_path(path).parent) for path in selected)
            payload = DiscoverOutcarRunsResponsePayload(
                root_dir=str(root_dir),
                recursive=request.recursive,
                max_runs=request.max_runs,
                total_discovered=len(discovered),
                returned_count=len(selected),
                outcar_paths=tuple(selected),
                run_dirs=run_dirs,
                warnings=tuple(warnings),
            )
            return AppResult.success(payload)
        except (ValidationError, OSError) as exc:
            return AppResult.failure(exc)


class BatchDiagnoseOutcarUseCase:
    """Run diagnostics on multiple OUTCAR files with per-row success/failure output."""

    def __init__(self, reader: OutcarObservablesReader) -> None:
        self._reader = reader

    def execute(self, request: BatchDiagnosticsRequestPayload) -> AppResult[BatchDiagnosticsResponsePayload]:
        """Run batch diagnostics extraction and return a typed aggregate result."""

        rows: list[BatchDiagnosticsRowPayload] = []
        success_count = 0
        error_count = 0

        for outcar_path in request.outcar_paths:
            try:
                resolved = validate_outcar_path(outcar_path)
                observables = self._reader.parse_observables_file(resolved)
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

                rows.append(
                    BatchDiagnosticsRowPayload(
                        outcar_path=observables.source_path,
                        status="ok",
                        final_total_energy_ev=observables.summary.final_total_energy_ev,
                        max_force_ev_per_a=observables.summary.max_force_ev_per_a,
                        external_pressure_kb=observables.external_pressure_kb,
                        is_energy_converged=convergence.is_energy_converged,
                        is_force_converged=convergence.is_force_converged,
                        is_converged=convergence.is_converged,
                        warnings=tuple(dict.fromkeys(warnings)),
                        error=None,
                    )
                )
                success_count += 1
            except Exception as exc:
                rows.append(
                    BatchDiagnosticsRowPayload(
                        outcar_path=outcar_path,
                        status="error",
                        final_total_energy_ev=None,
                        max_force_ev_per_a=None,
                        external_pressure_kb=None,
                        is_energy_converged=None,
                        is_force_converged=None,
                        is_converged=None,
                        warnings=(),
                        error=normalize_error(exc).to_mapping(),
                    )
                )
                error_count += 1
                if request.fail_fast:
                    break

        return AppResult.success(
            BatchDiagnosticsResponsePayload(
                total_count=len(rows),
                success_count=success_count,
                error_count=error_count,
                rows=tuple(rows),
            )
        )


class BuildBatchInsightsUseCase:
    """Build aggregate screening insights from multiple OUTCAR runs."""

    def __init__(self, reader: OutcarObservablesReader) -> None:
        self._reader = reader

    def execute(self, request: BatchInsightsRequestPayload) -> AppResult[BatchInsightsResponsePayload]:
        """Compute batch-level ranking/statistics while preserving per-row errors."""

        rows: list[BatchInsightsRowPayload] = []
        success_count = 0
        error_count = 0
        converged_count = 0
        not_converged_count = 0
        unknown_convergence_count = 0

        for outcar_path in request.outcar_paths:
            try:
                resolved = validate_outcar_path(outcar_path)
                observables = self._reader.parse_observables_file(resolved)
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

                is_converged = convergence.is_converged
                if convergence.is_energy_converged is None or convergence.is_force_converged is None:
                    is_converged = None

                if is_converged is True:
                    converged_count += 1
                elif is_converged is False:
                    not_converged_count += 1
                else:
                    unknown_convergence_count += 1

                rows.append(
                    BatchInsightsRowPayload(
                        outcar_path=observables.source_path,
                        status="ok",
                        system_name=observables.summary.system_name,
                        final_total_energy_ev=observables.summary.final_total_energy_ev,
                        max_force_ev_per_a=observables.summary.max_force_ev_per_a,
                        external_pressure_kb=observables.external_pressure_kb,
                        is_converged=is_converged,
                        warnings=tuple(dict.fromkeys(warnings)),
                        error=None,
                    )
                )
                success_count += 1
            except Exception as exc:
                rows.append(
                    BatchInsightsRowPayload(
                        outcar_path=outcar_path,
                        status="error",
                        system_name=None,
                        final_total_energy_ev=None,
                        max_force_ev_per_a=None,
                        external_pressure_kb=None,
                        is_converged=None,
                        warnings=(),
                        error=normalize_error(exc).to_mapping(),
                    )
                )
                error_count += 1
                if request.fail_fast:
                    break

        energy_values = [row.final_total_energy_ev for row in rows if row.status == "ok" and row.final_total_energy_ev is not None]
        force_values = [row.max_force_ev_per_a for row in rows if row.status == "ok" and row.max_force_ev_per_a is not None]

        ranked_candidates = sorted(
            (
                row
                for row in rows
                if row.status == "ok" and row.final_total_energy_ev is not None
            ),
            key=lambda row: row.final_total_energy_ev,
        )
        top_runs = tuple(
            BatchInsightsTopRunPayload(
                rank=idx + 1,
                outcar_path=row.outcar_path,
                system_name=row.system_name,
                final_total_energy_ev=row.final_total_energy_ev if row.final_total_energy_ev is not None else 0.0,
                max_force_ev_per_a=row.max_force_ev_per_a,
                is_converged=row.is_converged,
            )
            for idx, row in enumerate(ranked_candidates[: request.top_n])
        )

        energy_min_ev = min(energy_values) if energy_values else None
        energy_max_ev = max(energy_values) if energy_values else None
        energy_mean_ev = (sum(energy_values) / len(energy_values)) if energy_values else None
        energy_span_ev = (energy_max_ev - energy_min_ev) if energy_values else None
        mean_max_force_ev_per_a = (sum(force_values) / len(force_values)) if force_values else None

        return AppResult.success(
            BatchInsightsResponsePayload(
                total_count=len(rows),
                success_count=success_count,
                error_count=error_count,
                converged_count=converged_count,
                not_converged_count=not_converged_count,
                unknown_convergence_count=unknown_convergence_count,
                energy_min_ev=energy_min_ev,
                energy_max_ev=energy_max_ev,
                energy_mean_ev=energy_mean_ev,
                energy_span_ev=energy_span_ev,
                mean_max_force_ev_per_a=mean_max_force_ev_per_a,
                top_lowest_energy=top_runs,
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


class BuildDosProfileUseCase:
    """Extract chart-ready DOS profile points from DOSCAR."""

    def __init__(self, reader: DosProfileReader) -> None:
        self._reader = reader

    def execute(self, request: DosProfileRequestPayload) -> AppResult[DosProfileResponsePayload]:
        """Run DOSCAR parsing and return typed DOS-profile payload."""

        try:
            profile = self._reader.parse_dos_profile(
                doscar_path=request.validated_path(),
                energy_window_ev=request.energy_window_ev,
                max_points=request.max_points,
            )
            return AppResult.success(DosProfileResponsePayload.from_profile(profile))
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
