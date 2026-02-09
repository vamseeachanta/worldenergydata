"""Nabors Industries fleet collection config."""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="nabors",
    fleet_url="https://www.nabors.com/rigs",
    vessel_category="drilling_rig",
    vessel_type="land_rig",
    owner="Nabors Industries",
    table_selector="table.fleet-table",
    field_mapping={
        "Rig Name": "VESSEL_NAME",
        "Name": "VESSEL_NAME",
        "Model": "RIG_DESIGN",
        "Type": "RIG_TYPE",
        "Horsepower": "DRAWWORKS_HP",
    },
    rate_limit=0.5,
)

KNOWN_VESSELS = [
    {
        "VESSEL_NAME": "PACE-X1500",
        "RIG_TYPE": "land_rig",
        "RIG_DESIGN": "PACE-X",
        "DRAWWORKS_HP": 1500.0,
    },
    {
        "VESSEL_NAME": "MODS 400",
        "RIG_TYPE": "platform_rig",
        "RIG_DESIGN": "MODS",
    },
]
