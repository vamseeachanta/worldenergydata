"""Oceaneering International intervention/MSV fleet collection config (#593).

Oceaneering's vessel-fleet page renders a list of named multi-service
vessels (MSVs) with length/flag and partial DP class. Several specs
(year_built, water-depth rating) are not exposed and are left null.
"""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="oceaneering",
    fleet_url="https://www.oceaneering.com/subsea-projects/vessel-fleet/",
    vessel_category="intervention_vessel",
    vessel_type="mpsv",
    owner="Oceaneering International",
    table_selector="table",
    detail_selector="div.vessel-card",
    field_mapping={
        "Name": "VESSEL_NAME",
        "Vessel": "VESSEL_NAME",
        "Type": "VESSEL_SUBTYPE",
        "Length": "LOA_FT",
        "DP": "DP_CLASS",
        "Flag": "FLAG",
        "Water Depth": "WATER_DEPTH_RATING_M",
    },
    rate_limit=1.0,
)

KNOWN_VESSELS = [
    {
        "VESSEL_NAME": "Ocean Evolution",
        "VESSEL_SUBTYPE": "mpsv",
        "WATER_DEPTH_RATING_M": 4000.0,
        "DP_CLASS": 2,
        "YEAR_BUILT": 2019,
        "LOA_FT": 353.0,
        "FLAG": "US",
        "GOM_RESIDENT": True,
    },
    {
        "VESSEL_NAME": "Blue Sea",
        "VESSEL_SUBTYPE": "mpsv",
        "LOA_FT": 340.0,
        "FLAG": "US",
        "GOM_RESIDENT": True,
    },
    {
        "VESSEL_NAME": "Normand Superior",
        "VESSEL_SUBTYPE": "mpsv",
        "DP_CLASS": 2,
        "LOA_FT": 322.0,
        "FLAG": "Norway",
        "GOM_RESIDENT": False,
    },
    {
        "VESSEL_NAME": "Juanita Candies",
        "VESSEL_SUBTYPE": "mpsv",
        "DP_CLASS": 2,
        "LOA_FT": 302.0,
        "FLAG": "US",
        "GOM_RESIDENT": True,
    },
    {
        "VESSEL_NAME": "Intervention",
        "VESSEL_SUBTYPE": "mpsv",
        "LOA_FT": 300.0,
        "FLAG": "US",
        "GOM_RESIDENT": True,
    },
    {
        "VESSEL_NAME": "Brandon Bordelon",
        "VESSEL_SUBTYPE": "mpsv",
        "LOA_FT": 257.0,
        "FLAG": "US",
        "GOM_RESIDENT": True,
    },
    {
        "VESSEL_NAME": "Ocean Intervention II",
        "VESSEL_SUBTYPE": "mpsv",
        "DP_CLASS": 2,
        "LOA_FT": 254.0,
        "GOM_RESIDENT": True,
    },
    {
        "VESSEL_NAME": "Ocean Intervention",
        "VESSEL_SUBTYPE": "mpsv",
        "DP_CLASS": 2,
        "LOA_FT": 243.0,
        "FLAG": "US",
        "GOM_RESIDENT": True,
    },
]
