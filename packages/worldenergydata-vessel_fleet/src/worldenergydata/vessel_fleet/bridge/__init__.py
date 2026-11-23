"""Bridge modules for converting vessel_fleet data to legacy formats."""

from worldenergydata.vessel_fleet.bridge.rig_fleet_bridge import (
    LEGACY_COLUMNS,
    convert_curated_to_rig_fleet,
)

__all__ = ["LEGACY_COLUMNS", "convert_curated_to_rig_fleet"]
