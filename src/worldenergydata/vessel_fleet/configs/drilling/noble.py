"""Noble Corporation fleet collection config."""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="noble",
    fleet_url="https://www.noblecorp.com/our-fleet",
    vessel_category="drilling_rig",
    vessel_type="drilling_rig",
    owner="Noble Corporation plc",
    table_selector="table.fleet-table",
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
        "VESSEL_NAME": "Noble Globetrotter I",
        "RIG_TYPE": "drillship",
        "WATER_DEPTH_RATING_FT": 12000.0,
        "YEAR_BUILT": 2013,
        "DP_CLASS": 3,
    },
    {
        "VESSEL_NAME": "Noble Globetrotter II",
        "RIG_TYPE": "drillship",
        "WATER_DEPTH_RATING_FT": 12000.0,
        "YEAR_BUILT": 2014,
        "DP_CLASS": 3,
    },
    {
        "VESSEL_NAME": "Noble Faye Kozack",
        "RIG_TYPE": "semi_submersible",
        "WATER_DEPTH_RATING_FT": 5000.0,
        "YEAR_BUILT": 2002,
        "DP_CLASS": 3,
    },
    {
        "VESSEL_NAME": "Noble Lloyd Noble",
        "RIG_TYPE": "jack_up",
        "RIG_DESIGN": "Gusto MSC CJ70",
        "WATER_DEPTH_RATING_FT": 492.0,
        "YEAR_BUILT": 2016,
    },
    {
        "VESSEL_NAME": "Noble Innovator",
        "RIG_TYPE": "jack_up",
        "WATER_DEPTH_RATING_FT": 350.0,
        "YEAR_BUILT": 2012,
    },
    {
        "VESSEL_NAME": "Noble Intrepid",
        "RIG_TYPE": "jack_up",
        "WATER_DEPTH_RATING_FT": 400.0,
        "YEAR_BUILT": 2013,
    },
]
