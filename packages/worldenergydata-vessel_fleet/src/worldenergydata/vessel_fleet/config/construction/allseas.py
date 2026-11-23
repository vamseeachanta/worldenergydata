"""Allseas fleet collection config."""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="allseas",
    fleet_url="https://allseas.com/equipment/",
    vessel_category="construction_vessel",
    vessel_type="pipelay_vessel",
    owner="Allseas Group S.A.",
    table_selector="table.equipment-table",
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
        "VESSEL_NAME": "Pioneering Spirit",
        "VESSEL_SUBTYPE": "heavy_lift",
        "HEAVY_LIFT_CAPACITY_T": 48000.0,
        "PIPELAY_TENSION_T": 2000.0,
        "YEAR_BUILT": 2014,
        "LOA_M": 382.0,
        "BEAM_M": 124.0,
        "DP_CLASS": 2,
        "QUARTERS_CAPACITY": 571,
    },
    {
        "VESSEL_NAME": "Solitaire",
        "VESSEL_SUBTYPE": "pipelay_vessel",
        "PIPELAY_TENSION_T": 1000.0,
        "PIPELAY_METHOD": "s_lay",
        "YEAR_BUILT": 1972,
        "LOA_M": 300.0,
        "BEAM_M": 40.6,
        "DP_CLASS": 3,
    },
    {
        "VESSEL_NAME": "Audacia",
        "VESSEL_SUBTYPE": "pipelay_vessel",
        "PIPELAY_TENSION_T": 350.0,
        "PIPELAY_METHOD": "s_lay",
        "YEAR_BUILT": 2007,
        "LOA_M": 225.0,
        "BEAM_M": 36.0,
    },
    {
        "VESSEL_NAME": "Lorelay",
        "VESSEL_SUBTYPE": "pipelay_vessel",
        "PIPELAY_METHOD": "reel_lay",
        "YEAR_BUILT": 2009,
        "LOA_M": 163.0,
        "BEAM_M": 36.0,
    },
]
