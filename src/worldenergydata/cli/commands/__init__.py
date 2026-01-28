"""
CLI Command Modules

Each module provides subcommands for a specific domain:
- bsee: BSEE data operations and analysis
- marine_safety: Marine safety incident data
- fdas: Field development analysis system
- sodir: SODIR (Norwegian Offshore Directorate) data operations
- metocean: Metocean data (buoys, tides, marine weather)
- texas_rrc: Texas Railroad Commission data operations
- canada: Canadian oil & gas data (AER/BCER)
- mexico_cnh: Mexico CNH oil & gas data (SIH dashboard)
- landman: Mineral ownership and lease data operations
"""

from worldenergydata.cli.commands import (
    bsee,
    canada,
    fdas,
    landman,
    marine_safety,
    metocean,
    mexico_cnh,
    sodir,
    texas_rrc,
)

__all__ = [
    "bsee",
    "marine_safety",
    "fdas",
    "sodir",
    "metocean",
    "texas_rrc",
    "canada",
    "mexico_cnh",
    "landman",
]
