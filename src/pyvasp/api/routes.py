"""HTTP route definitions for pyVASP API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status

from pyvasp.api.schemas import (
    BatchDiagnosticsRequestSchema,
    BatchDiagnosticsResponseSchema,
    BatchInsightsRequestSchema,
    BatchInsightsResponseSchema,
    BatchSummaryRequestSchema,
    BatchSummaryResponseSchema,
    ConvergenceProfileRequestSchema,
    ConvergenceProfileResponseSchema,
    DiscoverOutcarRunsRequestSchema,
    DiscoverOutcarRunsResponseSchema,
    DiagnosticsRequestSchema,
    DiagnosticsResponseSchema,
    DosProfileRequestSchema,
    DosProfileResponseSchema,
    ElectronicMetadataRequestSchema,
    ElectronicMetadataResponseSchema,
    ErrorSchema,
    ExportTabularRequestSchema,
    ExportTabularResponseSchema,
    GenerateRelaxInputRequestSchema,
    GenerateRelaxInputResponseSchema,
    IonicSeriesRequestSchema,
    IonicSeriesResponseSchema,
    RunReportRequestSchema,
    RunReportResponseSchema,
    SummaryRequestSchema,
    SummaryResponseSchema,
)
from pyvasp.application.use_cases import (
    BatchDiagnoseOutcarUseCase,
    BuildBatchInsightsUseCase,
    BatchSummarizeOutcarUseCase,
    BuildConvergenceProfileUseCase,
    BuildDosProfileUseCase,
    BuildIonicSeriesUseCase,
    BuildRunReportUseCase,
    DiscoverOutcarRunsUseCase,
    DiagnoseOutcarUseCase,
    ExportOutcarTabularUseCase,
    GenerateRelaxInputUseCase,
    ParseElectronicMetadataUseCase,
    SummarizeOutcarUseCase,
)
from pyvasp.core.errors import AppError, ErrorCode, normalize_error
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
    validate_run_report_request,
    validate_summary_request,
)


def create_router(
    summary_use_case: SummarizeOutcarUseCase,
    discover_outcar_runs_use_case: DiscoverOutcarRunsUseCase,
    batch_summary_use_case: BatchSummarizeOutcarUseCase,
    batch_diagnostics_use_case: BatchDiagnoseOutcarUseCase,
    batch_insights_use_case: BuildBatchInsightsUseCase,
    run_report_use_case: BuildRunReportUseCase,
    diagnostics_use_case: DiagnoseOutcarUseCase,
    profile_use_case: BuildConvergenceProfileUseCase,
    ionic_series_use_case: BuildIonicSeriesUseCase,
    export_tabular_use_case: ExportOutcarTabularUseCase,
    electronic_use_case: ParseElectronicMetadataUseCase,
    dos_profile_use_case: BuildDosProfileUseCase,
    relax_input_use_case: GenerateRelaxInputUseCase,
) -> APIRouter:
    """Build an APIRouter bound to application use-cases."""

    router = APIRouter()

    error_responses = {
        status.HTTP_400_BAD_REQUEST: {"model": ErrorSchema},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorSchema},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorSchema},
    }

    @router.post("/v1/outcar/summary", response_model=SummaryResponseSchema, responses=error_responses)
    def summarize_outcar(request: SummaryRequestSchema) -> SummaryResponseSchema:
        try:
            payload = validate_summary_request(request.model_dump())
        except Exception as exc:
            _raise_http_from_error(normalize_error(exc))

        result = summary_use_case.execute(payload)
        if not result.ok or result.value is None:
            _raise_http_from_error(result.error or AppError(ErrorCode.INTERNAL_ERROR, "Unknown application error"))
        return SummaryResponseSchema(**result.value.to_mapping())

    @router.post("/v1/outcar/discover", response_model=DiscoverOutcarRunsResponseSchema, responses=error_responses)
    def discover_outcar_runs(request: DiscoverOutcarRunsRequestSchema) -> DiscoverOutcarRunsResponseSchema:
        try:
            payload = validate_discover_outcar_runs_request(request.model_dump())
        except Exception as exc:
            _raise_http_from_error(normalize_error(exc))

        result = discover_outcar_runs_use_case.execute(payload)
        if not result.ok or result.value is None:
            _raise_http_from_error(result.error or AppError(ErrorCode.INTERNAL_ERROR, "Unknown application error"))
        return DiscoverOutcarRunsResponseSchema(**result.value.to_mapping())

    @router.post("/v1/outcar/batch-summary", response_model=BatchSummaryResponseSchema, responses=error_responses)
    def batch_summary(request: BatchSummaryRequestSchema) -> BatchSummaryResponseSchema:
        try:
            payload = validate_batch_summary_request(request.model_dump())
        except Exception as exc:
            _raise_http_from_error(normalize_error(exc))

        result = batch_summary_use_case.execute(payload)
        if not result.ok or result.value is None:
            _raise_http_from_error(result.error or AppError(ErrorCode.INTERNAL_ERROR, "Unknown application error"))
        return BatchSummaryResponseSchema(**result.value.to_mapping())

    @router.post(
        "/v1/outcar/batch-diagnostics",
        response_model=BatchDiagnosticsResponseSchema,
        responses=error_responses,
    )
    def batch_diagnostics(request: BatchDiagnosticsRequestSchema) -> BatchDiagnosticsResponseSchema:
        try:
            payload = validate_batch_diagnostics_request(request.model_dump())
        except Exception as exc:
            _raise_http_from_error(normalize_error(exc))

        result = batch_diagnostics_use_case.execute(payload)
        if not result.ok or result.value is None:
            _raise_http_from_error(result.error or AppError(ErrorCode.INTERNAL_ERROR, "Unknown application error"))
        return BatchDiagnosticsResponseSchema(**result.value.to_mapping())

    @router.post(
        "/v1/outcar/batch-insights",
        response_model=BatchInsightsResponseSchema,
        responses=error_responses,
    )
    def batch_insights(request: BatchInsightsRequestSchema) -> BatchInsightsResponseSchema:
        try:
            payload = validate_batch_insights_request(request.model_dump())
        except Exception as exc:
            _raise_http_from_error(normalize_error(exc))

        result = batch_insights_use_case.execute(payload)
        if not result.ok or result.value is None:
            _raise_http_from_error(result.error or AppError(ErrorCode.INTERNAL_ERROR, "Unknown application error"))
        return BatchInsightsResponseSchema(**result.value.to_mapping())

    @router.post(
        "/v1/run/report",
        response_model=RunReportResponseSchema,
        responses=error_responses,
    )
    def run_report(request: RunReportRequestSchema) -> RunReportResponseSchema:
        try:
            payload = validate_run_report_request(request.model_dump())
        except Exception as exc:
            _raise_http_from_error(normalize_error(exc))

        result = run_report_use_case.execute(payload)
        if not result.ok or result.value is None:
            _raise_http_from_error(result.error or AppError(ErrorCode.INTERNAL_ERROR, "Unknown application error"))
        return RunReportResponseSchema(**result.value.to_mapping())

    @router.post("/v1/outcar/diagnostics", response_model=DiagnosticsResponseSchema, responses=error_responses)
    def diagnose_outcar(request: DiagnosticsRequestSchema) -> DiagnosticsResponseSchema:
        try:
            payload = validate_diagnostics_request(request.model_dump())
        except Exception as exc:
            _raise_http_from_error(normalize_error(exc))

        result = diagnostics_use_case.execute(payload)
        if not result.ok or result.value is None:
            _raise_http_from_error(result.error or AppError(ErrorCode.INTERNAL_ERROR, "Unknown application error"))
        return DiagnosticsResponseSchema(**result.value.to_mapping())

    @router.post(
        "/v1/outcar/convergence-profile",
        response_model=ConvergenceProfileResponseSchema,
        responses=error_responses,
    )
    def convergence_profile(request: ConvergenceProfileRequestSchema) -> ConvergenceProfileResponseSchema:
        try:
            payload = validate_convergence_profile_request(request.model_dump())
        except Exception as exc:
            _raise_http_from_error(normalize_error(exc))

        result = profile_use_case.execute(payload)
        if not result.ok or result.value is None:
            _raise_http_from_error(result.error or AppError(ErrorCode.INTERNAL_ERROR, "Unknown application error"))
        return ConvergenceProfileResponseSchema(**result.value.to_mapping())

    @router.post(
        "/v1/outcar/ionic-series",
        response_model=IonicSeriesResponseSchema,
        responses=error_responses,
    )
    def ionic_series(request: IonicSeriesRequestSchema) -> IonicSeriesResponseSchema:
        try:
            payload = validate_ionic_series_request(request.model_dump())
        except Exception as exc:
            _raise_http_from_error(normalize_error(exc))

        result = ionic_series_use_case.execute(payload)
        if not result.ok or result.value is None:
            _raise_http_from_error(result.error or AppError(ErrorCode.INTERNAL_ERROR, "Unknown application error"))
        return IonicSeriesResponseSchema(**result.value.to_mapping())

    @router.post(
        "/v1/outcar/export-tabular",
        response_model=ExportTabularResponseSchema,
        responses=error_responses,
    )
    def export_tabular(request: ExportTabularRequestSchema) -> ExportTabularResponseSchema:
        try:
            payload = validate_export_tabular_request(request.model_dump())
        except Exception as exc:
            _raise_http_from_error(normalize_error(exc))

        result = export_tabular_use_case.execute(payload)
        if not result.ok or result.value is None:
            _raise_http_from_error(result.error or AppError(ErrorCode.INTERNAL_ERROR, "Unknown application error"))
        return ExportTabularResponseSchema(**result.value.to_mapping())

    @router.post(
        "/v1/electronic/metadata",
        response_model=ElectronicMetadataResponseSchema,
        responses=error_responses,
    )
    def electronic_metadata(request: ElectronicMetadataRequestSchema) -> ElectronicMetadataResponseSchema:
        try:
            payload = validate_electronic_metadata_request(request.model_dump())
        except Exception as exc:
            _raise_http_from_error(normalize_error(exc))

        result = electronic_use_case.execute(payload)
        if not result.ok or result.value is None:
            _raise_http_from_error(result.error or AppError(ErrorCode.INTERNAL_ERROR, "Unknown application error"))
        return ElectronicMetadataResponseSchema(**result.value.to_mapping())

    @router.post(
        "/v1/electronic/dos-profile",
        response_model=DosProfileResponseSchema,
        responses=error_responses,
    )
    def electronic_dos_profile(request: DosProfileRequestSchema) -> DosProfileResponseSchema:
        try:
            payload = validate_dos_profile_request(request.model_dump())
        except Exception as exc:
            _raise_http_from_error(normalize_error(exc))

        result = dos_profile_use_case.execute(payload)
        if not result.ok or result.value is None:
            _raise_http_from_error(result.error or AppError(ErrorCode.INTERNAL_ERROR, "Unknown application error"))
        return DosProfileResponseSchema(**result.value.to_mapping())

    @router.post(
        "/v1/input/relax-generate",
        response_model=GenerateRelaxInputResponseSchema,
        responses=error_responses,
    )
    def generate_relax_input(request: GenerateRelaxInputRequestSchema) -> GenerateRelaxInputResponseSchema:
        try:
            payload = validate_generate_relax_input_request(request.model_dump())
        except Exception as exc:
            _raise_http_from_error(normalize_error(exc))

        result = relax_input_use_case.execute(payload)
        if not result.ok or result.value is None:
            _raise_http_from_error(result.error or AppError(ErrorCode.INTERNAL_ERROR, "Unknown application error"))
        return GenerateRelaxInputResponseSchema(**result.value.to_mapping())

    return router


def _raise_http_from_error(error: AppError) -> None:
    raise HTTPException(status_code=_status_for_error(error), detail=_error_detail(error))


def _status_for_error(error: AppError) -> int:
    if error.code in {
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.FILE_NOT_FOUND,
        ErrorCode.FILE_NOT_FILE,
    }:
        return status.HTTP_400_BAD_REQUEST

    if error.code in {
        ErrorCode.PARSE_ERROR,
        ErrorCode.IO_ERROR,
        ErrorCode.UNSUPPORTED_OPERATION,
    }:
        return status.HTTP_422_UNPROCESSABLE_CONTENT

    return status.HTTP_500_INTERNAL_SERVER_ERROR


def _error_detail(error: AppError) -> dict[str, Any]:
    return error.to_mapping()
