"""Heerema Marine Contractors fleet collection config."""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="heerema",
    fleet_url="https://heerema.com/fleet",
    vessel_category="construction_vessel",
    vessel_type="crane_vessel",
    owner="Heerema Marine Contractors",
    table_selector="table.fleet-table",
    field_mapping={
        "Name": "VESSEL_NAME",
        "Vessel": "VESSEL_NAME",
        "Type": "VESSEL_SUBTYPE",
        "Crane Capacity": "MAIN_CRANE_CAPACITY_T",
        "Year Built": "YEAR_BUILT",
        "DP Class": "DP_CLASS",
        "Length": "LOA_M",
        "Beam": "BEAM_M",
        "Accommodation": "QUARTERS_CAPACITY",
    },
    rate_limit=0.5,
)

# Known vessels for validation and manual fallback
KNOWN_VESSELS = [
    {
        "VESSEL_NAME": "Sleipnir",
        "VESSEL_SUBTYPE": "crane_vessel",
        "MAIN_CRANE_CAPACITY_T": 10000.0,
        "YEAR_BUILT": 2019,
        "LOA_M": 220.0,
        "BEAM_M": 102.0,
        "DP_CLASS": 3,
        "QUARTERS_CAPACITY": 400,
    },
    {
        "VESSEL_NAME": "Thialf",
        "VESSEL_SUBTYPE": "crane_vessel",
        "MAIN_CRANE_CAPACITY_T": 7100.0,
        "YEAR_BUILT": 1985,
        "LOA_M": 201.6,
        "BEAM_M": 88.4,
        "DP_CLASS": 2,
        "QUARTERS_CAPACITY": 736,
    },
    {
        "VESSEL_NAME": "Balder",
        "VESSEL_SUBTYPE": "crane_vessel",
        "MAIN_CRANE_CAPACITY_T": 6300.0,
        "YEAR_BUILT": 1978,
        "LOA_M": 154.0,
        "BEAM_M": 86.0,
        "DP_CLASS": 2,
        "QUARTERS_CAPACITY": 596,
    },
]
