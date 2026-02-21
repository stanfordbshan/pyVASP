"""Transport-agnostic application services for pyVASP workflows."""

from __future__ import annotations

from pyvasp.application.ports import OutcarSummaryReader
from pyvasp.core.errors import ParseError, ValidationError
from pyvasp.core.payloads import SummaryRequestPayload, SummaryResponsePayload
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
