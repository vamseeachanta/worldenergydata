"""Global vessel fleet data collection and enrichment."""

from worldenergydata.vessel_fleet.loaders import ConstructionVesselLoader
from worldenergydata.vessel_fleet.models.construction_vessel import (
    ConstructionVesselEntry,
)
from worldenergydata.vessel_fleet.schemas.construction_vessel import (
    ConstructionVesselSchema,
)

__version__ = "0.1.0"

__all__ = [
    "ConstructionVesselLoader",
    "ConstructionVesselEntry",
    "ConstructionVesselSchema",
]
