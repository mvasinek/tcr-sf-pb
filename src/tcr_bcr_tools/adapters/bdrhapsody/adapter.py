"""BD Rhapsody adapter skeleton."""

from __future__ import annotations

from pathlib import Path

from tcr_bcr_tools.adapters.base import AdapterValidationResult, BaseAdapter


class BDRhapsodyAdapter(BaseAdapter):
    """Placeholder adapter for BD Rhapsody datasets."""

    name = "bdrhapsody"
    version = "0.5.3"
    description = "BD Rhapsody adapter (not implemented)."

    @classmethod
    def validate_input(cls, dataset_path: Path) -> AdapterValidationResult:
        return AdapterValidationResult(
            valid=False,
            errors=["Adapter not implemented yet"],
            detected_files=[],
            summary={"dataset_path": str(dataset_path)},
        )

    @classmethod
    def normalize(
        cls,
        dataset_path: Path,
        output_path: Path,
        *,
        dataset_id: str = "",
    ) -> Path:
        raise NotImplementedError("Adapter not implemented yet")
