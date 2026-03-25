"""Valaris fleet collection config."""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="valaris",
    fleet_url="https://www.valaris.com/our-fleet",
    vessel_category="drilling_rig",
    vessel_type="drilling_rig",
    owner="Valaris Limited",
    table_selector="table.fleet-overview",
    field_mapping={
        "Rig Name": "VESSEL_NAME",
        "Name": "VESSEL_NAME",
        "Type": "RIG_TYPE",
        "Water Depth": "WATER_DEPTH_RATING_FT",
        "Year Built": "YEAR_BUILT",
        "Design": "RIG_DESIGN",
    },
    rate_limit=0.5,
)

KNOWN_VESSELS = [
    {
        "VESSEL_NAME": "VALARIS DS-4",
        "RIG_TYPE": "drillship",
        "WATER_DEPTH_RATING_FT": 12000.0,
        "YEAR_BUILT": 2010,
        "DP_CLASS": 3,
    },
    {
        "VESSEL_NAME": "VALARIS DS-7",
        "RIG_TYPE": "drillship",
        "WATER_DEPTH_RATING_FT": 12000.0,
        "YEAR_BUILT": 2013,
        "DP_CLASS": 3,
    },
    {
        "VESSEL_NAME": "VALARIS DS-8",
        "RIG_TYPE": "drillship",
        "WATER_DEPTH_RATING_FT": 12000.0,
        "YEAR_BUILT": 2014,
        "DP_CLASS": 3,
    },
    {
        "VESSEL_NAME": "VALARIS DPS-5",
        "RIG_TYPE": "semi_submersible",
        "WATER_DEPTH_RATING_FT": 8000.0,
        "YEAR_BUILT": 2009,
        "DP_CLASS": 3,
    },
    {
        "VESSEL_NAME": "VALARIS 100",
        "RIG_TYPE": "jack_up",
        "WATER_DEPTH_RATING_FT": 300.0,
        "YEAR_BUILT": 1982,
    },
    {
        "VESSEL_NAME": "VALARIS 106",
        "RIG_TYPE": "jack_up",
        "WATER_DEPTH_RATING_FT": 350.0,
        "YEAR_BUILT": 2007,
    },
    {
        "VESSEL_NAME": "VALARIS 120",
        "RIG_TYPE": "jack_up",
        "RIG_DESIGN": "Keppel FELS B Class",
        "WATER_DEPTH_RATING_FT": 400.0,
        "YEAR_BUILT": 2013,
    },
    {
        "VESSEL_NAME": "VALARIS 121",
        "RIG_TYPE": "jack_up",
        "RIG_DESIGN": "Keppel FELS B Class",
        "WATER_DEPTH_RATING_FT": 400.0,
        "YEAR_BUILT": 2014,
    },
]
