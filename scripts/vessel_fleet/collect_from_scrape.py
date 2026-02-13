#!/usr/bin/env python3
"""Collect vessel fleet records from Puppeteer scrape JSON data.

Parses Noble and Seadrill scrape JSON files and saves the results
as Parquet files for downstream processing.

Usage:
    PYTHONPATH="src:../assetutilities/src" python3 scripts/vessel_fleet/collect_from_scrape.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure src is on the path when run as a script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from worldenergydata.vessel_fleet.collectors.scrape_parser import (
    parse_noble_scrape,
    parse_seadrill_scrape,
)
from worldenergydata.vessel_fleet.storage.parquet import ParquetStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_DATA_ROOT = _PROJECT_ROOT / "data" / "modules" / "vessel_fleet"
_SCRAPE_DIR = _DATA_ROOT / "raw" / "contractor_scrape"
_OUTPUT_DIR = _DATA_ROOT / "raw" / "spec_details"

NOBLE_JSON = _SCRAPE_DIR / "noble.json"
SEADRILL_JSON = _SCRAPE_DIR / "seadrill.json"


def main() -> None:
    """Parse scrape JSONs and save to Parquet."""
    store = ParquetStore(_OUTPUT_DIR)

    # --- Noble ---
    logger.info("Parsing Noble scrape: %s", NOBLE_JSON)
    noble_records = parse_noble_scrape(NOBLE_JSON)
    noble_path = store.save(noble_records, "noble.parquet")
    _print_summary("Noble Corporation", noble_records, noble_path)

    # --- Seadrill ---
    logger.info("Parsing Seadrill scrape: %s", SEADRILL_JSON)
    seadrill_records = parse_seadrill_scrape(SEADRILL_JSON)
    seadrill_path = store.save(seadrill_records, "seadrill.parquet")
    _print_summary("Seadrill Limited", seadrill_records, seadrill_path)

    # --- Combined summary ---
    total = len(noble_records) + len(seadrill_records)
    print(f"\n{'='*60}")
    print(f"Total records saved: {total}")
    print(f"Output directory: {_OUTPUT_DIR}")
    print(f"{'='*60}")


def _print_summary(
    contractor: str,
    records: list[dict],
    path: Path,
) -> None:
    """Print a summary table for a contractor's parsed records."""
    print(f"\n--- {contractor} ---")
    print(f"  Records: {len(records)}")
    print(f"  Output:  {path}")

    if not records:
        return

    # Count by rig type
    type_counts: dict[str, int] = {}
    for rec in records:
        rt = rec.get("RIG_TYPE", "unknown")
        type_counts[rt] = type_counts.get(rt, 0) + 1

    print("  Rig types:")
    for rt, count in sorted(type_counts.items()):
        print(f"    {rt}: {count}")

    # Count PDF links
    pdf_count = sum(1 for r in records if r.get("DATA_SOURCE_URL"))
    print(f"  With PDF spec link: {pdf_count}/{len(records)}")


if __name__ == "__main__":
    main()
