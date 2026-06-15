"""Status formatting helpers."""

from __future__ import annotations

from tcr_bcr_tools.gui.constants import STATUS_LABELS
from tcr_bcr_tools.pipeline.registry import list_steps


def format_status(status: str) -> tuple[str, str]:
    """Return display label and color for a pipeline status."""
    normalized = status.lower() if status else "pending"
    return STATUS_LABELS.get(normalized, (status or "Pending", "gray"))


def build_status_rows(status_map: dict[str, str]) -> list[dict[str, str]]:
    """Build table rows for pipeline steps using the registry."""
    rows: list[dict[str, str]] = []
    for step in list_steps():
        raw_status = status_map.get(step.id, "pending")
        display, color = format_status(raw_status)
        rows.append(
            {
                "step_key": step.id,
                "step": step.name,
                "status": raw_status or "pending",
                "display": display,
                "color": color,
            }
        )
    return rows
