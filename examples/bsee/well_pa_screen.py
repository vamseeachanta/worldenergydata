"""Worked P&A screen: synthetic counts and hypothetical prices, not field costs.

Independent calculation: two TA boreholes at 10 USD each plus three COM
boreholes at 20 USD each gives five candidates and 80 USD. One PA borehole
is excluded. These numbers are example inputs, not empirical coefficients.
Status source: BSEE Data Center, Borehole Status Code enumeration, retrieved
2026-10-20; https://www.data.bsee.gov/Main/HtmlPage.aspx?page=boreholeFields.
"""

import json

from worldenergydata.field_development.well_pa_risk import build_well_pa_signals

SNAPSHOT = {
    "basis": "Synthetic registered-bottom-lease attribution; arithmetic only",
    "source_boreholes": 7,
    "joined_boreholes": 6,
    "unmatched_counts": {"lease_not_in_registry": 1},
    "source_sha256": "a" * 64,
    "registry_sha256": "b" * 64,
    "source_retrieved_at_utc": "2026-10-20T00:00:00+00:00",
    "status_definitions_url": (
        "https://www.data.bsee.gov/Main/HtmlPage.aspx?page=boreholeFields"
    ),
    "fields": [
        {
            "field_id": "sample_field",
            "registered_leases": ["G00001"],
            "borehole_count": 6,
            "status_counts": {"TA": 2, "COM": 3, "PA": 1},
        }
    ],
}
COST_INPUTS = {
    "sample_field": {
        "unit_cost_usd": {"TA": "10", "COM": "20"},
        "source": "Independent hand calculation in examples/bsee/well_pa_screen.py",
        "price_basis": "Hypothetical constant USD; not a field estimate",
    }
}


if __name__ == "__main__":
    print(json.dumps(build_well_pa_signals(SNAPSHOT, COST_INPUTS), indent=2))
