"""C-Innovation / Edison Chouest Offshore intervention fleet config (#593).

C-Innovation (Edison Chouest Offshore subsea arm) operates Jones-Act
RLWI/IMR MPSVs in the US Gulf of Mexico. The brochure PDF at
c-innovation.com returns unparseable binary, so ``KNOWN_VESSELS`` seeds the
named GoM-resident units from Ulstein shipyard reference pages and news.
"""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="c_innovation",
    fleet_url="https://c-innovation.com/vessel-services/",
    vessel_category="intervention_vessel",
    vessel_type="mpsv",
    owner="C-Innovation / Edison Chouest Offshore",
    table_selector="table",
    detail_selector="div.vessel-specs",
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
        "VESSEL_NAME": "Island Venture",
        "VESSEL_SUBTYPE": "mpsv",
        "DP_CLASS": 3,
        "YEAR_BUILT": 2017,
        "LOA_M": 160.0,
        "GOM_RESIDENT": True,
    },
    {
        "VESSEL_NAME": "Island Performer",
        "VESSEL_SUBTYPE": "mpsv",
        "DP_CLASS": 3,
        "YEAR_BUILT": 2014,
        "LOA_M": 130.0,
        "GOM_RESIDENT": True,
    },
    {
        "VESSEL_NAME": "Island Intervention",
        "VESSEL_SUBTYPE": "mpsv",
        "DP_CLASS": 3,
        "LOA_M": 120.2,
        "GOM_RESIDENT": True,
    },
]
