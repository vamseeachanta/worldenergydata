"""Global vessel fleet data collection and enrichment."""

from worldenergydata.vessel_fleet.loaders import (
    ConstructionVesselLoader,
    DrillingRiserLoader,
)
from worldenergydata.vessel_fleet.models.construction_vessel import (
    ConstructionVesselEntry,
)
from worldenergydata.vessel_fleet.models.drilling_riser import (
    BOPEntry,
    FlexJointEntry,
    LMRPEntry,
    RiserJointEntry,
    TelescopicJointEntry,
)
from worldenergydata.vessel_fleet.schemas.construction_vessel import (
    ConstructionVesselSchema,
)
from worldenergydata.vessel_fleet.schemas.drilling_riser import (
    BOPSchema,
    FlexJointSchema,
    LMRPSchema,
    RiserJointSchema,
    TelescopicJointSchema,
)

__version__ = "0.1.0"

__all__ = [
    "BOPEntry",
    "BOPSchema",
    "ConstructionVesselEntry",
    "ConstructionVesselLoader",
    "ConstructionVesselSchema",
    "DrillingRiserLoader",
    "FlexJointEntry",
    "FlexJointSchema",
    "LMRPEntry",
    "LMRPSchema",
    "RiserJointEntry",
    "RiserJointSchema",
    "TelescopicJointEntry",
    "TelescopicJointSchema",
]
