"""YAML preview helpers."""

from __future__ import annotations

from pathlib import Path


def load_yaml_text(path: Path) -> str:
    """Load YAML file contents as text."""
    return path.read_text(encoding="utf-8")
