"""Subsea 7 fleet collection config."""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="subsea7",
    fleet_url="https://www.subsea7.com/our-fleet",
    vessel_category="construction_vessel",
    vessel_type="surf_vessel",
    owner="Subsea 7 S.A.",
    table_selector="div.fleet-grid table",
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
        "VESSEL_NAME": "Seven Borealis",
        "VESSEL_SUBTYPE": "crane_vessel",
        "MAIN_CRANE_CAPACITY_T": 5000.0,
        "PIPELAY_TENSION_T": 550.0,
        "YEAR_BUILT": 2012,
        "LOA_M": 182.2,
        "BEAM_M": 46.2,
        "DP_CLASS": 3,
    },
    {
        "VESSEL_NAME": "Seven Vega",
        "VESSEL_SUBTYPE": "pipelay_vessel",
        "PIPELAY_METHOD": "reel_lay",
        "YEAR_BUILT": 2020,
        "LOA_M": 149.9,
        "BEAM_M": 30.0,
        "DP_CLASS": 3,
    },
    {
        "VESSEL_NAME": "Seven Arctic",
        "VESSEL_SUBTYPE": "pipelay_vessel",
        "PIPELAY_METHOD": "reel_lay",
        "YEAR_BUILT": 2017,
        "LOA_M": 149.9,
        "BEAM_M": 30.0,
        "DP_CLASS": 3,
    },
]
