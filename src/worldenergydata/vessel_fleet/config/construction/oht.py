"""OHT ASA fleet collection config."""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="oht",
    fleet_url="https://www.ofrshore-heavy-transport.com/fleet",
    vessel_category="construction_vessel",
    vessel_type="heavy_transport",
    owner="OHT ASA",
    table_selector="div.fleet-list table",
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
        "VESSEL_NAME": "Alfa Lift",
        "VESSEL_SUBTYPE": "heavy_transport",
        "MAIN_CRANE_CAPACITY_T": 3000.0,
        "YEAR_BUILT": 2021,
        "LOA_M": 216.3,
        "BEAM_M": 56.7,
    },
]
