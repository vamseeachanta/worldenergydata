"""ADES Holding fleet collection config."""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="ades",
    fleet_url="https://www.adesholding.com/fleet",
    vessel_category="drilling_rig",
    vessel_type="drilling_rig",
    owner="ADES Holding",
    table_selector="table.fleet-table",
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
        "VESSEL_NAME": "Admarine 5",
        "RIG_TYPE": "jack_up",
        "WATER_DEPTH_RATING_FT": 300.0,
        "YEAR_BUILT": 2008,
    },
    {
        "VESSEL_NAME": "Admarine 11",
        "RIG_TYPE": "jack_up",
        "WATER_DEPTH_RATING_FT": 350.0,
        "YEAR_BUILT": 2014,
    },
]
