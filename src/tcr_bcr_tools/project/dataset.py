"""Dataset manifest and filesystem layout."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from tcr_bcr_tools.adapters.base import AdapterValidationResult, BaseAdapter
from tcr_bcr_tools.adapters.report import write_adapter_report
from tcr_bcr_tools.adapters.schema import UNIFIED_ANNOTATIONS_FILE
from tcr_bcr_tools.project.manifest import load_yaml, save_yaml

DATASET_MANIFEST = "dataset.yaml"


def _default_dataset_manifest(
    dataset_id: str,
    *,
    title: str = "",
    source: str = "",
    adapter: str = "tenx",
    raw_source: str = "",
) -> dict[str, Any]:
    files: dict[str, str] = {
        "raw": "raw/",
        "intermediate": "intermediate/",
    }
    if raw_source:
        files["raw_source"] = raw_source
    return {
        "dataset": {
            "id": dataset_id,
            "title": title or dataset_id,
            "source": source,
            "adapter": adapter,
            "created": date.today().isoformat(),
        },
        "files": files,
    }


class Dataset:
    """A shared dataset with raw data and adapter-produced intermediate tables."""

    def __init__(self, root: Path, dataset_id: str) -> None:
        self.root = root
        self.dataset_id = dataset_id
        self.manifest_path = root / DATASET_MANIFEST
        self._data: dict[str, Any] = {}

    @property
    def raw_dir(self) -> Path:
        return self.root / "raw"

    @property
    def intermediate_dir(self) -> Path:
        return self.root / "intermediate"

    def load(self) -> dict[str, Any]:
        """Load dataset manifest from disk."""
        self._data = load_yaml(self.manifest_path)
        return self._data

    def save(self) -> None:
        """Persist dataset manifest to disk."""
        save_yaml(self.manifest_path, self._data)

    def validate(self) -> list[str]:
        """Return validation errors; empty list means valid."""
        errors: list[str] = []
        if not self.manifest_path.exists():
            errors.append(f"Missing manifest: {self.manifest_path}")
            return errors

        if not self._data:
            self.load()

        dataset_meta = self._data.get("dataset", {})
        if dataset_meta.get("id") != self.dataset_id:
            errors.append(
                f"Manifest id '{dataset_meta.get('id')}' does not match '{self.dataset_id}'."
            )

        if not self.raw_dir.is_dir():
            errors.append(f"Missing raw directory: {self.raw_dir}")
        if not self.intermediate_dir.is_dir():
            errors.append(f"Missing intermediate directory: {self.intermediate_dir}")

        return errors

    def adapter(self) -> str:
        """Return the adapter name for this dataset."""
        if not self._data:
            self.load()
        return str(self._data.get("dataset", {}).get("adapter", ""))

    def get_adapter(self) -> type[BaseAdapter]:
        """Return the registered adapter class for this dataset."""
        from tcr_bcr_tools.adapters.registry import get_adapter

        return get_adapter(self.adapter())

    def validate_with_adapter(self) -> AdapterValidationResult:
        """Validate raw inputs using the dataset adapter."""
        return self.get_adapter().validate_input(self.root)

    def normalize_with_adapter(self, output_path: Path | None = None) -> Path:
        """Normalize raw inputs to unified_annotations.csv via the adapter."""
        adapter_cls = self.get_adapter()
        started = datetime.now().isoformat(timespec="seconds")
        validation = adapter_cls.validate_input(self.root)
        if not validation.valid:
            raise ValueError("; ".join(validation.errors))

        output = output_path or self.intermediate_dir / UNIFIED_ANNOTATIONS_FILE
        adapter_cls.normalize(self.root, output, dataset_id=self.dataset_id)
        df = pd.read_csv(output)
        finished = datetime.now().isoformat(timespec="seconds")
        write_adapter_report(
            self.root,
            adapter_name=adapter_cls.name,
            adapter_version=adapter_cls.version,
            started=started,
            finished=finished,
            status="completed",
            detected_files=validation.detected_files,
            output_path=output,
            df=df,
        )
        return output

    def unified_annotations_path(self) -> Path:
        """Return path to unified annotation output."""
        return self.intermediate_dir / UNIFIED_ANNOTATIONS_FILE

    def has_unified_annotations(self) -> bool:
        """Return True when unified_annotations.csv exists."""
        return self.unified_annotations_path().is_file()

    def raw_source_path(self) -> Path | None:
        """Return external raw directory if registered."""
        if not self._data:
            self.load()
        raw_source = self._data.get("files", {}).get("raw_source")
        if not raw_source:
            return None
        return Path(raw_source)

    def count_raw_files(self) -> int:
        """Count files in raw directory or external raw source."""
        source = self.raw_source_path()
        target = source if source and source.exists() else self.raw_dir
        if not target.is_dir():
            return 0
        return sum(1 for path in target.rglob("*") if path.is_file())

    def metadata(self) -> dict[str, Any]:
        """Return dataset metadata from manifest."""
        if not self._data:
            self.load()
        return dict(self._data.get("dataset", {}))

    @classmethod
    def create(
        cls,
        datasets_root: Path,
        dataset_id: str,
        *,
        title: str = "",
        source: str = "",
        adapter: str = "tenx",
        raw_source: str = "",
    ) -> Dataset:
        """Create a new dataset directory and manifest."""
        root = datasets_root / dataset_id
        root.mkdir(parents=True, exist_ok=True)
        (root / "raw").mkdir(exist_ok=True)
        (root / "intermediate").mkdir(exist_ok=True)

        instance = cls(root, dataset_id)
        instance._data = _default_dataset_manifest(
            dataset_id,
            title=title,
            source=source,
            adapter=adapter,
            raw_source=raw_source,
        )
        instance.save()
        return instance
