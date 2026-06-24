"""Boskalis Westminster fleet collection config."""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="boskalis",
    fleet_url="https://boskalis.com/fleet",
    vessel_category="construction_vessel",
    vessel_type="heavy_transport",
    owner="Boskalis Westminster",
    table_selector="table.fleet-table",
    field_mapping={
        "Name": "VESSEL_NAME",
        "Vessel": "VESSEL_NAME",
        "Type": "VESSEL_SUBTYPE",
        "Deadweight": "DEADWEIGHT_T",
        "Year Built": "YEAR_BUILT",
        "Length": "LOA_M",
        "Beam": "BEAM_M",
    },
    rate_limit=0.5,
)

KNOWN_VESSELS = [
    {
        "VESSEL_NAME": "Boka Vanguard",
        "VESSEL_SUBTYPE": "heavy_transport",
        "DEADWEIGHT_T": 110000.0,
        "YEAR_BUILT": 2012,
        "LOA_M": 275.0,
        "BEAM_M": 70.0,
    },
]
