"""WorldEnergyData CLI package."""

from importlib import import_module


def __getattr__(name: str):
    """Load the Typer app only when requested."""
    if name != "app":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = import_module("worldenergydata.cli.main").app
    globals()[name] = value
    return value


__all__ = ["app"]
