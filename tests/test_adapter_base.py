"""Tests for BaseAdapter and AdapterValidationResult."""

from pathlib import Path

from tcr_bcr_tools.adapters.base import AdapterValidationResult, BaseAdapter
from tcr_bcr_tools.adapters.tenx.adapter import TenXAdapter


def test_adapter_validation_result_defaults() -> None:
    result = AdapterValidationResult(valid=True)
    assert result.errors == []
    assert result.warnings == []
    assert result.detected_files == []
    assert result.summary == {}


def test_tenx_adapter_is_base_adapter() -> None:
    assert issubclass(TenXAdapter, BaseAdapter)
    assert TenXAdapter.name == "tenx"
    assert TenXAdapter.version
    assert TenXAdapter.description


def test_get_output_schema_matches_required_columns() -> None:
    schema = TenXAdapter.get_output_schema()
    assert "dataset_id" in schema
    assert "sample_id" in schema
    assert "adapter_name" in schema


def test_validate_input_missing_raw(tmp_path: Path) -> None:
    dataset_path = tmp_path / "GSE160097"
    dataset_path.mkdir()
    result = TenXAdapter.validate_input(dataset_path)
    assert result.valid is False
    assert result.errors
