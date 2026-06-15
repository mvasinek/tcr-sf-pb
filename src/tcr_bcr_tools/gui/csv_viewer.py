"""CSV preview helpers for the results browser."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from tcr_bcr_tools.project.output_registry import CSV_PREVIEW_LIMIT, load_csv_preview


def filter_dataframe(
    df: pd.DataFrame,
    *,
    query: str = "",
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """Filter and subset a dataframe for preview."""
    result = df.copy()
    if columns:
        available = [column for column in columns if column in result.columns]
        if available:
            result = result[available]
    if query:
        mask = result.astype(str).apply(
            lambda row: row.str.contains(query, case=False, na=False).any(),
            axis=1,
        )
        result = result.loc[mask]
    return result


def paginate_dataframe(df: pd.DataFrame, page: int, page_size: int) -> pd.DataFrame:
    """Return one page of a dataframe."""
    start = max(page - 1, 0) * page_size
    end = start + page_size
    return df.iloc[start:end]


def load_csv_for_viewer(path: Path) -> tuple[pd.DataFrame, bool]:
    """Load CSV data for interactive viewing."""
    return load_csv_preview(path, limit=CSV_PREVIEW_LIMIT)
