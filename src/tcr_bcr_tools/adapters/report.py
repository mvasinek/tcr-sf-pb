"""Adapter run report persistence."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from tcr_bcr_tools.adapters.schema import ADAPTER_REPORT_FILE
from tcr_bcr_tools.project.manifest import save_yaml


def write_adapter_report(
    dataset_path: Path,
    *,
    adapter_name: str,
    adapter_version: str,
    started: str,
    finished: str,
    status: str,
    detected_files: list[Path],
    output_path: Path,
    df: pd.DataFrame | None = None,
) -> Path:
    """Write adapter_report.yaml under dataset intermediate/."""
    report_path = dataset_path / "intermediate" / ADAPTER_REPORT_FILE
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "adapter": {
            "name": adapter_name,
            "version": adapter_version,
        },
        "run": {
            "started": started,
            "finished": finished,
            "status": status,
        },
        "input": {
            "detected_files": [str(path) for path in detected_files],
            "n_files": len(detected_files),
        },
        "output": {
            "unified_annotations": str(output_path),
            "n_rows": int(len(df)) if df is not None else 0,
            "columns": list(df.columns) if df is not None else [],
        },
    }
    save_yaml(report_path, report)
    return report_path
