from __future__ import annotations

from pathlib import Path

from pyvasp.application.use_cases import (
    BuildConvergenceProfileUseCase,
    BuildIonicSeriesUseCase,
    DiagnoseOutcarUseCase,
    GenerateRelaxInputUseCase,
    ParseElectronicMetadataUseCase,
    SummarizeOutcarUseCase,
)
from pyvasp.core.errors import ErrorCode, ParseError
from pyvasp.core.models import (
    BandGapChannel,
    BandGapSummary,
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
    ConvergenceProfileRequestPayload,
    DiagnosticsRequestPayload,
    ElectronicMetadataRequestPayload,
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
