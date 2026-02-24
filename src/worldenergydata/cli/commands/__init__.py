"""
CLI Command Modules

Each module provides subcommands for a specific domain:
- bsee: BSEE data operations and analysis
- dashboard: Plotly Dash web dashboard for BSEE/FDAS data
- eia: EIA API v2 weekly petroleum and gas feed ingestion
- marine_safety: Marine safety incident data
- fdas: Field development analysis system
- sodir: SODIR (Norwegian Offshore Directorate) data operations
- metocean: Metocean data (buoys, tides, marine weather)
- texas_rrc: Texas Railroad Commission data operations
- canada: Canadian oil & gas data (AER/BCER)
- mexico_cnh: Mexico CNH oil & gas data (SIH dashboard)
- landman: Mineral ownership and lease data operations
- lng_terminals: Global LNG terminal dataset with engineering design data
"""

from worldenergydata.cli.commands import (
    bsee,
    canada,
    dashboard,
    eia,
    fdas,
    landman,
    lng_terminals,
    marine_safety,
    metocean,
    mexico_cnh,
    sodir,
    texas_rrc,
)

__all__ = [
    "bsee",
    "dashboard",
    "eia",
    "marine_safety",
    "fdas",
    "sodir",
    "metocean",
    "texas_rrc",
    "canada",
    "mexico_cnh",
    "landman",
    "lng_terminals",
]
