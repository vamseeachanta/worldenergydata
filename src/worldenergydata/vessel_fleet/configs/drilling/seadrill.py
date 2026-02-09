"""Seadrill fleet collection config."""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="seadrill",
    fleet_url="https://www.seadrill.com/fleet",
    vessel_category="drilling_rig",
    vessel_type="drilling_rig",
    owner="Seadrill Limited",
    table_selector="table.fleet-table",
    field_mapping={
        "Rig Name": "VESSEL_NAME",
        "Name": "VESSEL_NAME",
        "Type": "RIG_TYPE",
        "Water Depth": "WATER_DEPTH_RATING_FT",
        "Year Built": "YEAR_BUILT",
        "Design": "RIG_DESIGN",
        "DP Class": "DP_CLASS",
    },
    rate_limit=0.5,
)

KNOWN_VESSELS = [
    {
        "VESSEL_NAME": "West Neptune",
        "RIG_TYPE": "drillship",
        "WATER_DEPTH_RATING_FT": 10000.0,
        "YEAR_BUILT": 2014,
        "DP_CLASS": 3,
    },
    {
        "VESSEL_NAME": "West Saturn",
        "RIG_TYPE": "drillship",
        "WATER_DEPTH_RATING_FT": 10000.0,
        "YEAR_BUILT": 2014,
        "DP_CLASS": 3,
    },
    {
        "VESSEL_NAME": "West Gemini",
        "RIG_TYPE": "semi_submersible",
        "WATER_DEPTH_RATING_FT": 7500.0,
        "YEAR_BUILT": 2010,
    },
]
