"""Cadeler A/S fleet collection config (formerly Eneti / Swire Blue Ocean)."""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="cadeler",
    fleet_url="https://www.cadeler.com/fleet",
    vessel_category="construction_vessel",
    vessel_type="wind_installation",
    owner="Cadeler A/S",
    table_selector="div.fleet-grid table",
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
        "VESSEL_NAME": "Wind Osprey",
        "VESSEL_SUBTYPE": "wind_installation",
        "MAIN_CRANE_CAPACITY_T": 1600.0,
        "YEAR_BUILT": 2012,
    },
    {
        "VESSEL_NAME": "Wind Orca",
        "VESSEL_SUBTYPE": "wind_installation",
        "MAIN_CRANE_CAPACITY_T": 1200.0,
        "YEAR_BUILT": 2012,
    },
]
