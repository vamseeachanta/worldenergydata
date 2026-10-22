"""Synthetic Phase 1B assessment; writes JSON to stdout, never incident data.

Hand calculation: three activities x two dates x five distinct incidents gives
thirty rows. Each activity has ten incidents; each season has fifteen. All
windows have one vendor type, so that type has thirty. These are fixture counts,
not measured HSE results. No exposure denominator or significance is assumed.

The five-incident disclosure floor is from the issue-416 plan (2026-05-18),
Operator Aggregation Contract rule 2. The dates straddle NHC's Atlantic hurricane
season: https://www.nhc.noaa.gov/climo/ (accessed 2026-10-22).
"""

from __future__ import annotations

import json

from worldenergydata.bsee.analysis.intervention.hse_patterns import assess_patterns


def worked_example() -> dict[str, object]:
    """Return aggregate candidates from a fully enumerated synthetic cohort."""
    incidents = [
        {
            "incident_id": f"synthetic-{code}-{day}-{i}",
            "source": "BSEE",
            "record_kind": "incident",
            "operator": "synthetic identity",
            "lease_number": "synthetic lease",
            "incident_date": day,
            "activity_code": code,
        }
        for code in ("PERS", "PSAFE", "CRANE")
        for day in ("2024-01-01", "2024-06-01")
        for i in range(5)
    ]
    windows = [
        {
            "BUS_ASC_NAME": "SYNTHETIC IDENTITY",
            "BOTM_LEASE_NUM": "synthetic lease",
            "WAR_START_DT": "2024-01-01",
            "WAR_END_DT": "2024-12-31",
            "vendor_type": "wireline",
        }
    ]
    return assess_patterns(incidents, windows).public_summary()


if __name__ == "__main__":
    print(json.dumps(worked_example(), indent=2, sort_keys=True))
