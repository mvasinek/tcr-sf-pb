"""Gallery helpers for figures and tables."""

from __future__ import annotations

from tcr_bcr_tools.project.output_registry import OutputEntry, OutputRegistry


def list_figure_entries(registry: OutputRegistry) -> list[OutputEntry]:
    """Return PNG/image outputs."""
    return [entry for entry in registry.list_outputs() if entry.type == "png"]


def list_table_entries(registry: OutputRegistry) -> list[OutputEntry]:
    """Return CSV outputs."""
    return [entry for entry in registry.list_outputs() if entry.type == "csv"]
