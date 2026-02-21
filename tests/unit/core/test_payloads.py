from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyvasp.core.errors import ValidationError
from pyvasp.core.models import (
    BandGapChannel,
    BandGapSummary,
    ConvergenceReport,
    DosProfile,
    DosProfilePoint,
    DosMetadata,
    ElectronicStructureMetadata,
    EnergyPoint,
    GeneratedInputBundle,
    MagnetizationSummary,
    OutcarDiagnostics,
    OutcarIonicSeries,
    OutcarIonicSeriesPoint,
    OutcarSummary,
    StressTensor,
)
from pyvasp.core.payloads import (
    BatchDiagnosticsRequestPayload,
    BatchDiagnosticsResponsePayload,
    BatchDiagnosticsRowPayload,
    BatchInsightsResponsePayload,
    BatchInsightsRowPayload,
    BatchInsightsTopRunPayload,
    DiscoverOutcarRunsResponsePayload,
    BatchSummaryResponsePayload,
    BatchSummaryRowPayload,
    DiagnosticsResponsePayload,
    DosProfileResponsePayload,
    ElectronicMetadataResponsePayload,
    ExportTabularResponsePayload,
    GenerateRelaxInputResponsePayload,
    IonicSeriesResponsePayload,
    RunReportResponsePayload,
    SummaryResponsePayload,
    validate_batch_diagnostics_request,
    validate_batch_insights_request,
    validate_batch_summary_request,
    validate_discover_outcar_runs_request,
    validate_diagnostics_request,
    validate_dos_profile_request,
    validate_electronic_metadata_request,
    validate_export_tabular_request,
    validate_generate_relax_input_request,
    validate_ionic_series_request,
    validate_run_report_request,
    validate_summary_request,
)


FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "OUTCAR.sample"
STRUCTURE_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "structure.si2.json"
EIGENVAL_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "EIGENVAL.sample"
DOSCAR_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "DOSCAR.sample"
DISCOVERY_ROOT_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "discovery_root"


def test_validate_summary_request_success() -> None:
    payload = validate_summary_request({"outcar_path": str(FIXTURE), "include_history": True})
    assert payload.outcar_path == str(FIXTURE)
    assert payload.include_history is True


def test_validate_summary_request_missing_file_raises() -> None:
    with pytest.raises(ValidationError):
        validate_summary_request({"outcar_path": "/does/not/exist/OUTCAR"})


def test_validate_batch_summary_request_success() -> None:
    payload = validate_batch_summary_request(
        {
            "outcar_paths": [str(FIXTURE), str(FIXTURE)],
            "fail_fast": True,
        }
    )
    assert payload.outcar_paths == (str(FIXTURE), str(FIXTURE))
    assert payload.fail_fast is True


def test_validate_batch_summary_request_requires_nonempty_list() -> None:
    with pytest.raises(ValidationError):
        validate_batch_summary_request({"outcar_paths": []})


def test_validate_batch_diagnostics_request_success() -> None:
    payload = validate_batch_diagnostics_request(
        {
            "outcar_paths": [str(FIXTURE)],
            "energy_tolerance_ev": 1e-4,
            "force_tolerance_ev_per_a": 0.02,
            "fail_fast": True,
        }
    )
    assert isinstance(payload, BatchDiagnosticsRequestPayload)
    assert payload.outcar_paths == (str(FIXTURE),)
    assert payload.fail_fast is True


def test_validate_batch_diagnostics_request_requires_nonempty_list() -> None:
    with pytest.raises(ValidationError):
        validate_batch_diagnostics_request({"outcar_paths": []})


def test_validate_batch_insights_request_success() -> None:
    payload = validate_batch_insights_request(
        {
            "outcar_paths": [str(FIXTURE)],
            "energy_tolerance_ev": 1e-4,
            "force_tolerance_ev_per_a": 0.02,
            "top_n": 4,
            "fail_fast": True,
        }
    )
    assert payload.outcar_paths == (str(FIXTURE),)
    assert payload.top_n == 4
    assert payload.fail_fast is True


def test_validate_batch_insights_request_bad_top_n() -> None:
    with pytest.raises(ValidationError):
        validate_batch_insights_request(
            {
                "outcar_paths": [str(FIXTURE)],
                "top_n": 0,
            }
        )


