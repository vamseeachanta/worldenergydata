"""DOF Group intervention / construction fleet collection config (#593).

DOF maintains per-vessel fleet pages at dof.com/fleet/<vessel> with
type/depth/year. The Skandi units cover deepwater construction, flexlay and
light well intervention / IMR. None are documented as GoM-resident.
"""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="dof",
    fleet_url="https://www.dof.com/fleet",
    vessel_category="intervention_vessel",
    vessel_type="mpsv",
    owner="DOF Group",
    table_selector="table",
    detail_selector="div.vessel-specs",
    vessel_links_selector="a[href*='/fleet/']",
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
        "VESSEL_NAME": "Skandi Africa",
        "VESSEL_SUBTYPE": "construction",
        "WATER_DEPTH_RATING_M": 3000.0,
        "DP_CLASS": 3,
        "YEAR_BUILT": 2015,
        "LOA_M": 160.9,
        "GOM_RESIDENT": False,
    },
    {
        "VESSEL_NAME": "Skandi Acergy",
        "VESSEL_SUBTYPE": "construction",
        "WATER_DEPTH_RATING_M": 3000.0,
        "DP_CLASS": 3,
        "YEAR_BUILT": 2008,
        "LOA_M": 156.9,
        "GOM_RESIDENT": False,
    },
    {
        "VESSEL_NAME": "Skandi Constructor",
        "VESSEL_SUBTYPE": "mpsv",
        "YEAR_BUILT": 2009,
        "LOA_M": 120.2,
        "GOM_RESIDENT": False,
    },
    {
        "VESSEL_NAME": "Skandi Vinland",
        "VESSEL_SUBTYPE": "mpsv",
        "WATER_DEPTH_RATING_M": 4000.0,
        "YEAR_BUILT": 2017,
        "GOM_RESIDENT": False,
    },
]
