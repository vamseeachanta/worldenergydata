"""Borr Drilling fleet collection config."""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="borr",
    fleet_url="https://www.bfrdrilling.com/fleet",
    vessel_category="drilling_rig",
    vessel_type="drilling_rig",
    owner="Borr Drilling Limited",
    table_selector="table.fleet-list",
    field_mapping={
        "Rig Name": "VESSEL_NAME",
        "Name": "VESSEL_NAME",
        "Design": "RIG_DESIGN",
        "Water Depth": "WATER_DEPTH_RATING_FT",
        "Year Built": "YEAR_BUILT",
        "Drilling Depth": "DRILLING_DEPTH_RATING_FT",
    },
    rate_limit=0.5,
)

KNOWN_VESSELS = [
    {
        "VESSEL_NAME": "Var",
        "RIG_TYPE": "jack_up",
        "RIG_DESIGN": "Gusto MSC CJ50",
        "WATER_DEPTH_RATING_FT": 400.0,
        "DRILLING_DEPTH_RATING_FT": 30000.0,
        "YEAR_BUILT": 2013,
    },
    {
        "VESSEL_NAME": "Natt",
        "RIG_TYPE": "jack_up",
        "RIG_DESIGN": "Gusto MSC CJ50",
        "WATER_DEPTH_RATING_FT": 400.0,
        "YEAR_BUILT": 2013,
    },
    {
        "VESSEL_NAME": "Gunnlod",
        "RIG_TYPE": "jack_up",
        "RIG_DESIGN": "Gusto MSC CJ46",
        "WATER_DEPTH_RATING_FT": 375.0,
        "YEAR_BUILT": 2019,
    },
    {
        "VESSEL_NAME": "Idun",
        "RIG_TYPE": "jack_up",
        "RIG_DESIGN": "Keppel FELS B Class",
        "WATER_DEPTH_RATING_FT": 400.0,
        "YEAR_BUILT": 2013,
    },
    {
        "VESSEL_NAME": "Ran",
        "RIG_TYPE": "jack_up",
        "RIG_DESIGN": "PPL Pacific Class 400",
        "WATER_DEPTH_RATING_FT": 400.0,
        "YEAR_BUILT": 2014,
    },
]
