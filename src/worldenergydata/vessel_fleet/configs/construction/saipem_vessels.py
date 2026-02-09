"""Saipem fleet collection config (construction vessels, not drilling)."""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="saipem_vessels",
    fleet_url="https://www.saipem.com/en/fleet-and-yards",
    vessel_category="construction_vessel",
    vessel_type="pipelay_vessel",
    owner="Saipem S.p.A.",
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
        "VESSEL_NAME": "Castorone",
        "VESSEL_SUBTYPE": "pipelay_vessel",
        "PIPELAY_TENSION_T": 750.0,
        "PIPELAY_METHOD": "j_lay",
        "PIPELAY_CAPACITY_IN": 48.0,
        "YEAR_BUILT": 2012,
        "LOA_M": 330.0,
        "BEAM_M": 39.0,
        "DP_CLASS": 3,
        "QUARTERS_CAPACITY": 700,
    },
    {
        "VESSEL_NAME": "Saipem 7000",
        "VESSEL_SUBTYPE": "crane_vessel",
        "MAIN_CRANE_CAPACITY_T": 7000.0,
        "PIPELAY_TENSION_T": 525.0,
        "YEAR_BUILT": 1987,
        "LOA_M": 197.95,
        "BEAM_M": 87.0,
        "DP_CLASS": 3,
        "QUARTERS_CAPACITY": 725,
    },
    {
        "VESSEL_NAME": "FDS 2",
        "VESSEL_SUBTYPE": "pipelay_vessel",
        "PIPELAY_METHOD": "j_lay",
        "YEAR_BUILT": 2011,
        "LOA_M": 199.9,
        "BEAM_M": 38.0,
        "DP_CLASS": 3,
    },
]
