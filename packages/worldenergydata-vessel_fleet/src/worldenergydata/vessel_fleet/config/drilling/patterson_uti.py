"""Patterson-UTI Energy fleet collection config."""

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
)

CONFIG = ContractorConfig(
    name="patterson_uti",
    fleet_url="https://www.patenergy.com/rigs",
    vessel_category="drilling_rig",
    vessel_type="land_rig",
    owner="Patterson-UTI Energy",
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
        "VESSEL_NAME": "APEX 1500",
        "RIG_TYPE": "land_rig",
        "RIG_DESIGN": "APEX",
        "SUPER_SPEC": True,
        "DRAWWORKS_HP": 1500.0,
    },
]
