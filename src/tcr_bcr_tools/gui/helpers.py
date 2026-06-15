"""Status formatting helpers."""

from __future__ import annotations

from tcr_bcr_tools.gui.constants import PIPELINE_STEPS, STATUS_LABELS


def format_status(status: str) -> tuple[str, str]:
    """Return display label and color for a pipeline status."""
    normalized = status.lower() if status else "pending"
    return STATUS_LABELS.get(normalized, (status or "Pending", "gray"))


def build_status_rows(status_map: dict[str, str]) -> list[dict[str, str]]:
    """Build table rows for the project status panel."""
    rows: list[dict[str, str]] = []
    for step_key, step_label in PIPELINE_STEPS:
        raw_status = status_map.get(step_key, "pending")
        display, color = format_status(raw_status)
        rows.append(
            {
                "step_key": step_key,
                "step": step_label,
                "status": raw_status or "pending",
                "display": display,
                "color": color,
            }
        )
    return rows
