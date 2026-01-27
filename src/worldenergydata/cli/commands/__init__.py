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
"""

from worldenergydata.cli.commands import (
    bsee,
    canada,
    fdas,
    marine_safety,
    metocean,
    sodir,
    texas_rrc,
)

__all__ = ["bsee", "marine_safety", "fdas", "sodir", "metocean", "texas_rrc", "canada"]
