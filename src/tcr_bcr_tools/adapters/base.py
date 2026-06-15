"""Base adapter interface for dataset normalization."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseAdapter(ABC):
    """Convert external dataset formats into the unified internal model."""

    name: str = "base"

    def __init__(self, dataset_root: Path) -> None:
        self.dataset_root = dataset_root
        self.raw_dir = dataset_root / "raw"
        self.intermediate_dir = dataset_root / "intermediate"

    @abstractmethod
    def validate(self) -> list[str]:
        """Return validation errors for raw inputs."""

    @abstractmethod
    def extract(self) -> Path:
        """Extract or load raw data into intermediate representation."""

    @abstractmethod
    def normalize(self) -> Path:
        """Normalize extracted data to the unified internal table."""

    @abstractmethod
    def metadata(self) -> dict[str, Any]:
        """Return adapter-specific metadata."""
