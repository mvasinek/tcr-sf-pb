"""Project output registry for indexed analysis results."""

from __future__ import annotations

import json
import uuid
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from tcr_bcr_tools import __version__
from tcr_bcr_tools.project.manifest import load_yaml, save_yaml

OUTPUT_TYPES = {"csv", "png", "html", "yaml", "json", "txt", "directory"}
FAVORITES_FILE = "favorites.yaml"
RECENT_FILE = "recent.yaml"
MAX_RECENT = 20
CSV_PREVIEW_LIMIT = 5000
CSV_ROW_WARNING = 100_000


@dataclass
class OutputEntry:
    """One registered project output."""

    id: str
    name: str
    analysis: str
    type: str
    created: str
    tool_version: str
    git_branch: str
    git_commit: str
    git_tag: str
    path: str
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    pipeline_step: str = ""
    size_bytes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OutputEntry:
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            analysis=str(data.get("analysis", "")),
            type=str(data.get("type", "txt")),
            created=str(data.get("created", "")),
            tool_version=str(data.get("tool_version", "")),
            git_branch=str(data.get("git_branch", data.get("git", {}).get("branch", "unknown"))),
            git_commit=str(data.get("git_commit", data.get("git", {}).get("commit", "unknown"))),
            git_tag=str(data.get("git_tag", data.get("git", {}).get("tag", "unknown"))),
            path=str(data.get("path", "")),
            description=str(data.get("description", "")),
            metadata=dict(data.get("metadata", {})),
            pipeline_step=str(data.get("pipeline_step", "")),
            size_bytes=int(data.get("size_bytes", 0)),
        )


def infer_output_type(path: Path) -> str:
    """Infer registry output type from a filesystem path."""
    if path.is_dir():
        return "directory"
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix in {".png", ".jpg", ".jpeg", ".svg", ".pdf"}:
        return "png"
    if suffix in {".html", ".htm"}:
        return "html"
    if suffix in {".yaml", ".yml"}:
        return "yaml"
    if suffix == ".json":
        return "json"
    return "txt"


def _entry_id_for_path(path: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, path))


