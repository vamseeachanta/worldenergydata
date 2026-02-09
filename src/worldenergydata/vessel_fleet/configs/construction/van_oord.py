"""Van Oord fleet collection config."""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="van_oord",
    fleet_url="https://www.vanoord.com/fleet",
    vessel_category="construction_vessel",
    vessel_type="wind_installation",
    owner="Van Oord",
    table_selector="div.fleet-overview table",
    field_mapping={
        "Name": "VESSEL_NAME",
        "Vessel": "VESSEL_NAME",
        "Type": "VESSEL_SUBTYPE",
        "Crane Capacity": "MAIN_CRANE_CAPACITY_T",
        "Year Built": "YEAR_BUILT",
        "Length": "LOA_M",
        "Beam": "BEAM_M",
    },
    rate_limit=0.5,
)

KNOWN_VESSELS = [
    {
        "VESSEL_NAME": "Aeolus",
        "VESSEL_SUBTYPE": "wind_installation",
        "MAIN_CRANE_CAPACITY_T": 1600.0,
        "YEAR_BUILT": 2014,
        "LOA_M": 139.0,
        "BEAM_M": 38.0,
    },
]
