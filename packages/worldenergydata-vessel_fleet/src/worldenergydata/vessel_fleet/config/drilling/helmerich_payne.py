"""Helmerich & Payne fleet collection config."""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="helmerich_payne",
    fleet_url="https://www.helmerichpayne.com/rigs",
    vessel_category="drilling_rig",
    vessel_type="land_rig",
    owner="Helmerich & Payne",
    table_selector="table.fleet-table",
    field_mapping={
        "Rig Name": "VESSEL_NAME",
        "Name": "VESSEL_NAME",
        "Model": "RIG_DESIGN",
        "Type": "RIG_TYPE",
        "Horsepower": "DRAWWORKS_HP",
    },
    rate_limit=0.5,
)

KNOWN_VESSELS = [
    {
        "VESSEL_NAME": "FlexRig 3",
        "RIG_TYPE": "land_rig",
        "RIG_DESIGN": "FlexRig",
        "SUPER_SPEC": True,
        "WALKING": True,
    },
]