def test_validate_discover_outcar_runs_request_success() -> None:
    payload = validate_discover_outcar_runs_request(
        {
            "root_dir": str(DISCOVERY_ROOT_FIXTURE),
            "recursive": True,
            "max_runs": 10,
        }
    )
    assert payload.root_dir == str(DISCOVERY_ROOT_FIXTURE.resolve())
    assert payload.recursive is True
    assert payload.max_runs == 10


def test_validate_discover_outcar_runs_request_bad_max_runs() -> None:
    with pytest.raises(ValidationError):
        validate_discover_outcar_runs_request(
            {
                "root_dir": str(DISCOVERY_ROOT_FIXTURE),
                "max_runs": 0,
            }
        )


def test_validate_run_report_request_success() -> None:
    payload = validate_run_report_request(
        {
            "run_dir": str(DISCOVERY_ROOT_FIXTURE / "run_a"),
            "energy_tolerance_ev": 1e-4,
            "force_tolerance_ev_per_a": 0.02,
            "include_electronic": False,
        }
    )
    assert payload.run_dir.endswith("run_a")
    assert payload.include_electronic is False


def test_validate_run_report_request_requires_directory() -> None:
    with pytest.raises(ValidationError):
        validate_run_report_request({"run_dir": str(FIXTURE)})


def test_validate_diagnostics_request_rejects_non_positive_tolerances() -> None:
    with pytest.raises(ValidationError):
        validate_diagnostics_request(
            {
                "outcar_path": str(FIXTURE),
                "energy_tolerance_ev": 0,
                "force_tolerance_ev_per_a": 0.02,
            }
        )


def test_validate_electronic_metadata_request_success() -> None:
    payload = validate_electronic_metadata_request(
        {
            "eigenval_path": str(EIGENVAL_FIXTURE),
            "doscar_path": str(DOSCAR_FIXTURE),
        }
    )

    assert payload.eigenval_path == str(EIGENVAL_FIXTURE)
    assert payload.doscar_path == str(DOSCAR_FIXTURE)


def test_validate_electronic_metadata_request_requires_one_file() -> None:
    with pytest.raises(ValidationError):
        validate_electronic_metadata_request({})


def test_validate_dos_profile_request_success() -> None:
    payload = validate_dos_profile_request(
        {
            "doscar_path": str(DOSCAR_FIXTURE),
            "energy_window_ev": 4.0,
            "max_points": 250,
        }
    )
    assert payload.doscar_path == str(DOSCAR_FIXTURE)
    assert payload.energy_window_ev == pytest.approx(4.0)
    assert payload.max_points == 250


def test_validate_dos_profile_request_bad_window() -> None:
    with pytest.raises(ValidationError):
        validate_dos_profile_request(
            {
                "doscar_path": str(DOSCAR_FIXTURE),
                "energy_window_ev": -1.0,
            }
        )


def test_validate_generate_relax_input_request_success() -> None:
    structure = json.loads(STRUCTURE_FIXTURE.read_text(encoding="utf-8"))
    payload = validate_generate_relax_input_request({"structure": structure, "kmesh": [4, 4, 4]})

    assert payload.structure.comment == "Si2 cubic"
    assert payload.kmesh == (4, 4, 4)
    assert len(payload.structure.atoms) == 2


def test_validate_generate_relax_input_request_bad_element() -> None:
    structure = json.loads(STRUCTURE_FIXTURE.read_text(encoding="utf-8"))
    structure["atoms"][0]["element"] = "Xx"

    with pytest.raises(ValidationError):
        validate_generate_relax_input_request({"structure": structure})


def test_validate_ionic_series_request_success() -> None:
    payload = validate_ionic_series_request({"outcar_path": str(FIXTURE)})
    assert payload.outcar_path == str(FIXTURE)


def test_validate_export_tabular_request_success() -> None:
    payload = validate_export_tabular_request(
        {
            "outcar_path": str(FIXTURE),
            "dataset": "convergence_profile",
            "delimiter": "tab",
        }
    )
    assert payload.outcar_path == str(FIXTURE)
    assert payload.dataset == "convergence_profile"
    assert payload.delimiter == "\t"


