"""Saipem Drilling fleet collection config."""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="saipem_drilling",
    fleet_url="https://www.saipem.com/en/fleet-and-yards",
    vessel_category="drilling_rig",
    vessel_type="drilling_rig",
    owner="Saipem S.p.A.",
    table_selector="div.fleet-list table",
    field_mapping={
        "Rig Name": "VESSEL_NAME",
        "Name": "VESSEL_NAME",
        "Type": "RIG_TYPE",
        "Water Depth": "WATER_DEPTH_RATING_FT",
        "Year Built": "YEAR_BUILT",
    },
    rate_limit=0.5,
)

KNOWN_VESSELS = [
    {
        "VESSEL_NAME": "Saipem 10000",
        "RIG_TYPE": "drillship",
        "WATER_DEPTH_RATING_FT": 10000.0,
        "YEAR_BUILT": 2000,
        "DP_CLASS": 3,
        "LOA_M": 228.0,
        "BEAM_M": 42.0,
    },
    {
        "VESSEL_NAME": "Saipem 12000",
        "RIG_TYPE": "drillship",
        "WATER_DEPTH_RATING_FT": 12000.0,
        "YEAR_BUILT": 2005,
        "DP_CLASS": 3,
    },
    {
        "VESSEL_NAME": "Scarabeo 5",
        "RIG_TYPE": "semi_submersible",
        "WATER_DEPTH_RATING_FT": 5000.0,
        "YEAR_BUILT": 1990,
    },
    {
        "VESSEL_NAME": "Scarabeo 8",
        "RIG_TYPE": "semi_submersible",
        "WATER_DEPTH_RATING_FT": 10000.0,
        "YEAR_BUILT": 2012,
        "DP_CLASS": 3,
    },
    {
        "VESSEL_NAME": "Scarabeo 9",
        "RIG_TYPE": "semi_submersible",
        "WATER_DEPTH_RATING_FT": 10000.0,
        "YEAR_BUILT": 2011,
        "DP_CLASS": 3,
    },
]
