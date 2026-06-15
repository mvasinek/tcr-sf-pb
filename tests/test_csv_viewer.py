"""Tests for CSV viewer helpers."""

from pathlib import Path

import pandas as pd

from tcr_bcr_tools.gui.csv_viewer import filter_dataframe, paginate_dataframe
from tcr_bcr_tools.project.output_registry import load_csv_preview


def test_filter_and_paginate_dataframe() -> None:
    df = pd.DataFrame({"patient": ["p1", "p2", "p3"], "value": [1, 2, 3]})
    filtered = filter_dataframe(df, query="p2", columns=["patient"])
    assert len(filtered) == 1
    page = paginate_dataframe(df, page=2, page_size=2)
    assert len(page) == 1


def test_load_csv_preview(tmp_path: Path) -> None:
    path = tmp_path / "demo.csv"
    path.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    df, truncated = load_csv_preview(path)
    assert len(df) == 2
    assert truncated is False