def test_validate_export_tabular_request_bad_dataset() -> None:
    with pytest.raises(ValidationError):
        validate_export_tabular_request(
            {
                "outcar_path": str(FIXTURE),
                "dataset": "unknown",
            }
        )


def test_summary_response_payload_hides_history_when_not_requested() -> None:
    summary = OutcarSummary(
        source_path=str(FIXTURE),
        system_name="Si2 test",
        nions=2,
        ionic_steps=2,
        electronic_iterations=4,
        final_total_energy_ev=-10.5,
        final_fermi_energy_ev=5.2,
        max_force_ev_per_a=0.005,
        energy_history=(EnergyPoint(ionic_step=1, total_energy_ev=-10.0),),
        warnings=(),
    )
    payload = SummaryResponsePayload.from_summary(summary, include_history=False)
    mapped = payload.to_mapping()
    assert mapped["energy_history"] == []


def test_diagnostics_response_payload_serialization() -> None:
    summary = OutcarSummary(
        source_path=str(FIXTURE),
        system_name="Fe2",
        nions=2,
        ionic_steps=2,
        electronic_iterations=2,
        final_total_energy_ev=-20.00005,
        final_fermi_energy_ev=4.25,
        max_force_ev_per_a=0.01,
        energy_history=(
            EnergyPoint(ionic_step=1, total_energy_ev=-20.0),
            EnergyPoint(ionic_step=2, total_energy_ev=-20.00005),
        ),
        warnings=(),
    )
    diagnostics = OutcarDiagnostics(
        source_path=str(FIXTURE),
        summary=summary,
        external_pressure_kb=-1.23,
        stress_tensor_kb=StressTensor(9.0, 18.0, 27.0, 0.9, 1.8, 2.7),
        magnetization=MagnetizationSummary(axis="z", total_moment_mu_b=0.3, site_moments_mu_b=(1.1, -0.8)),
        convergence=ConvergenceReport(
            energy_tolerance_ev=1e-4,
            force_tolerance_ev_per_a=0.02,
            final_energy_change_ev=5e-05,
            is_energy_converged=True,
            is_force_converged=True,
            is_converged=True,
        ),
        warnings=("ok",),
    )

    payload = DiagnosticsResponsePayload.from_diagnostics(diagnostics)
    mapped = payload.to_mapping()

    assert mapped["external_pressure_kb"] == pytest.approx(-1.23)
    assert mapped["stress_tensor_kb"]["xx_kb"] == pytest.approx(9.0)
    assert mapped["magnetization"]["site_moments_mu_b"] == [1.1, -0.8]
    assert mapped["convergence"]["is_converged"] is True
    assert mapped["warnings"] == ["ok"]


def test_electronic_metadata_response_serialization() -> None:
    metadata = ElectronicStructureMetadata(
        eigenval_path=str(EIGENVAL_FIXTURE),
        doscar_path=str(DOSCAR_FIXTURE),
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
        warnings=("ok",),
    )

    payload = ElectronicMetadataResponsePayload.from_metadata(metadata)
    mapped = payload.to_mapping()

    assert mapped["band_gap"]["fundamental_gap_ev"] == pytest.approx(1.3)
    assert mapped["dos_metadata"]["nedos"] == 5
    assert mapped["warnings"] == ["ok"]


def test_dos_profile_response_serialization() -> None:
    profile = DosProfile(
        source_path=str(DOSCAR_FIXTURE),
        efermi_ev=0.5,
        energy_window_ev=4.0,
        points=(
            DosProfilePoint(index=1, energy_ev=-1.0, energy_relative_ev=-1.5, dos_total=0.2),
            DosProfilePoint(index=2, energy_ev=0.5, energy_relative_ev=0.0, dos_total=0.4),
        ),
        warnings=("sampled",),
    )

    payload = DosProfileResponsePayload.from_profile(profile)
    mapped = payload.to_mapping()
    assert mapped["source_path"] == str(DOSCAR_FIXTURE)
    assert mapped["n_points"] == 2
    assert mapped["points"][1]["dos_total"] == pytest.approx(0.4)
    assert mapped["warnings"] == ["sampled"]


