"""CLI command modules.

Each module provides subcommands for a specific domain:
- bsee: BSEE data operations and analysis
- dashboard: Plotly Dash web dashboard for BSEE/FDAS data
- eia: EIA API v2 weekly petroleum and gas feed ingestion
- marine_safety: Marine safety incident data
- fdas: Field development analysis system
- ndbc: NDBC buoy data — scatter matrices, Weibull fits, wave roses (WRK-316)
- sodir: SODIR (Norwegian Offshore Directorate) data operations
- metocean: Metocean data (buoys, tides, marine weather)
- texas_rrc: Texas Railroad Commission data operations
- kansas_kgs: Kansas Geological Survey data operations
- canada: Canadian oil & gas data (AER/BCER)
- mexico_cnh: Mexico CNH oil & gas data (SIH dashboard)
- landman: Mineral ownership and lease data operations
- lng_terminals: Global LNG terminal dataset with engineering design data
"""

from importlib import import_module

_COMMAND_MODULES = {
    "bsee",
    "canada",
    "dashboard",
    "eia",
    "fdas",
    "kansas_kgs",
    "landman",
    "lng_terminals",
    "marine_safety",
    "metocean",
    "mexico_cnh",
    "ndbc",
    "sodir",
    "texas_rrc",
}


def __getattr__(name: str):
    """Load command modules only when requested."""
    if name not in _COMMAND_MODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(f"{__name__}.{name}")
    globals()[name] = module
    return module


__all__ = [
    "bsee",
    "dashboard",
    "eia",
    "marine_safety",
    "fdas",
    "ndbc",
    "sodir",
    "metocean",
    "kansas_kgs",
    "texas_rrc",
    "canada",
    "mexico_cnh",
    "landman",
    "lng_terminals",
]
