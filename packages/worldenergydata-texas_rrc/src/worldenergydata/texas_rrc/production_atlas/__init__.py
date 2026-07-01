"""Production atlas tools for Texas RRC PDQ data."""

from importlib import import_module

_LAZY_EXPORTS = {
    "build_production_atlas": ".atlas",
    "build_production_atlas_from_chunks": ".atlas",
    "normalize_production_frame": ".atlas",
    "ProductionAtlasOutputManifest": ".io",
    "load_production_atlas": ".io",
    "write_production_atlas_outputs": ".io",
    "ProductionInputFrame": ".sources",
    "load_production_inputs": ".sources",
}


def __getattr__(name: str):
    """Load production-atlas exports only when requested."""
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(_LAZY_EXPORTS[name], __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value

__all__ = [
    "ProductionAtlasOutputManifest",
    "ProductionInputFrame",
    "build_production_atlas",
    "build_production_atlas_from_chunks",
    "load_production_atlas",
    "load_production_inputs",
    "normalize_production_frame",
    "write_production_atlas_outputs",
]
