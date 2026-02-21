"""Transport-agnostic application services for pyVASP workflows."""

from __future__ import annotations

from itertools import chain
from pathlib import Path

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
    RunReportRequestPayload,
    RunReportResponsePayload,
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


class BuildRunReportUseCase:
    """Build a consolidated run report from one VASP output directory."""

    def __init__(
        self,
        *,
        outcar_reader: OutcarObservablesReader,
        electronic_reader: ElectronicMetadataReader,
    ) -> None:
        self._outcar_reader = outcar_reader
        self._electronic_reader = electronic_reader

    def execute(self, request: RunReportRequestPayload) -> AppResult[RunReportResponsePayload]:
        """Build summary/diagnostics/electronic report for one run folder."""

        try:
            run_dir = request.validated_run_dir()
            outcar_path = validate_outcar_path(str(run_dir / "OUTCAR"))

            observables = self._outcar_reader.parse_observables_file(outcar_path)
            convergence = build_convergence_report(
                observables.summary,
                energy_tolerance_ev=request.energy_tolerance_ev,
                force_tolerance_ev_per_a=request.force_tolerance_ev_per_a,
            )

            report_warnings = list(observables.summary.warnings)
            report_warnings.extend(observables.warnings)
            if convergence.is_energy_converged is None:
                report_warnings.append("Energy convergence could not be evaluated (insufficient TOTEN history)")
            if convergence.is_force_converged is None:
                report_warnings.append("Force convergence could not be evaluated (missing force table)")

            diagnostics = OutcarDiagnostics(
                source_path=observables.source_path,
                summary=observables.summary,
                external_pressure_kb=observables.external_pressure_kb,
                stress_tensor_kb=observables.stress_tensor_kb,
                magnetization=observables.magnetization,
                convergence=convergence,
                warnings=tuple(dict.fromkeys(report_warnings)),
            )
            summary_payload = SummaryResponsePayload.from_summary(observables.summary, include_history=False).to_mapping()
            diagnostics_payload = DiagnosticsResponsePayload.from_diagnostics(diagnostics).to_mapping()

            eigenval_path = _optional_file(run_dir, "EIGENVAL")
            doscar_path = _optional_file(run_dir, "DOSCAR")
            electronic_payload: dict[str, object] | None = None

            if request.include_electronic:
                if eigenval_path is not None or doscar_path is not None:
                    metadata = self._electronic_reader.parse_metadata(
                        eigenval_path=eigenval_path,
                        doscar_path=doscar_path,
                    )
                    mapped = ElectronicMetadataResponsePayload.from_metadata(metadata).to_mapping()
                    electronic_payload = mapped
                    report_warnings.extend(mapped.get("warnings", []))
                else:
                    report_warnings.append(
                        "EIGENVAL/DOSCAR not found in run directory; electronic metadata section skipped"
                    )

            is_converged = diagnostics_payload["convergence"].get("is_converged")
            suggested_actions: list[str] = []
            if is_converged is True:
                suggested_actions.append("Run is converged; suitable for downstream screening/comparison")
            elif is_converged is False:
                suggested_actions.append("Run is not converged; tighten relaxation settings and continue ionic steps")
            else:
                suggested_actions.append("Convergence is indeterminate; inspect OUTCAR completeness and force table")

            if request.include_electronic and (eigenval_path is None and doscar_path is None):
                suggested_actions.append("Generate or retain EIGENVAL/DOSCAR for electronic post-processing")

            if request.include_electronic and electronic_payload is not None and electronic_payload.get("band_gap"):
                band_gap = electronic_payload["band_gap"]
                if isinstance(band_gap, dict) and band_gap.get("is_metal") is True:
                    suggested_actions.append("Metallic character detected; inspect DOS near E-fermi for finite states")

            recommended_status = "ready"
            if is_converged is False:
                recommended_status = "needs_convergence"
            elif is_converged is None:
                recommended_status = "incomplete"

            warnings_unique = tuple(dict.fromkeys(str(item) for item in report_warnings if str(item).strip()))
            return AppResult.success(
                RunReportResponsePayload(
                    run_dir=str(run_dir),
                    outcar_path=str(outcar_path),
                    eigenval_path=None if eigenval_path is None else str(eigenval_path),
                    doscar_path=None if doscar_path is None else str(doscar_path),
                    summary=summary_payload,
                    diagnostics=diagnostics_payload,
                    electronic_metadata=electronic_payload,
                    is_converged=is_converged,
                    recommended_status=recommended_status,
                    suggested_actions=tuple(dict.fromkeys(suggested_actions)),
                    warnings=warnings_unique,
                )
            )
        except (ValidationError, ParseError, OSError, ValueError) as exc:
            return AppResult.failure(exc)


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


def _optional_file(run_dir: Path, filename: str) -> Path | None:
    candidate = run_dir / filename
    if candidate.exists() and candidate.is_file():
        return candidate.resolve()
    return None
