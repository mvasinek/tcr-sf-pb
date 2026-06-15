"""PNG and image preview helpers."""

from __future__ import annotations

from pathlib import Path

from tcr_bcr_tools.project.output_registry import OutputEntry


def image_metadata(path: Path, entry: OutputEntry) -> dict[str, str]:
    """Return display metadata for an image output."""
    resolution = "unknown"
    try:
        from PIL import Image

        with Image.open(path) as image:
            resolution = f"{image.width} x {image.height}"
    except Exception:  # noqa: BLE001 - optional dependency path
        resolution = "unknown"
    return {
        "resolution": resolution,
        "created": entry.created,
        "analysis": entry.analysis,
        "description": entry.description,
    }
