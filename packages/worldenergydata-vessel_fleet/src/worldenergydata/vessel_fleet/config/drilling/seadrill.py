"""Seadrill fleet collection config."""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="seadrill",
    fleet_url="https://www.seadrill.com/fleet/",  # validated 2026-02-13 (Puppeteer)
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
        "VESSEL_NAME": "Sevan Louisiana",
        "RIG_TYPE": "semi_submersible",
        "OWNER": "Seadrill Limited",
    },
    {
        "VESSEL_NAME": "Sonangol Libongos",
        "RIG_TYPE": "drillship",
        "OWNER": "Sonadrill Holding Ltd",
    },
    {
        "VESSEL_NAME": "Sonangol Quenguela",
        "RIG_TYPE": "drillship",
        "OWNER": "Sonadrill Holding Ltd",
    },
    {
        "VESSEL_NAME": "West Aquarius",
        "RIG_TYPE": "semi_submersible",
        "OWNER": "Seadrill Limited",
    },
    {
        "VESSEL_NAME": "West Auriga",
        "RIG_TYPE": "drillship",
        "OWNER": "Seadrill Limited",
    },
    {
        "VESSEL_NAME": "West Capella",
        "RIG_TYPE": "drillship",
        "OWNER": "Seadrill Limited",
    },
    {
        "VESSEL_NAME": "West Carina",
        "RIG_TYPE": "drillship",
        "OWNER": "Seadrill Limited",
    },
    {
        "VESSEL_NAME": "West Eclipse",
        "RIG_TYPE": "semi_submersible",
        "OWNER": "Seadrill Limited",
    },
    {
        "VESSEL_NAME": "West Elara",
        "RIG_TYPE": "jack_up",
        "OWNER": "Seadrill Limited",
    },
    {
        "VESSEL_NAME": "West Gemini",
        "RIG_TYPE": "drillship",
        "OWNER": "Seadrill Limited",
    },
    {
        "VESSEL_NAME": "West Jupiter",
        "RIG_TYPE": "drillship",
        "OWNER": "Seadrill Limited",
    },
    {
        "VESSEL_NAME": "West Neptune",
        "RIG_TYPE": "drillship",
        "OWNER": "Seadrill Limited",
    },
    {
        "VESSEL_NAME": "West Phoenix",
        "RIG_TYPE": "semi_submersible",
        "OWNER": "Seadrill Limited",
    },
    {
        "VESSEL_NAME": "West Polaris",
        "RIG_TYPE": "drillship",
        "OWNER": "Seadrill Limited",
    },
    {
        "VESSEL_NAME": "West Saturn",
        "RIG_TYPE": "drillship",
        "OWNER": "Seadrill Limited",
    },
    {
        "VESSEL_NAME": "West Tellus",
        "RIG_TYPE": "drillship",
        "OWNER": "Seadrill Limited",
    },
    {
        "VESSEL_NAME": "West Vela",
        "RIG_TYPE": "drillship",
        "OWNER": "Seadrill Limited",
    },
]
