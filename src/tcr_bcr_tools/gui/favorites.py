"""Favorites helpers for the results browser."""

from __future__ import annotations

from tcr_bcr_tools.project.output_registry import OutputEntry, OutputRegistry


def favorite_entries(registry: OutputRegistry) -> list[OutputEntry]:
    """Return favorite outputs."""
    favorite_ids = set(registry.list_favorites())
    return [entry for entry in registry.list_outputs() if entry.id in favorite_ids]
