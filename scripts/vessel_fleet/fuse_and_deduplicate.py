#!/usr/bin/env python3
"""Merge all vessel fleet sources, deduplicate, and validate.

Usage:
    python scripts/vessel_fleet/fuse_and_deduplicate.py [--data-dir <dir>]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from worldenergydata.vessel_fleet.dedup.deduplicator import deduplicate_fleet
from worldenergydata.vessel_fleet.quality.validator import validate_fleet
from worldenergydata.vessel_fleet.quality.completeness import fleet_completeness_report
from worldenergydata.vessel_fleet.storage.parquet import ParquetStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fuse and deduplicate vessel fleet")
    parser.add_argument(
        "--data-dir",
        default=str(_PROJECT_ROOT / "data/modules/vessel_fleet"),
        help="Base data directory",
    )
    args = parser.parse_args()
    data_dir = Path(args.data_dir)

    # Collect all raw sources
    raw_dir = data_dir / "raw"
    all_records: list[dict] = []

    for source_dir in sorted(raw_dir.iterdir()) if raw_dir.exists() else []:
        if not source_dir.is_dir():
            continue
        store = ParquetStore(base_dir=source_dir)
        for pq_file in store.list_files():
            records = store.load(pq_file.name)
            logger.info("Loaded %d records from %s/%s", len(records), source_dir.name, pq_file.name)
            all_records.extend(records)

    if not all_records:
        logger.warning("No raw records found in %s", raw_dir)
        return 0

    logger.info("Total raw records: %d", len(all_records))

    # Deduplicate
    deduped = deduplicate_fleet(all_records)

    # Split by category
    drilling = [r for r in deduped if r.get("VESSEL_CATEGORY") == "drilling_rig"]
    construction = [r for r in deduped if r.get("VESSEL_CATEGORY") == "construction_vessel"]
    other = [r for r in deduped if r.get("VESSEL_CATEGORY") not in ("drilling_rig", "construction_vessel")]

    # Validate
    if drilling:
        validate_fleet(drilling, "drilling_rig")
        report = fleet_completeness_report(drilling, "drilling_rig")
        logger.info("Drilling rigs completeness: %.1f%%", report["avg_completeness"] * 100)

    if construction:
        validate_fleet(construction, "construction_vessel")
        report = fleet_completeness_report(construction, "construction_vessel")
        logger.info("Construction vessels completeness: %.1f%%", report["avg_completeness"] * 100)

    # Save curated output
    curated_dir = data_dir / "curated"
    curated_store = ParquetStore(base_dir=curated_dir)

    if drilling:
        curated_store.save(drilling, "drilling_rigs.parquet")
        curated_store.export_csv("drilling_rigs.parquet", "drilling_rigs.csv")

    if construction:
        curated_store.save(construction, "construction_vessels.parquet")
        curated_store.export_csv("construction_vessels.parquet", "construction_vessels.csv")

    if other:
        curated_store.save(other, "other_vessels.parquet")

    logger.info(
        "Curated: %d drilling rigs, %d construction vessels, %d other",
        len(drilling), len(construction), len(other),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