def test_generate_relax_input_response_payload() -> None:
    bundle = GeneratedInputBundle(
        system_name="Si2",
        n_atoms=2,
        incar_text="ENCUT = 520\n",
        kpoints_text="Automatic mesh\n",
        poscar_text="Si2\n",
        warnings=("none",),
    )

    payload = GenerateRelaxInputResponsePayload.from_bundle(bundle)
    mapped = payload.to_mapping()
    assert mapped["system_name"] == "Si2"
    assert mapped["n_atoms"] == 2
    assert mapped["warnings"] == ["none"]


def test_ionic_series_response_payload() -> None:
    series = OutcarIonicSeries(
        source_path=str(FIXTURE),
        points=(
            OutcarIonicSeriesPoint(
                ionic_step=1,
                total_energy_ev=-10.0,
                delta_energy_ev=None,
                relative_energy_ev=0.5,
                max_force_ev_per_a=0.02,
                external_pressure_kb=-3.0,
                fermi_energy_ev=5.1,
            ),
            OutcarIonicSeriesPoint(
                ionic_step=2,
                total_energy_ev=-10.5,
                delta_energy_ev=-0.5,
                relative_energy_ev=0.0,
                max_force_ev_per_a=0.005,
                external_pressure_kb=-1.0,
                fermi_energy_ev=5.2,
            ),
        ),
        warnings=("ok",),
    )

    payload = IonicSeriesResponsePayload.from_series(series)
    mapped = payload.to_mapping()
    assert mapped["source_path"] == str(FIXTURE)
    assert mapped["n_steps"] == 2
    assert mapped["points"][0]["delta_energy_ev"] is None
    assert mapped["points"][1]["relative_energy_ev"] == pytest.approx(0.0)


def test_export_tabular_response_payload() -> None:
    payload = ExportTabularResponsePayload(
        source_path=str(FIXTURE),
        dataset="ionic_series",
        format="csv",
        delimiter=",",
        filename_hint="ionic_series.csv",
        n_rows=2,
        content="ionic_step,total_energy_ev\n1,-10.0\n",
        warnings=("ok",),
    )

    mapped = payload.to_mapping()
    assert mapped["dataset"] == "ionic_series"
    assert mapped["filename_hint"] == "ionic_series.csv"
    assert mapped["warnings"] == ["ok"]


def test_batch_summary_response_payload_mapping() -> None:
    payload = BatchSummaryResponsePayload(
        total_count=2,
        success_count=1,
        error_count=1,
        rows=(
            BatchSummaryRowPayload(
                outcar_path=str(FIXTURE),
                status="ok",
                system_name="Si2",
                nions=2,
                ionic_steps=2,
                electronic_iterations=4,
                final_total_energy_ev=-10.5,
                final_fermi_energy_ev=5.2,
                max_force_ev_per_a=0.005,
                warnings=("ok",),
                error=None,
            ),
            BatchSummaryRowPayload(
                outcar_path="/missing/OUTCAR",
                status="error",
                system_name=None,
                nions=None,
                ionic_steps=None,
                electronic_iterations=None,
                final_total_energy_ev=None,
                final_fermi_energy_ev=None,
                max_force_ev_per_a=None,
                warnings=(),
                error={"code": "FILE_NOT_FOUND", "message": "missing"},
            ),
        ),
    )

    mapped = payload.to_mapping()
    assert mapped["total_count"] == 2
    assert mapped["success_count"] == 1
    assert mapped["error_count"] == 1
    assert mapped["rows"][0]["warnings"] == ["ok"]
    assert mapped["rows"][1]["error"]["code"] == "FILE_NOT_FOUND"


def test_discover_outcar_runs_response_payload_mapping() -> None:
    payload = DiscoverOutcarRunsResponsePayload(
        root_dir=str(DISCOVERY_ROOT_FIXTURE),
        recursive=True,
        max_runs=10,
        total_discovered=2,
        returned_count=2,
        outcar_paths=(
            str(DISCOVERY_ROOT_FIXTURE / "run_a" / "OUTCAR"),
            str(DISCOVERY_ROOT_FIXTURE / "group" / "run_b" / "OUTCAR"),
        ),
        run_dirs=(
            str(DISCOVERY_ROOT_FIXTURE / "run_a"),
            str(DISCOVERY_ROOT_FIXTURE / "group" / "run_b"),
        ),
        warnings=("truncated",),
    )

    mapped = payload.to_mapping()
    assert mapped["total_discovered"] == 2
    assert mapped["returned_count"] == 2
    assert mapped["run_dirs"][0].endswith("run_a")
    assert mapped["warnings"] == ["truncated"]


