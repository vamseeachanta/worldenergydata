"""Vantage Drilling International fleet collection config."""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="vantage",
    fleet_url="https://www.vantagedrilling.com/fleet",
    vessel_category="drilling_rig",
    vessel_type="drilling_rig",
    owner="Vantage Drilling International",
    table_selector="table.fleet-table",
    field_mapping={
        "Rig Name": "VESSEL_NAME",
        "Name": "VESSEL_NAME",
        "Type": "RIG_TYPE",
        "Water Depth": "WATER_DEPTH_RATING_FT",
        "Year Built": "YEAR_BUILT",
        "DP Class": "DP_CLASS",
    },
    rate_limit=0.5,
)

KNOWN_VESSELS = [
    {
        "VESSEL_NAME": "Tungsten Explorer",
        "RIG_TYPE": "drillship",
        "WATER_DEPTH_RATING_FT": 12000.0,
        "YEAR_BUILT": 2013,
        "DP_CLASS": 3,
    },
    {
        "VESSEL_NAME": "Platinum Explorer",
        "RIG_TYPE": "drillship",
        "WATER_DEPTH_RATING_FT": 12000.0,
        "YEAR_BUILT": 2010,
        "DP_CLASS": 3,
    },
]
