"""DEME Group fleet collection config."""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="deme",
    fleet_url="https://www.deme-group.com/fleet",
    vessel_category="construction_vessel",
    vessel_type="wind_installation",
    owner="DEME Group",
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
        "VESSEL_NAME": "Orion",
        "VESSEL_SUBTYPE": "wind_installation",
        "MAIN_CRANE_CAPACITY_T": 3000.0,
        "YEAR_BUILT": 2019,
        "LOA_M": 216.5,
        "BEAM_M": 49.0,
    },
]
