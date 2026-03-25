"""COSL (China Oilfield Services) fleet collection config."""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="cosl",
    fleet_url="https://www.cosl.com.cn/en/fleet",
    vessel_category="drilling_rig",
    vessel_type="drilling_rig",
    owner="COSL (China Oilfield Services)",
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
        "VESSEL_NAME": "HYSY 981",
        "RIG_TYPE": "semi_submersible",
        "WATER_DEPTH_RATING_FT": 10000.0,
        "YEAR_BUILT": 2012,
        "DP_CLASS": 3,
    },
    {
        "VESSEL_NAME": "HYSY 982",
        "RIG_TYPE": "semi_submersible",
        "WATER_DEPTH_RATING_FT": 5000.0,
        "YEAR_BUILT": 2015,
    },
]
