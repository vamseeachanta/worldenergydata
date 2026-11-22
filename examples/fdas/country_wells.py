"""Synthetic DataVic-shaped inputs, explicit activity, and FDAS drilling CAPEX.

Scenario inputs are not measured data. Four supplied active days at a selected
rate of 0.5 million USD/day yield 2.0 million USD by independent multiplication.
No drilling duration is inferred from the well's spud date.
"""

import json
from datetime import date

from worldenergydata.fdas.adapters.datavic_wells import read_datavic_wells
from worldenergydata.fdas.analysis.cashflow import CashflowEngine
from worldenergydata.fdas.core.config import AssumptionsManager
from worldenergydata.fdas.data.country_drilling import (
    DrillingActivity,
    build_drilling_timeline,
)


def run_example() -> dict:
    """Return scenario inputs and answers with monetary units explicit."""
    raw = json.dumps(
        {
            "type": "FeatureCollection",
            "numberMatched": 1,
            "numberReturned": 1,
            "features": [
                {
                    "type": "Feature",
                    "id": "pet_wells.synthetic",
                    "properties": {
                        "siteid": 1,
                        "spud_date": "2024-01-30",
                        "abswaterdepth": None,
                    },
                }
            ],
        }
    ).encode()
    exported = read_datavic_wells(
        raw, development_by_site_id={"1": "Example"}, water_depth_unit=None
    )
    well = exported.wells[0]
    # Scenario assumption: Jan 30, Jan 31, Feb 1, Feb 2 are active drilling days.
    activity = DrillingActivity(
        *well.key, date(2024, 1, 30), date(2024, 2, 3), "urn:synthetic:four-active-days"
    )
    timeline = build_drilling_timeline(
        exported.wells, [activity], development="Example"
    )
    # Selected scenario input, not an empirical rig-rate coefficient.
    rate_mm_usd_per_day = 0.5
    capex = CashflowEngine(AssumptionsManager()).calculate_drilling_capex(
        timeline.as_cashflow_input()["drilling_monthly"], rate_mm_usd_per_day
    )
    return {
        "synthetic": True,
        "status": timeline.status,
        "day_basis": "supplied active drilling intervals, end exclusive",
        "rate_mm_usd_per_day": rate_mm_usd_per_day,
        "drilling_monthly": timeline.drilling_monthly,
        "drilling_capex_mm_usd": capex,
        "total_drilling_capex_mm_usd": sum(capex.values()),
    }


if __name__ == "__main__":
    print(json.dumps(run_example(), indent=2))
