"""HTTP route definitions for pyVASP API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from pyvasp.api.schemas import ErrorSchema, SummaryRequestSchema, SummaryResponseSchema
from pyvasp.application.use_cases import SummarizeOutcarUseCase
from pyvasp.core.errors import ValidationError
from pyvasp.core.payloads import validate_summary_request


def create_router(use_case: SummarizeOutcarUseCase) -> APIRouter:
    """Build an APIRouter bound to application use-cases."""

    router = APIRouter()

    @router.post(
        "/v1/outcar/summary",
        response_model=SummaryResponseSchema,
        responses={
            status.HTTP_400_BAD_REQUEST: {"model": ErrorSchema},
            status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorSchema},
        },
    )
    def summarize_outcar(request: SummaryRequestSchema) -> SummaryResponseSchema:
        try:
            payload = validate_summary_request(request.model_dump())
        except ValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        result = use_case.execute(payload)
        if not result.ok or result.value is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=result.error or "Unknown application error",
            )

        return SummaryResponseSchema(**result.value.to_mapping())

    return router
