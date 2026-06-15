"""Base adapter interface for dataset normalization."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tcr_bcr_tools.adapters.schema import REQUIRED_COLUMNS


@dataclass
class AdapterValidationResult:
    """Result of adapter input or schema validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    detected_files: list[Path] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


class AdapterNotFoundError(KeyError):
    """Raised when an adapter name is not registered."""


class BaseAdapter(ABC):
    """Convert external dataset formats into the unified annotation schema."""

    name: str = "base"
    version: str = "0.0.0"
    description: str = ""

    @classmethod
    @abstractmethod
    def validate_input(cls, dataset_path: Path) -> AdapterValidationResult:
        """Validate raw inputs under a dataset directory."""

    @classmethod
    def extract_metadata(cls, file_path: Path) -> dict[str, str]:
        """Extract metadata from one raw input file."""
        return {}

    @classmethod
    @abstractmethod
    def normalize(
        cls,
        dataset_path: Path,
        output_path: Path,
        *,
        dataset_id: str = "",
    ) -> Path:
        """Normalize raw inputs to unified_annotations.csv."""

    @classmethod
    def get_output_schema(cls) -> list[str]:
        """Return unified output column names."""
        return list(REQUIRED_COLUMNS)
