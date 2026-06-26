"""AKOFS Offshore intervention fleet collection config (#593).

AKOFS Offshore's site names its three subsea well-intervention units; the
detailed specs (depth rating, DP3, year, IMO) come from the DNV vessel
register and Petrobras/Equinor contract news. None are GoM-resident.
"""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="akofs",
    fleet_url="https://www.akofsoffshore.com/",
    vessel_category="intervention_vessel",
    vessel_type="mpsv",
    owner="AKOFS Offshore",
    table_selector="table",
    detail_selector="div.vessel",
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
        "VESSEL_NAME": "AKOFS Seafarer",
        "VESSEL_SUBTYPE": "mpsv",
        "WATER_DEPTH_RATING_M": 2500.0,
        "DP_CLASS": 3,
        "YEAR_BUILT": 2010,
        "LOA_M": 157.0,
        "GOM_RESIDENT": False,
    },
    {
        "VESSEL_NAME": "AKOFS Santos",
        "VESSEL_SUBTYPE": "mpsv",
        "WATER_DEPTH_RATING_M": 3000.0,
        "DP_CLASS": 3,
        "YEAR_BUILT": 2009,
        "LOA_M": 121.0,
        "GOM_RESIDENT": False,
    },
    {
        "VESSEL_NAME": "Aker Wayfarer",
        "VESSEL_SUBTYPE": "construction",
        "WATER_DEPTH_RATING_M": 3000.0,
        "LOA_M": 157.0,
        "GOM_RESIDENT": False,
    },
]
