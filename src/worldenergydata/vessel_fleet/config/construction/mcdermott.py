"""McDermott International fleet collection config."""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="mcdermott",
    fleet_url="https://www.mcdermott.com/fleet",
    vessel_category="construction_vessel",
    vessel_type="crane_vessel",
    owner="McDermott International",
    table_selector="div.fleet-list table",
    field_mapping={
        "Name": "VESSEL_NAME",
        "Vessel": "VESSEL_NAME",
        "Type": "VESSEL_SUBTYPE",
        "Crane Capacity": "MAIN_CRANE_CAPACITY_T",
        "Pipelay Tension": "PIPELAY_TENSION_T",
        "Year Built": "YEAR_BUILT",
        "Length": "LOA_M",
        "Beam": "BEAM_M",
    },
    rate_limit=0.5,
)

KNOWN_VESSELS = [
    {
        "VESSEL_NAME": "Amazon",
        "VESSEL_SUBTYPE": "crane_vessel",
        "MAIN_CRANE_CAPACITY_T": 2200.0,
        "YEAR_BUILT": 2005,
        "LOA_M": 174.0,
        "BEAM_M": 52.0,
    },
    {
        "VESSEL_NAME": "DLV 2000",
        "VESSEL_SUBTYPE": "pipelay_vessel",
        "PIPELAY_TENSION_T": 550.0,
        "YEAR_BUILT": 2001,
    },
]
