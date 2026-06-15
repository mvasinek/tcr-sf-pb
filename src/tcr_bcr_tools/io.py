"""File discovery and I/O helpers."""

from pathlib import Path


def find_annotation_files(input_dir: Path) -> list[Path]:
    """Recursively find all files ending with ``annotations.csv.gz``."""
    return sorted(input_dir.rglob("*annotations.csv.gz"))
