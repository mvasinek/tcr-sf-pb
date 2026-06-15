"""Search helpers for the results browser."""

from __future__ import annotations

from tcr_bcr_tools.project.output_registry import OutputEntry, OutputRegistry


def search_registry(registry: OutputRegistry, query: str) -> list[OutputEntry]:
    """Search outputs in the registry."""
    return registry.search_outputs(query)
