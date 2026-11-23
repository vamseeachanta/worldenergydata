"""Island Offshore / TIOS intervention fleet collection config (#593).

Island Offshore's own fleet page (islandoffshore.com/fleet) is JS-driven and
exposes only one vessel name to a static fetch; TIOS (Island Offshore +
TechnipFMC JV, tiosgroup.com) lists RLWI monohulls but hides per-vessel specs
behind JS. ``KNOWN_VESSELS`` seeds the named units from public references
(Ulstein shipyard pages, ship-technology) since the operator pages are thin.
"""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="island_offshore",
    fleet_url="https://www.islandoffshore.com/fleet",
    vessel_category="intervention_vessel",
    vessel_type="rlwi_monohull",
    owner="Island Offshore / TIOS",
    table_selector="table",
    detail_selector="div.vessel-specs",
    vessel_links_selector="a[href*='/fleet']",
    field_mapping={
        "Name": "VESSEL_NAME",
        "Vessel": "VESSEL_NAME",
        "Type": "VESSEL_SUBTYPE",
        "Water Depth": "WATER_DEPTH_RATING_M",
        "Year Built": "YEAR_BUILT",
        "DP": "DP_CLASS",
        "Length": "LOA_M",
    },
    rate_limit=1.0,
)

KNOWN_VESSELS = [
    {
        "VESSEL_NAME": "Island Constructor",
        "VESSEL_SUBTYPE": "rlwi_monohull",
        "WATER_DEPTH_RATING_M": 600.0,
        "DP_CLASS": 3,
        "GOM_RESIDENT": False,
    },
    {
        "VESSEL_NAME": "Island Wellserver",
        "VESSEL_SUBTYPE": "rlwi_monohull",
        "GOM_RESIDENT": False,
    },
    {
        "VESSEL_NAME": "Island Frontier",
        "VESSEL_SUBTYPE": "rlwi_monohull",
        "GOM_RESIDENT": False,
    },
    {
        "VESSEL_NAME": "Vanguard",
        "VESSEL_SUBTYPE": "osv",
        "GOM_RESIDENT": False,
    },
]