class OutputRegistry:
    """Manage indexed outputs for one project."""

    def __init__(self, project_root: Path, workspace_root: Path) -> None:
        self.project_root = project_root
        self.workspace_root = workspace_root
        self.cache_dir = project_root / "cache"
        self.manifest_path = project_root / "project.yaml"

    def _load_manifest(self) -> dict[str, Any]:
        if self.manifest_path.exists():
            return load_yaml(self.manifest_path)
        return {}

    def _save_manifest(self, data: dict[str, Any]) -> None:
        save_yaml(self.manifest_path, data)

    def _entries_from_manifest(self) -> list[OutputEntry]:
        data = self._load_manifest()
        raw = data.get("output_registry", [])
        if not isinstance(raw, list):
            return []
        return [OutputEntry.from_dict(item) for item in raw if isinstance(item, dict)]

    def _write_entries(self, entries: list[OutputEntry]) -> None:
        data = self._load_manifest()
        data["output_registry"] = [entry.to_dict() for entry in entries]
        self._save_manifest(data)

    def register_output(
        self,
        *,
        path: str,
        name: str,
        analysis: str,
        output_type: str,
        pipeline_step: str = "",
        description: str = "",
        metadata: dict[str, Any] | None = None,
        git_branch: str = "unknown",
        git_commit: str = "unknown",
        git_tag: str = "unknown",
        tool_version: str | None = None,
    ) -> OutputEntry:
        """Register or update one output entry."""
        abs_path = self.workspace_root / path
        size_bytes = 0
        if abs_path.is_file():
            size_bytes = abs_path.stat().st_size
        entry = OutputEntry(
            id=_entry_id_for_path(path),
            name=name,
            analysis=analysis,
            type=output_type,
            created=datetime.now().isoformat(timespec="seconds"),
            tool_version=tool_version or __version__,
            git_branch=git_branch,
            git_commit=git_commit,
            git_tag=git_tag,
            path=path,
            description=description,
            metadata=metadata or {},
            pipeline_step=pipeline_step,
            size_bytes=size_bytes,
        )
        entries = self._entries_from_manifest()
        entries = [item for item in entries if item.id != entry.id]
        entries.append(entry)
        self._write_entries(entries)
        return entry

    def register_from_step(
        self,
        step_id: str,
        outputs: dict[str, list[str]],
        *,
        git_branch: str = "unknown",
        git_commit: str = "unknown",
        git_tag: str = "unknown",
        tool_version: str | None = None,
        description: str = "",
    ) -> list[OutputEntry]:
        """Register all paths produced by one pipeline step."""
        registered: list[OutputEntry] = []
        for file_type, paths in outputs.items():
            for rel_path in paths:
                abs_path = self.workspace_root / rel_path
                output_type = file_type if file_type in OUTPUT_TYPES else infer_output_type(abs_path)
                if abs_path.is_dir():
                    output_type = "directory"
                analysis = step_id
                if "/" in rel_path:
                    parts = Path(rel_path).parts
                    if len(parts) >= 2:
                        analysis = parts[-2]
                registered.append(
                    self.register_output(
                        path=rel_path,
                        name=Path(rel_path).name,
                        analysis=analysis,
                        output_type=output_type,
                        pipeline_step=step_id,
                        description=description or f"Output from {step_id}",
                        git_branch=git_branch,
                        git_commit=git_commit,
                        git_tag=git_tag,
                        tool_version=tool_version,
                        metadata={"file_type": file_type},
                    )
                )
        return registered

    def list_outputs(self) -> list[OutputEntry]:
        """Return all registered outputs sorted by created time."""
        return sorted(self._entries_from_manifest(), key=lambda item: item.created, reverse=True)

    def find_output(self, output_id: str) -> OutputEntry | None:
        """Find one output by id."""
        for entry in self.list_outputs():
            if entry.id == output_id:
                return entry
        return None

    def list_analysis_outputs(self, analysis: str) -> list[OutputEntry]:
        """Return outputs for one analysis or pipeline step."""
        analysis_lower = analysis.lower()
        return [
            entry
            for entry in self.list_outputs()
            if entry.analysis.lower() == analysis_lower
            or entry.pipeline_step.lower() == analysis_lower
        ]

    def search_outputs(self, query: str) -> list[OutputEntry]:
        """Search outputs by filename, analysis, description, or type."""
        needle = query.lower().strip()
        if not needle:
            return self.list_outputs()
        return [
            entry
            for entry in self.list_outputs()
            if needle in entry.name.lower()
            or needle in entry.analysis.lower()
            or needle in entry.description.lower()
            or needle in entry.type.lower()
        ]

    def _favorites_path(self) -> Path:
        return self.cache_dir / FAVORITES_FILE

    def _recent_path(self) -> Path:
        return self.cache_dir / RECENT_FILE

    def list_favorites(self) -> list[str]:
        """Return favorite output ids."""
        path = self._favorites_path()
        if not path.exists():
            return []
        data = load_yaml(path)
        favorites = data.get("favorites", [])
        return [str(item) for item in favorites] if isinstance(favorites, list) else []

    def favorite(self, output_id: str, *, enabled: bool = True) -> None:
        """Mark or unmark an output as favorite."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        favorites = set(self.list_favorites())
        if enabled:
            favorites.add(output_id)
        else:
            favorites.discard(output_id)
        save_yaml(self._favorites_path(), {"favorites": sorted(favorites)})

    def is_favorite(self, output_id: str) -> bool:
        return output_id in self.list_favorites()

    def recent(self) -> list[dict[str, str]]:
        """Return recent opened outputs."""
        path = self._recent_path()
        if not path.exists():
            return []
        data = load_yaml(path)
        items = data.get("recent", [])
        return [dict(item) for item in items if isinstance(item, dict)] if isinstance(items, list) else []

    def record_recent(self, output_id: str) -> None:
        """Record that an output was opened."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        recent_items = [item for item in self.recent() if item.get("id") != output_id]
        recent_items.insert(
            0,
            {"id": output_id, "opened": datetime.now().isoformat(timespec="seconds")},
        )
        save_yaml(self._recent_path(), {"recent": recent_items[:MAX_RECENT]})

    def statistics(self) -> dict[str, Any]:
        """Return project output statistics."""
        entries = self.list_outputs()
        total_size = sum(entry.size_bytes for entry in entries)
        figures = [entry for entry in entries if entry.type == "png"]
        tables = [entry for entry in entries if entry.type == "csv"]
        last_created = entries[0].created if entries else ""
        return {
            "outputs": len(entries),
            "figures": len(figures),
            "tables": len(tables),
            "disk_usage_bytes": total_size,
            "last_execution": last_created,
            "tool_version": __version__,
        }

    def resolve_path(self, entry: OutputEntry) -> Path:
        """Resolve workspace-relative registry path."""
        return self.workspace_root / entry.path

    def export_zip(self, output_ids: list[str], target_zip: Path) -> Path:
        """Export selected outputs into a ZIP archive."""
        target_zip.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for output_id in output_ids:
                entry = self.find_output(output_id)
                if entry is None:
                    continue
                path = self.resolve_path(entry)
                if path.is_file():
                    archive.write(path, arcname=entry.path)
                elif path.is_dir():
                    for file_path in path.rglob("*"):
                        if file_path.is_file():
                            rel = file_path.relative_to(self.workspace_root)
                            archive.write(file_path, arcname=str(rel))
        return target_zip

    def export_all_zip(self, target_zip: Path) -> Path:
        """Export all registered outputs into a ZIP archive."""
        return self.export_zip([entry.id for entry in self.list_outputs()], target_zip)


def load_csv_preview(path: Path, *, limit: int = CSV_PREVIEW_LIMIT):
    """Load a CSV preview with optional truncation warning."""
    import pandas as pd

    total_rows = sum(1 for _ in path.open(encoding="utf-8")) - 1
    truncated = total_rows > CSV_ROW_WARNING
    df = pd.read_csv(path, nrows=limit)
    return df, truncated
