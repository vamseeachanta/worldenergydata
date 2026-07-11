#!/usr/bin/env python3
"""ABOUTME: Country data-density badge rule shared by the all-regions atlas and
ABOUTME: the field-atlas Explorer feed (lifted verbatim from build_all_regions_atlas, #947).

STDLIB-ONLY by the deploy-parity convention (#850): generators import this via
the scripts/ sys.path-insert pattern; nothing here may require a third-party
package.

The rule has THREE branches (all load-bearing — see #947 plan r1 finding 2):
1. US is hardcoded RICH (BSEE materialised to full life-cycle depth in the GoM,
   even though the bsee module's catalog_status is "sample").
2. Countries with a dedicated national-regulator ingest module map that
   module's catalog_status through CATALOG_TO_BADGE.
3. Countries with no dedicated module fall back to SAMPLE — they are covered
   only by the shared curated reference inventory (offshore_assets).
"""

from __future__ import annotations

import json
from pathlib import Path

# Country (as spelled in coverage_summary) -> dedicated national-regulator ingest module
COUNTRY_MODULE = {
    "US": "bsee",
    "UK": "ukcs",
    "Norway": "sodir",
    "Brazil": "brazil_anp",
    "Mexico": "mexico_cnh",
    "Canada": "canada",
}
CATALOG_TO_BADGE = {
    "full": "RICH",
    "sample": "SAMPLE",
    "runtime_fetched": "ROADMAP",
    "missing": "ROADMAP",
}


def load_scorecard(path: str | Path) -> dict:
    """catalog_status per module from data/freshness-scorecard.json."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {k: v.get("catalog_status") for k, v in data["modules"].items()}


def badge_for(country: str, statuses: dict) -> tuple[str, str, str]:
    """Return (badge, module, catalog_status) for a country."""
    module = COUNTRY_MODULE.get(country)
    if country == "US":
        # BSEE materialised to full life-cycle depth in the Gulf of Mexico.
        return "RICH", "bsee", statuses.get("bsee", "sample")
    if module:
        status = statuses.get(module, "missing")
        return CATALOG_TO_BADGE.get(status, "ROADMAP"), module, status
    # No dedicated national module -> shared curated reference inventory only.
    return "SAMPLE", "offshore_assets (reference)", "reference"
