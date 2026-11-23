"""Transocean fleet collection config."""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="transocean",
    fleet_url="https://www.deepwater.com/fleet",
    vessel_category="drilling_rig",
    vessel_type="drilling_rig",
    owner="Transocean Ltd.",
    table_selector="table.fleet-table",
    field_mapping={
        "Rig Name": "VESSEL_NAME",
        "Name": "VESSEL_NAME",
        "Rig": "VESSEL_NAME",
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
        "VESSEL_NAME": "Deepwater Titan",
        "RIG_TYPE": "drillship",
        "RIG_DESIGN": "Samsung 12000",
        "WATER_DEPTH_RATING_FT": 12000.0,
        "DRILLING_DEPTH_RATING_FT": 40000.0,
        "YEAR_BUILT": 2014,
        "DP_CLASS": 3,
        "LOA_M": 228.0,
        "BEAM_M": 42.0,
    },
    {
        "VESSEL_NAME": "Deepwater Atlas",
        "RIG_TYPE": "drillship",
        "RIG_DESIGN": "Jurong Espadon",
        "WATER_DEPTH_RATING_FT": 12000.0,
        "YEAR_BUILT": 2022,
        "DP_CLASS": 3,
        "BOP_PRESSURE_PSI": 20000.0,
    },
    {
        "VESSEL_NAME": "Deepwater Mykonos",
        "RIG_TYPE": "drillship",
        "WATER_DEPTH_RATING_FT": 12000.0,
        "YEAR_BUILT": 2011,
        "DP_CLASS": 3,
    },
    {
        "VESSEL_NAME": "Deepwater Poseidon",
        "RIG_TYPE": "drillship",
        "WATER_DEPTH_RATING_FT": 12000.0,
        "YEAR_BUILT": 2014,
        "DP_CLASS": 3,
    },
    {
        "VESSEL_NAME": "Deepwater Proteus",
        "RIG_TYPE": "drillship",
        "WATER_DEPTH_RATING_FT": 12000.0,
        "YEAR_BUILT": 2014,
        "DP_CLASS": 3,
    },
    {
        "VESSEL_NAME": "Deepwater Thalassa",
        "RIG_TYPE": "drillship",
        "WATER_DEPTH_RATING_FT": 12000.0,
        "YEAR_BUILT": 2015,
        "DP_CLASS": 3,
    },
    {
        "VESSEL_NAME": "Deepwater Asgard",
        "RIG_TYPE": "semi_submersible",
        "WATER_DEPTH_RATING_FT": 10000.0,
        "YEAR_BUILT": 2012,
        "DP_CLASS": 3,
    },
    {
        "VESSEL_NAME": "Development Driller III",
        "RIG_TYPE": "semi_submersible",
        "WATER_DEPTH_RATING_FT": 8000.0,
        "YEAR_BUILT": 2009,
        "DP_CLASS": 3,
    },
    {
        "VESSEL_NAME": "Transocean Barents",
        "RIG_TYPE": "semi_submersible",
        "WATER_DEPTH_RATING_FT": 10000.0,
        "YEAR_BUILT": 2009,
        "DP_CLASS": 3,
    },
    {
        "VESSEL_NAME": "Paul B. Loyd, Jr.",
        "RIG_TYPE": "semi_submersible",
        "WATER_DEPTH_RATING_FT": 1600.0,
        "YEAR_BUILT": 1983,
    },
]
