"""Field-development metrics tools for Texas RRC curated data."""

from importlib import import_module

_LAZY_EXPORTS = {
    "FieldDevelopmentOutputManifest": ".io",
    "load_field_development_metrics": ".io",
    "write_field_development_outputs": ".io",
    "build_field_development_metrics": ".metrics",
    "FieldDevelopmentQualityReport": ".quality",
    "assess_field_development_quality": ".quality",
    "FieldDevelopmentInputs": ".sources",
    "load_field_development_inputs": ".sources",
}


def __getattr__(name: str):
    """Load field-development exports only when requested."""
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(_LAZY_EXPORTS[name], __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value


__all__ = [
    "FieldDevelopmentInputs",
    "FieldDevelopmentOutputManifest",
    "FieldDevelopmentQualityReport",
    "assess_field_development_quality",
    "build_field_development_metrics",
    "load_field_development_metrics",
    "load_field_development_inputs",
    "write_field_development_outputs",
]
