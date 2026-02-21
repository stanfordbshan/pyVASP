"""Transport-agnostic application services for pyVASP workflows."""

from __future__ import annotations

from pyvasp.application.ports import (
    ElectronicMetadataReader,
    OutcarObservablesReader,
    OutcarSummaryReader,
    RelaxInputBuilder,
)
from pyvasp.core.analysis import build_convergence_profile, build_convergence_report
from pyvasp.core.errors import ParseError, ValidationError
from pyvasp.core.models import OutcarDiagnostics
from pyvasp.core.payloads import (
    ConvergenceProfileRequestPayload,
    ConvergenceProfileResponsePayload,
    DiagnosticsRequestPayload,
    DiagnosticsResponsePayload,
    ElectronicMetadataRequestPayload,
    ElectronicMetadataResponsePayload,
    GenerateRelaxInputRequestPayload,
    GenerateRelaxInputResponsePayload,
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
            payload = SummaryResponsePayload.from_summary(summary, include_history=request.include_history)
            return AppResult.success(payload)
        except (ValidationError, ParseError, OSError) as exc:
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