def test_batch_diagnostics_response_payload_mapping() -> None:
    payload = BatchDiagnosticsResponsePayload(
        total_count=2,
        success_count=1,
        error_count=1,
        rows=(
            BatchDiagnosticsRowPayload(
                outcar_path=str(FIXTURE),
                status="ok",
                final_total_energy_ev=-10.5,
                max_force_ev_per_a=0.005,
                external_pressure_kb=-1.23,
                is_energy_converged=True,
                is_force_converged=True,
                is_converged=True,
                warnings=("ok",),
                error=None,
            ),
            BatchDiagnosticsRowPayload(
                outcar_path="/missing/OUTCAR",
                status="error",
                final_total_energy_ev=None,
                max_force_ev_per_a=None,
                external_pressure_kb=None,
                is_energy_converged=None,
                is_force_converged=None,
                is_converged=None,
                warnings=(),
                error={"code": "FILE_NOT_FOUND", "message": "missing"},
            ),
        ),
    )

    mapped = payload.to_mapping()
    assert mapped["total_count"] == 2
    assert mapped["success_count"] == 1
    assert mapped["error_count"] == 1
    assert mapped["rows"][0]["is_converged"] is True
    assert mapped["rows"][1]["error"]["code"] == "FILE_NOT_FOUND"


def test_batch_insights_response_payload_mapping() -> None:
    payload = BatchInsightsResponsePayload(
        total_count=2,
        success_count=1,
        error_count=1,
        converged_count=1,
        not_converged_count=0,
        unknown_convergence_count=0,
        energy_min_ev=-10.5,
        energy_max_ev=-10.5,
        energy_mean_ev=-10.5,
        energy_span_ev=0.0,
        mean_max_force_ev_per_a=0.005,
        top_lowest_energy=(
            BatchInsightsTopRunPayload(
                rank=1,
                outcar_path=str(FIXTURE),
                system_name="Si2",
                final_total_energy_ev=-10.5,
                max_force_ev_per_a=0.005,
                is_converged=True,
            ),
        ),
        rows=(
            BatchInsightsRowPayload(
                outcar_path=str(FIXTURE),
                status="ok",
                system_name="Si2",
                final_total_energy_ev=-10.5,
                max_force_ev_per_a=0.005,
                external_pressure_kb=-1.23,
                is_converged=True,
                warnings=("ok",),
                error=None,
            ),
            BatchInsightsRowPayload(
                outcar_path="/missing/OUTCAR",
                status="error",
                system_name=None,
                final_total_energy_ev=None,
                max_force_ev_per_a=None,
                external_pressure_kb=None,
                is_converged=None,
                warnings=(),
                error={"code": "FILE_NOT_FOUND", "message": "missing"},
            ),
        ),
    )

    mapped = payload.to_mapping()
    assert mapped["total_count"] == 2
    assert mapped["success_count"] == 1
    assert mapped["error_count"] == 1
    assert mapped["top_lowest_energy"][0]["rank"] == 1
    assert mapped["rows"][0]["warnings"] == ["ok"]
    assert mapped["rows"][1]["error"]["code"] == "FILE_NOT_FOUND"


def test_run_report_response_payload_mapping() -> None:
    payload = RunReportResponsePayload(
        run_dir=str(DISCOVERY_ROOT_FIXTURE / "run_a"),
        outcar_path=str(FIXTURE),
        eigenval_path=None,
        doscar_path=None,
        summary={"source_path": str(FIXTURE), "final_total_energy_ev": -10.5},
        diagnostics={"source_path": str(FIXTURE), "convergence": {"is_converged": True}},
        electronic_metadata=None,
        is_converged=True,
        recommended_status="ready",
        suggested_actions=("Run is converged; suitable for downstream screening/comparison",),
        warnings=("ok",),
    )

    mapped = payload.to_mapping()
    assert mapped["run_dir"].endswith("run_a")
    assert mapped["is_converged"] is True
    assert mapped["recommended_status"] == "ready"
    assert mapped["suggested_actions"][0].startswith("Run is converged")
    assert mapped["warnings"] == ["ok"]
