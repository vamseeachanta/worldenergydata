"""Helix Energy Solutions intervention fleet collection config (#593).

Helix publishes per-vessel asset pages under https://helixesg.com/our-assets/.
The correct public domain is ``helixesg.com`` (``helixenergy.com`` does not
resolve). Each asset page is a key-value detail page rather than a single
fleet table, so ``detail_selector`` is provided for future per-asset runs.
"""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="helix",
    fleet_url="https://helixesg.com/our-assets/",
    vessel_category="intervention_vessel",
    vessel_type="heavy_intervention_semi",
    owner="Helix Energy Solutions",
    table_selector="table",
    detail_selector="div.asset-specs",
    vessel_links_selector="a[href*='/our-assets/']",
    field_mapping={
        "Name": "VESSEL_NAME",
        "Vessel": "VESSEL_NAME",
        "Type": "VESSEL_SUBTYPE",
        "Water Depth": "WATER_DEPTH_RATING_M",
        "Year Built": "YEAR_BUILT",
        "Built": "YEAR_BUILT",
        "DP": "DP_CLASS",
        "Length": "LOA_M",
        "Beam": "BEAM_M",
    },
    rate_limit=0.5,
)

KNOWN_VESSELS = [
    {
        "VESSEL_NAME": "Q4000",
        "VESSEL_SUBTYPE": "heavy_intervention_semi",
        "WATER_DEPTH_RATING_M": 3000.0,
        "DP_CLASS": 3,
        "YEAR_BUILT": 2002,
        "GOM_RESIDENT": True,
    },
    {
        "VESSEL_NAME": "Q5000",
        "VESSEL_SUBTYPE": "heavy_intervention_semi",
        "WATER_DEPTH_RATING_M": 3000.0,
        "DP_CLASS": 3,
        "YEAR_BUILT": 2015,
        "GOM_RESIDENT": True,
    },
    {
        "VESSEL_NAME": "Q7000",
        "VESSEL_SUBTYPE": "heavy_intervention_semi",
        "WATER_DEPTH_RATING_M": 3000.0,
        "DP_CLASS": 3,
        "YEAR_BUILT": 2019,
        "GOM_RESIDENT": False,
    },
    {
        "VESSEL_NAME": "Seawell",
        "VESSEL_SUBTYPE": "rlwi_monohull",
        "WATER_DEPTH_RATING_M": 500.0,
        "DP_CLASS": 2,
        "YEAR_BUILT": 1987,
        "GOM_RESIDENT": False,
    },
    {
        "VESSEL_NAME": "Well Enhancer",
        "VESSEL_SUBTYPE": "rlwi_monohull",
        "WATER_DEPTH_RATING_M": 300.0,
        "YEAR_BUILT": 2009,
        "GOM_RESIDENT": False,
    },
    {
        "VESSEL_NAME": "Siem Helix 1",
        "VESSEL_SUBTYPE": "rlwi_monohull",
        "WATER_DEPTH_RATING_M": 3000.0,
        "DP_CLASS": 3,
        "YEAR_BUILT": 2016,
        "GOM_RESIDENT": False,
    },
    {
        "VESSEL_NAME": "Siem Helix 2",
        "VESSEL_SUBTYPE": "rlwi_monohull",
        "WATER_DEPTH_RATING_M": 3000.0,
        "DP_CLASS": 3,
        "YEAR_BUILT": 2016,
        "GOM_RESIDENT": False,
    },
]
