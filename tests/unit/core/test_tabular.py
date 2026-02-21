from __future__ import annotations

from pyvasp.core.tabular import build_csv_text


def test_build_csv_text_serializes_headers_rows_and_none() -> None:
    text = build_csv_text(
        headers=("a", "b", "c"),
        rows=[
            (1, 2.5, None),
            (2, -3.25, "ok"),
        ],
    )

    assert text.splitlines()[0] == "a,b,c"
    assert text.splitlines()[1] == "1,2.5,"
    assert text.splitlines()[2] == "2,-3.25,ok"
