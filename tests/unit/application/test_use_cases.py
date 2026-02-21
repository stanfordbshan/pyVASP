from __future__ import annotations

from pathlib import Path

from pyvasp.application.use_cases import (
    BatchDiagnoseOutcarUseCase,
    BatchSummarizeOutcarUseCase,
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
from pyvasp.core.errors import ErrorCode, ParseError
from pyvasp.core.models import (
    BandGapChannel,
    BandGapSummary,
    DosProfile,
    DosProfilePoint,
    DosMetadata,
    ElectronicStructureMetadata,
    EnergyPoint,
    GeneratedInputBundle,
    MagnetizationSummary,
    OutcarObservables,
    OutcarIonicSeries,
    OutcarIonicSeriesPoint,
    OutcarSummary,
    RelaxInputSpec,
    StressTensor,
)
from pyvasp.core.payloads import (
    BatchDiagnosticsRequestPayload,
    BatchSummaryRequestPayload,
    ConvergenceProfileRequestPayload,
    DiscoverOutcarRunsRequestPayload,
    DiagnosticsRequestPayload,
    DosProfileRequestPayload,
    ElectronicMetadataRequestPayload,
    ExportTabularRequestPayload,
    GenerateRelaxInputRequestPayload,
    IonicSeriesRequestPayload,
    SummaryRequestPayload,
)


FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "OUTCAR.sample"


class WorkingSummaryReader:
    def parse_file(self, outcar_path: Path) -> OutcarSummary:
        return OutcarSummary(
            source_path=str(outcar_path),
            system_name="stub",
            nions=1,
            ionic_steps=2,
            electronic_iterations=3,
            final_total_energy_ev=-1.23,
            final_fermi_energy_ev=2.34,
            max_force_ev_per_a=0.01,
            energy_history=(
                EnergyPoint(ionic_step=1, total_energy_ev=-1.2),
                EnergyPoint(ionic_step=2, total_energy_ev=-1.23),
            ),
            warnings=(),
        )


class BrokenSummaryReader:
    def parse_file(self, outcar_path: Path) -> OutcarSummary:
        raise ParseError("failed")


class WorkingObservablesReader:
    def parse_observables_file(self, outcar_path: Path) -> OutcarObservables:
        summary = OutcarSummary(
            source_path=str(outcar_path),
            system_name="diag",
            nions=2,
            ionic_steps=2,
            electronic_iterations=4,
            final_total_energy_ev=-20.00005,
            final_fermi_energy_ev=4.25,
            max_force_ev_per_a=0.01,
            energy_history=(
                EnergyPoint(ionic_step=1, total_energy_ev=-20.0),
                EnergyPoint(ionic_step=2, total_energy_ev=-20.00005),
            ),
            warnings=(),
        )
        return OutcarObservables(
            source_path=str(outcar_path),
            summary=summary,
            external_pressure_kb=-1.23,
            stress_tensor_kb=StressTensor(9.0, 18.0, 27.0, 0.9, 1.8, 2.7),
            magnetization=MagnetizationSummary(axis="z", total_moment_mu_b=0.3, site_moments_mu_b=(1.1, -0.8)),
            warnings=(),
        )


class BrokenObservablesReader:
    def parse_observables_file(self, outcar_path: Path) -> OutcarObservables:
        raise ParseError("diagnostics failed")


class WorkingIonicSeriesReader:
    def parse_ionic_series_file(self, outcar_path: Path) -> OutcarIonicSeries:
        return OutcarIonicSeries(
            source_path=str(outcar_path),
            points=(
                OutcarIonicSeriesPoint(
                    ionic_step=1,
                    total_energy_ev=-20.0,
                    delta_energy_ev=None,
                    relative_energy_ev=0.1,
                    max_force_ev_per_a=0.05,
                    external_pressure_kb=-3.21,
                    fermi_energy_ev=4.2,
                ),
                OutcarIonicSeriesPoint(
                    ionic_step=2,
                    total_energy_ev=-20.1,
                    delta_energy_ev=-0.1,
                    relative_energy_ev=0.0,
                    max_force_ev_per_a=0.01,
                    external_pressure_kb=-1.23,
                    fermi_energy_ev=4.25,
                ),
            ),
            warnings=(),
        )


class BrokenIonicSeriesReader:
    def parse_ionic_series_file(self, outcar_path: Path) -> OutcarIonicSeries:
        raise ParseError("ionic series failed")


class WorkingElectronicReader:
    def parse_metadata(self, *, eigenval_path: Path | None, doscar_path: Path | None) -> ElectronicStructureMetadata:
        return ElectronicStructureMetadata(
            eigenval_path=str(eigenval_path) if eigenval_path is not None else None,
            doscar_path=str(doscar_path) if doscar_path is not None else None,
            band_gap=BandGapSummary(
                is_spin_polarized=False,
                is_metal=False,
                fundamental_gap_ev=1.3,
                vbm_ev=-0.5,
                cbm_ev=0.8,
                is_direct=True,
                channel="total",
                channels=(
                    BandGapChannel(
                        spin="total",
                        gap_ev=1.3,
                        vbm_ev=-0.5,
                        cbm_ev=0.8,
                        is_direct=True,
                        kpoint_index_vbm=2,
                        kpoint_index_cbm=2,
                        is_metal=False,
                    ),
                ),
            ),
            dos_metadata=DosMetadata(
                energy_min_ev=-5.0,
                energy_max_ev=5.0,
                nedos=5,
                efermi_ev=0.5,
                is_spin_polarized=False,
                has_integrated_dos=True,
                energy_step_ev=3.0,
                total_dos_at_fermi=0.4,
            ),
            warnings=(),
        )


class BrokenElectronicReader:
    def parse_metadata(self, *, eigenval_path: Path | None, doscar_path: Path | None) -> ElectronicStructureMetadata:
        raise ParseError("electronic parse failed")


class WorkingDosProfileReader:
    def parse_dos_profile(self, *, doscar_path: Path, energy_window_ev: float, max_points: int) -> DosProfile:
        return DosProfile(
            source_path=str(doscar_path),
            efermi_ev=0.5,
            energy_window_ev=energy_window_ev,
            points=(
                DosProfilePoint(index=1, energy_ev=-0.5, energy_relative_ev=-1.0, dos_total=0.2),
                DosProfilePoint(index=2, energy_ev=0.5, energy_relative_ev=0.0, dos_total=0.4),
                DosProfilePoint(index=3, energy_ev=1.5, energy_relative_ev=1.0, dos_total=0.8),
            ),
            warnings=(),
        )


class BrokenDosProfileReader:
    def parse_dos_profile(self, *, doscar_path: Path, energy_window_ev: float, max_points: int) -> DosProfile:
        raise ParseError("dos profile failed")


class WorkingInputBuilder:
    def generate_relax_input(self, spec: RelaxInputSpec) -> GeneratedInputBundle:
        return GeneratedInputBundle(
            system_name=spec.structure.comment,
            n_atoms=len(spec.structure.atoms),
            incar_text="ENCUT = 520\n",
            kpoints_text="Automatic mesh\n",
            poscar_text="Si2\n",
            warnings=(),
        )


class BrokenInputBuilder:
    def generate_relax_input(self, spec: RelaxInputSpec) -> GeneratedInputBundle:
        raise ValueError("input generation failed")


def test_summary_use_case_success() -> None:
    use_case = SummarizeOutcarUseCase(reader=WorkingSummaryReader())
    request = SummaryRequestPayload(outcar_path=str(FIXTURE), include_history=True)

    result = use_case.execute(request)
    assert result.ok is True
    assert result.value is not None
    assert result.value.final_total_energy_ev == -1.23


def test_summary_use_case_failure() -> None:
    use_case = SummarizeOutcarUseCase(reader=BrokenSummaryReader())
    request = SummaryRequestPayload(outcar_path=str(FIXTURE), include_history=False)

    result = use_case.execute(request)
    assert result.ok is False
    assert result.error is not None
    assert result.error.code == ErrorCode.PARSE_ERROR
    assert result.error.message == "failed"


def test_batch_summary_use_case_mixed_results() -> None:
    use_case = BatchSummarizeOutcarUseCase(reader=WorkingSummaryReader())
    request = BatchSummaryRequestPayload(
        outcar_paths=(str(FIXTURE), "/missing/OUTCAR"),
        fail_fast=False,
    )

    result = use_case.execute(request)
    assert result.ok is True
    assert result.value is not None
    assert result.value.total_count == 2
    assert result.value.success_count == 1
    assert result.value.error_count == 1
    assert result.value.rows[0].status == "ok"
    assert result.value.rows[1].status == "error"
    assert result.value.rows[1].error is not None
    assert result.value.rows[1].error["code"] == "FILE_NOT_FOUND"


def test_batch_summary_use_case_fail_fast_stops_early() -> None:
    use_case = BatchSummarizeOutcarUseCase(reader=WorkingSummaryReader())
    request = BatchSummaryRequestPayload(
        outcar_paths=("/missing/OUTCAR", str(FIXTURE)),
        fail_fast=True,
    )

    result = use_case.execute(request)
    assert result.ok is True
    assert result.value is not None
    assert result.value.total_count == 1
    assert result.value.success_count == 0
    assert result.value.error_count == 1


def test_discover_runs_use_case_recursive(tmp_path: Path) -> None:
    run_a = tmp_path / "run_a"
    run_b = tmp_path / "group" / "run_b"
    run_a.mkdir(parents=True)
    run_b.mkdir(parents=True)
    (run_a / "OUTCAR").write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    (run_b / "OUTCAR").write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")

    use_case = DiscoverOutcarRunsUseCase()
    request = DiscoverOutcarRunsRequestPayload(root_dir=str(tmp_path), recursive=True, max_runs=10)

    result = use_case.execute(request)
    assert result.ok is True
    assert result.value is not None
    assert result.value.total_discovered == 2
    assert result.value.returned_count == 2
    assert len(result.value.outcar_paths) == 2
    assert any(Path(path).parent.name == "run_a" for path in result.value.outcar_paths)
    assert any(Path(path).parent.name == "run_b" for path in result.value.outcar_paths)


def test_discover_runs_use_case_non_recursive_and_truncated(tmp_path: Path) -> None:
    run_a = tmp_path / "run_a"
    run_b = tmp_path / "group" / "run_b"
    run_a.mkdir(parents=True)
    run_b.mkdir(parents=True)
    (run_a / "OUTCAR").write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    (run_b / "OUTCAR").write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")

    use_case = DiscoverOutcarRunsUseCase()
    non_recursive = DiscoverOutcarRunsRequestPayload(root_dir=str(tmp_path), recursive=False, max_runs=10)
    limited = DiscoverOutcarRunsRequestPayload(root_dir=str(tmp_path), recursive=True, max_runs=1)

    result_non_recursive = use_case.execute(non_recursive)
    assert result_non_recursive.ok is True
    assert result_non_recursive.value is not None
    assert result_non_recursive.value.total_discovered == 1

    result_limited = use_case.execute(limited)
    assert result_limited.ok is True
    assert result_limited.value is not None
    assert result_limited.value.total_discovered == 2
    assert result_limited.value.returned_count == 1
    assert any("truncated" in warning for warning in result_limited.value.warnings)


def test_batch_diagnostics_use_case_mixed_results() -> None:
    use_case = BatchDiagnoseOutcarUseCase(reader=WorkingObservablesReader())
    request = BatchDiagnosticsRequestPayload(
        outcar_paths=(str(FIXTURE), "/missing/OUTCAR"),
        energy_tolerance_ev=1e-4,
        force_tolerance_ev_per_a=0.02,
        fail_fast=False,
    )

    result = use_case.execute(request)
    assert result.ok is True
    assert result.value is not None
    assert result.value.total_count == 2
    assert result.value.success_count == 1
    assert result.value.error_count == 1
    assert result.value.rows[0].status == "ok"
    assert result.value.rows[0].is_converged is True
    assert result.value.rows[1].status == "error"
    assert result.value.rows[1].error is not None
    assert result.value.rows[1].error["code"] == "FILE_NOT_FOUND"


def test_batch_diagnostics_use_case_fail_fast_stops_early() -> None:
    use_case = BatchDiagnoseOutcarUseCase(reader=WorkingObservablesReader())
    request = BatchDiagnosticsRequestPayload(
        outcar_paths=("/missing/OUTCAR", str(FIXTURE)),
        energy_tolerance_ev=1e-4,
        force_tolerance_ev_per_a=0.02,
        fail_fast=True,
    )

    result = use_case.execute(request)
    assert result.ok is True
    assert result.value is not None
    assert result.value.total_count == 1
    assert result.value.success_count == 0
    assert result.value.error_count == 1


def test_diagnostics_use_case_success() -> None:
    use_case = DiagnoseOutcarUseCase(reader=WorkingObservablesReader())
    request = DiagnosticsRequestPayload(
        outcar_path=str(FIXTURE),
        energy_tolerance_ev=1e-4,
        force_tolerance_ev_per_a=0.02,
    )

    result = use_case.execute(request)
    assert result.ok is True
    assert result.value is not None
    assert result.value.convergence["is_converged"] is True
    assert result.value.external_pressure_kb == -1.23


def test_diagnostics_use_case_failure() -> None:
    use_case = DiagnoseOutcarUseCase(reader=BrokenObservablesReader())
    request = DiagnosticsRequestPayload(outcar_path=str(FIXTURE))

    result = use_case.execute(request)
    assert result.ok is False
    assert result.error is not None
    assert result.error.code == ErrorCode.PARSE_ERROR
    assert result.error.message == "diagnostics failed"


def test_profile_use_case_success() -> None:
    use_case = BuildConvergenceProfileUseCase(reader=WorkingSummaryReader())
    request = ConvergenceProfileRequestPayload(outcar_path=str(FIXTURE))

    result = use_case.execute(request)
    assert result.ok is True
    assert result.value is not None
    assert len(result.value.points) == 2


def test_ionic_series_use_case_success() -> None:
    use_case = BuildIonicSeriesUseCase(reader=WorkingIonicSeriesReader())
    request = IonicSeriesRequestPayload(outcar_path=str(FIXTURE))

    result = use_case.execute(request)
    assert result.ok is True
    assert result.value is not None
    assert result.value.n_steps == 2
    assert result.value.points[1]["external_pressure_kb"] == -1.23


def test_ionic_series_use_case_failure() -> None:
    use_case = BuildIonicSeriesUseCase(reader=BrokenIonicSeriesReader())
    request = IonicSeriesRequestPayload(outcar_path=str(FIXTURE))

    result = use_case.execute(request)
    assert result.ok is False
    assert result.error is not None
    assert result.error.code == ErrorCode.PARSE_ERROR
    assert result.error.message == "ionic series failed"


def test_export_tabular_use_case_ionic_series_success() -> None:
    use_case = ExportOutcarTabularUseCase(
        summary_reader=WorkingSummaryReader(),
        ionic_series_reader=WorkingIonicSeriesReader(),
    )
    request = ExportTabularRequestPayload(outcar_path=str(FIXTURE), dataset="ionic_series", delimiter=",")

    result = use_case.execute(request)
    assert result.ok is True
    assert result.value is not None
    assert result.value.dataset == "ionic_series"
    assert result.value.n_rows == 2
    assert "external_pressure_kb" in result.value.content


def test_export_tabular_use_case_profile_success() -> None:
    use_case = ExportOutcarTabularUseCase(
        summary_reader=WorkingSummaryReader(),
        ionic_series_reader=WorkingIonicSeriesReader(),
    )
    request = ExportTabularRequestPayload(outcar_path=str(FIXTURE), dataset="convergence_profile", delimiter=",")

    result = use_case.execute(request)
    assert result.ok is True
    assert result.value is not None
    assert result.value.dataset == "convergence_profile"
    assert result.value.n_rows == 2
    assert "relative_energy_ev" in result.value.content


def test_export_tabular_use_case_failure() -> None:
    use_case = ExportOutcarTabularUseCase(
        summary_reader=BrokenSummaryReader(),
        ionic_series_reader=BrokenIonicSeriesReader(),
    )
    request = ExportTabularRequestPayload(outcar_path=str(FIXTURE), dataset="ionic_series", delimiter=",")

    result = use_case.execute(request)
    assert result.ok is False
    assert result.error is not None
    assert result.error.code == ErrorCode.PARSE_ERROR
    assert result.error.message == "ionic series failed"


def test_electronic_use_case_success() -> None:
    use_case = ParseElectronicMetadataUseCase(reader=WorkingElectronicReader())
    request = ElectronicMetadataRequestPayload(
        eigenval_path=str(FIXTURE),
        doscar_path=str(FIXTURE),
    )

    result = use_case.execute(request)
    assert result.ok is True
    assert result.value is not None
    assert result.value.band_gap is not None
    assert result.value.band_gap["fundamental_gap_ev"] == 1.3


def test_electronic_use_case_failure() -> None:
    use_case = ParseElectronicMetadataUseCase(reader=BrokenElectronicReader())
    request = ElectronicMetadataRequestPayload(
        eigenval_path=str(FIXTURE),
        doscar_path=str(FIXTURE),
    )

    result = use_case.execute(request)
    assert result.ok is False
    assert result.error is not None
    assert result.error.code == ErrorCode.PARSE_ERROR
    assert result.error.message == "electronic parse failed"


def test_dos_profile_use_case_success() -> None:
    use_case = BuildDosProfileUseCase(reader=WorkingDosProfileReader())
    request = DosProfileRequestPayload(
        doscar_path=str(FIXTURE),
        energy_window_ev=3.0,
        max_points=200,
    )

    result = use_case.execute(request)
    assert result.ok is True
    assert result.value is not None
    assert result.value.n_points == 3
    assert result.value.points[1]["energy_relative_ev"] == 0.0


def test_dos_profile_use_case_failure() -> None:
    use_case = BuildDosProfileUseCase(reader=BrokenDosProfileReader())
    request = DosProfileRequestPayload(
        doscar_path=str(FIXTURE),
        energy_window_ev=3.0,
        max_points=200,
    )

    result = use_case.execute(request)
    assert result.ok is False
    assert result.error is not None
    assert result.error.code == ErrorCode.PARSE_ERROR
    assert result.error.message == "dos profile failed"


def test_generate_relax_input_use_case_success() -> None:
    use_case = GenerateRelaxInputUseCase(builder=WorkingInputBuilder())
    request = GenerateRelaxInputRequestPayload.from_mapping(
        {
            "structure": {
                "comment": "Si2",
                "lattice_vectors": [[5.43, 0, 0], [0, 5.43, 0], [0, 0, 5.43]],
                "atoms": [
                    {"element": "Si", "frac_coords": [0, 0, 0]},
                    {"element": "Si", "frac_coords": [0.25, 0.25, 0.25]},
                ],
            }
        }
    )

    result = use_case.execute(request)
    assert result.ok is True
    assert result.value is not None
    assert result.value.n_atoms == 2


def test_generate_relax_input_use_case_failure() -> None:
    use_case = GenerateRelaxInputUseCase(builder=BrokenInputBuilder())
    request = GenerateRelaxInputRequestPayload.from_mapping(
        {
            "structure": {
                "comment": "Si2",
                "lattice_vectors": [[5.43, 0, 0], [0, 5.43, 0], [0, 0, 5.43]],
                "atoms": [
                    {"element": "Si", "frac_coords": [0, 0, 0]},
                    {"element": "Si", "frac_coords": [0.25, 0.25, 0.25]},
                ],
            }
        }
    )

    result = use_case.execute(request)
    assert result.ok is False
    assert result.error is not None
    assert result.error.code == ErrorCode.INTERNAL_ERROR
    assert result.error.message == "input generation failed"
