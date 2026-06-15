"""Registry of dataset format adapters."""

from __future__ import annotations

from tcr_bcr_tools.adapters.base import AdapterNotFoundError, BaseAdapter

_REGISTRY: dict[str, type[BaseAdapter]] = {}


def register_adapter(adapter: type[BaseAdapter]) -> None:
    """Register an adapter class by its ``name``."""
    _REGISTRY[adapter.name] = adapter


def get_adapter(name: str) -> type[BaseAdapter]:
    """Return a registered adapter class by name."""
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise AdapterNotFoundError(f"Unknown adapter: {name}") from exc


def list_adapters() -> list[str]:
    """Return registered adapter names in sorted order."""
    return sorted(_REGISTRY.keys())


def _register_builtin_adapters() -> None:
    from tcr_bcr_tools.adapters.airr.adapter import AIRRAdapter
    from tcr_bcr_tools.adapters.bdrhapsody.adapter import BDRhapsodyAdapter
    from tcr_bcr_tools.adapters.custom.adapter import CustomAdapter
    from tcr_bcr_tools.adapters.tenx.adapter import TenXAdapter

    for adapter_cls in (TenXAdapter, BDRhapsodyAdapter, AIRRAdapter, CustomAdapter):
        register_adapter(adapter_cls)


_register_builtin_adapters()
