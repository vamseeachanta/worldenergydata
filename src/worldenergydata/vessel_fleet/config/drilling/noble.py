"""Noble Corporation fleet collection config."""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="noble",
    fleet_url="https://www.noblecorp.com/our-fleet",  # validated 2026-02-13 (Puppeteer)
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
        "VESSEL_NAME": "Ocean Apex",
        "RIG_TYPE": "semi_submersible",
        "RIG_DESIGN": "Enhanced Victory Class",
        "WATER_DEPTH_RATING_FT": 6000.0,
    },
    {
        "VESSEL_NAME": "Noble BlackHawk",
        "RIG_TYPE": "drillship",
        "RIG_DESIGN": "Gusto P10000",
        "WATER_DEPTH_RATING_FT": 12000.0,
    },
    {
        "VESSEL_NAME": "Noble BlackHornet",
        "RIG_TYPE": "drillship",
        "RIG_DESIGN": "Gusto P10000",
        "WATER_DEPTH_RATING_FT": 12000.0,
    },
    {
        "VESSEL_NAME": "Noble BlackLion",
        "RIG_TYPE": "drillship",
        "RIG_DESIGN": "Gusto P10000",
        "WATER_DEPTH_RATING_FT": 12000.0,
    },
    {
        "VESSEL_NAME": "Noble BlackRhino",
        "RIG_TYPE": "drillship",
        "RIG_DESIGN": "Gusto P10000",
        "WATER_DEPTH_RATING_FT": 12000.0,
    },
    {
        "VESSEL_NAME": "Noble Bob Douglas",
        "RIG_TYPE": "drillship",
        "RIG_DESIGN": "Gusto P10000",
        "WATER_DEPTH_RATING_FT": 12000.0,
    },
    {
        "VESSEL_NAME": "Noble Courage",
        "RIG_TYPE": "semi_submersible",
        "RIG_DESIGN": "F&G ExD Millennium",
        "WATER_DEPTH_RATING_FT": 10000.0,
    },
    {
        "VESSEL_NAME": "Noble Deliverer",
        "RIG_TYPE": "semi_submersible",
        "RIG_DESIGN": "DSS21-DPS2",
        "WATER_DEPTH_RATING_FT": 10000.0,
    },
    {
        "VESSEL_NAME": "Noble Developer",
        "RIG_TYPE": "semi_submersible",
        "RIG_DESIGN": "DSS21-DPS2",
        "WATER_DEPTH_RATING_FT": 10000.0,
    },
    {
        "VESSEL_NAME": "Noble Discoverer",
        "RIG_TYPE": "semi_submersible",
        "RIG_DESIGN": "DSS21-DPS2",
        "WATER_DEPTH_RATING_FT": 10000.0,
    },
    {
        "VESSEL_NAME": "Noble Don Taylor",
        "RIG_TYPE": "drillship",
        "RIG_DESIGN": "Gusto P10000",
        "WATER_DEPTH_RATING_FT": 12000.0,
    },
    {
        "VESSEL_NAME": "Noble Endeavor",
        "RIG_TYPE": "semi_submersible",
        "RIG_DESIGN": "Odeco Victory",
        "WATER_DEPTH_RATING_FT": 8000.0,
    },
    {
        "VESSEL_NAME": "Noble Faye Kozack",
        "RIG_TYPE": "drillship",
        "RIG_DESIGN": "Samsung 96K",
        "WATER_DEPTH_RATING_FT": 12000.0,
    },
    {
        "VESSEL_NAME": "Noble Gerry de Souza",
        "RIG_TYPE": "drillship",
        "RIG_DESIGN": "Samsung 12000 Double Hull",
        "WATER_DEPTH_RATING_FT": 12000.0,
    },
    {
        "VESSEL_NAME": "Noble Globetrotter I",
        "RIG_TYPE": "semi_submersible",
        "RIG_DESIGN": "Globetrotter Class",
        "WATER_DEPTH_RATING_FT": 10000.0,
    },
    {
        "VESSEL_NAME": "Noble Globetrotter II",
        "RIG_TYPE": "semi_submersible",
        "RIG_DESIGN": "Globetrotter Class",
        "WATER_DEPTH_RATING_FT": 10000.0,
    },
    {
        "VESSEL_NAME": "Noble GreatWhite",
        "RIG_TYPE": "semi_submersible",
        "RIG_DESIGN": "Moss CS60E",
        "WATER_DEPTH_RATING_FT": 10000.0,
    },
    {
        "VESSEL_NAME": "Noble Innovator",
        "RIG_TYPE": "jack_up",
        "RIG_DESIGN": "Gusto MSC CJ 70 - 150 MC",
        "WATER_DEPTH_RATING_FT": 492.0,
    },
    {
        "VESSEL_NAME": "Noble Integrator",
        "RIG_TYPE": "jack_up",
        "RIG_DESIGN": "Gusto MSC CJ70 X150 MD",
        "WATER_DEPTH_RATING_FT": 492.0,
    },
    {
        "VESSEL_NAME": "Noble Interceptor",
        "RIG_TYPE": "jack_up",
        "RIG_DESIGN": "Gusto MSC CJ70 X150 MD",
        "WATER_DEPTH_RATING_FT": 492.0,
    },
    {
        "VESSEL_NAME": "Noble Intrepid",
        "RIG_TYPE": "jack_up",
        "RIG_DESIGN": "Gusto MSC CJ70 X150 MD",
        "WATER_DEPTH_RATING_FT": 492.0,
    },
    {
        "VESSEL_NAME": "Noble Invincible",
        "RIG_TYPE": "jack_up",
        "RIG_DESIGN": "Gusto MSC CJ70 X150 MD",
        "WATER_DEPTH_RATING_FT": 492.0,
    },
    {
        "VESSEL_NAME": "Noble Patriot",
        "RIG_TYPE": "semi_submersible",
        "RIG_DESIGN": "Trosvik Bingo 3000",
        "WATER_DEPTH_RATING_FT": 1500.0,
    },
    {
        "VESSEL_NAME": "Noble Resolve",
        "RIG_TYPE": "jack_up",
        "RIG_DESIGN": "Gusto MSC CJ50 X100 MC",
        "WATER_DEPTH_RATING_FT": 350.0,
    },
    {
        "VESSEL_NAME": "Noble Sam Croft",
        "RIG_TYPE": "drillship",
        "RIG_DESIGN": "Gusto P10000",
        "WATER_DEPTH_RATING_FT": 12000.0,
    },
    {
        "VESSEL_NAME": "Noble Stanley Lafosse",
        "RIG_TYPE": "drillship",
        "RIG_DESIGN": "Samsung 96K",
        "WATER_DEPTH_RATING_FT": 12000.0,
    },
    {
        "VESSEL_NAME": "Noble Tom Madden",
        "RIG_TYPE": "drillship",
        "RIG_DESIGN": "Gusto P10000",
        "WATER_DEPTH_RATING_FT": 12000.0,
    },
    {
        "VESSEL_NAME": "Noble Valiant",
        "RIG_TYPE": "drillship",
        "RIG_DESIGN": "Samsung 96K",
        "WATER_DEPTH_RATING_FT": 12000.0,
    },
    {
        "VESSEL_NAME": "Noble Venturer",
        "RIG_TYPE": "drillship",
        "RIG_DESIGN": "Samsung 96K",
        "WATER_DEPTH_RATING_FT": 12000.0,
    },
    {
        "VESSEL_NAME": "Noble Viking",
        "RIG_TYPE": "drillship",
        "RIG_DESIGN": "Samsung 96K",
        "WATER_DEPTH_RATING_FT": 12000.0,
    },
    {
        "VESSEL_NAME": "Noble Voyager",
        "RIG_TYPE": "drillship",
        "RIG_DESIGN": "Samsung 96K",
        "WATER_DEPTH_RATING_FT": 12000.0,
    },
]
