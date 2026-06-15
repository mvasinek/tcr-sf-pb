"""Tests for adapter registry."""

import pytest

from tcr_bcr_tools.adapters.base import AdapterNotFoundError
from tcr_bcr_tools.adapters.registry import get_adapter, list_adapters, register_adapter
from tcr_bcr_tools.adapters.tenx.adapter import TenXAdapter


def test_list_adapters_includes_builtin() -> None:
    names = list_adapters()
    assert names == ["airr", "bdrhapsody", "custom", "tenx"]


def test_get_adapter_by_name() -> None:
    adapter = get_adapter("tenx")
    assert adapter is TenXAdapter


def test_unknown_adapter_raises() -> None:
    with pytest.raises(AdapterNotFoundError):
        get_adapter("missing")


def test_register_adapter() -> None:
    class DemoAdapter(TenXAdapter):
        name = "demo_test_adapter"

    register_adapter(DemoAdapter)
    assert get_adapter("demo_test_adapter") is DemoAdapter
