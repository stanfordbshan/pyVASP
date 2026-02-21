"""Tabular serialization helpers for transport-neutral CSV exports."""

from __future__ import annotations

import csv
from io import StringIO
from typing import Any, Sequence


def build_csv_text(
    *,
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    delimiter: str = ",",
) -> str:
    """Build deterministic CSV text with a normalized newline policy."""

    buffer = StringIO()
    writer = csv.writer(buffer, delimiter=delimiter, lineterminator="\n")
    writer.writerow(list(headers))
    for row in rows:
        writer.writerow([_serialize_cell(value) for value in row])
    return buffer.getvalue()


def _serialize_cell(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.12g}"
    return value
