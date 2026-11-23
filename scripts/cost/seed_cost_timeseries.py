# ABOUTME: Seeds the curated cost-basis CSVs from researched, individually-cited records.
# ABOUTME: Issue #844 — every record here was read off a fetched page and carries its verbatim quote.
"""
seed_cost_timeseries
====================

Writes ``data/modules/cost/curated/cost_component_timeseries.csv`` and
``sanctioned_projects.csv`` from the research records below, then appends the
FRED reference series (CPI / PPI / Brent / WTI) pulled live.

WHY THE RECORDS LIVE IN CODE
----------------------------
They are literals here — not typed straight into the CSV — so that every figure
passes through ``CostObservation``'s validator before it can reach the dataset.
A record missing a quote, a URL or an access date cannot be committed: the seed
fails. This mirrors ``cost/data_collection/public_dataset.py``, which holds the
existing sanction dataset the same way.

FIGURE TYPE IS LORE, NOT DECORATION
-----------------------------------
The single most important interpretation rule in this dataset:

* ``fleet_average`` — a contractor's "Estimated Average Contract Dayrate"
  (Transocean) or "Average Day Rates" (Valaris). These are **backlog-weighted
  averages of rigs already under contract**. They lag the market badly and are
  **survivorship-biased upward**, because stacked rigs are excluded and expensive
  legacy contracts persist for years. Transocean's ultra-deepwater average still
  read ~$484k in Q1-2016 while new fixtures were being signed at a fraction of it.
* ``single_fixture`` — an actual contract award. This is the market-clearing price.
* ``market_average`` — a third-party average of *awards* (Rigzone, Esgian).

**Fleet averages and fixtures must never be plotted on the same line.** They are
different series that answer different questions, and conflating them would
manufacture a cost history that never happened. The ``figure_type`` column is what
lets a downstream consumer keep them apart.

DELIBERATELY EXCLUDED
---------------------
* IHS Petrodata's 2013 jackup figures (487, 599) — those are **index values, not
  dollars**. Sourced and real, but mixing them into a $/day series would corrupt it.
* A "$130,000 average for 2000" midpoint — the source states a *band* ($120k–$140k
  across mid-2000 to mid-2004). The midpoint is a derivation, not a printed figure,
  so the band endpoints are recorded and the midpoint is not.
* offshoreindustry.co.uk day-rate tracker — reads as thin AI-generated SEO content
  with no verifiable primary attribution. Its numbers happened to be plausible;
  that is not a reason to trust them.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from worldenergydata.cost.timeseries.dataset import (  # noqa: E402
    SANCTIONED_CSV,
    TIMESERIES_CSV,
    curated_dir,
    write_sanctioned_csv,
    write_timeseries_csv,
)
from worldenergydata.cost.timeseries.records import (  # noqa: E402
    RIG_DAY_RATES,
    SANCTIONED_PROJECTS,
    SURF_LUMPSUM_AWARDS,
    UCCI_ANCHORS,
    VESSEL_DAY_RATES,
)
from worldenergydata.cost.timeseries.reference_series import (  # noqa: E402
    build_reference_observations,
)

ACCESSED = date(2026, 7, 14)


def main() -> int:
    curated = curated_dir(PROJECT_ROOT)

    research_rows = (
        list(RIG_DAY_RATES)
        + list(VESSEL_DAY_RATES)
        + list(SURF_LUMPSUM_AWARDS)
        + list(UCCI_ANCHORS)
    )
    print(f"research rows (hand-sourced, each with a quote): {len(research_rows)}")

    print("fetching reference series from FRED ...")
    reference_rows = build_reference_observations(accessed_date=ACCESSED, start_year=1998)
    print(f"reference rows (CPI/PPI/Brent/WTI): {len(reference_rows)}")

    n = write_timeseries_csv(research_rows + reference_rows, curated / TIMESERIES_CSV)
    print(f"wrote {n:,} rows -> {curated / TIMESERIES_CSV}")

    m = write_sanctioned_csv(SANCTIONED_PROJECTS, curated / SANCTIONED_CSV)
    print(f"wrote {m:,} projects -> {curated / SANCTIONED_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
