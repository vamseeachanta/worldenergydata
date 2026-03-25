#!/usr/bin/env python3
"""Enrich vessel fleet data with maritime registry lookups.

Usage:
    python scripts/vessel_fleet/enrich_from_registries.py [--input <parquet>] [--output <parquet>]
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from worldenergydata.vessel_fleet.collectors.equasis_collector import EquasisCollector
from worldenergydata.vessel_fleet.collectors.classification_collector import ClassificationCollector
from worldenergydata.vessel_fleet.storage.parquet import ParquetStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich fleet with registry data")
    parser.add_argument(
        "--input",
        default=str(_PROJECT_ROOT / "data/modules/vessel_fleet/curated/drilling_rigs.parquet"),
        help="Input Parquet file",
    )
    parser.add_argument(
        "--output",
        default=str(_PROJECT_ROOT / "data/modules/vessel_fleet/raw/equasis/enriched.parquet"),
        help="Output Parquet file",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error("Input file not found: %s", input_path)
        return 1

    store = ParquetStore(base_dir=input_path.parent)
    records = store.load(input_path.name)
    logger.info("Loaded %d records from %s", len(records), input_path.name)

    # Equasis enrichment (requires credentials)
    equasis_user = os.environ.get("EQUASIS_USERNAME")
    equasis_pass = os.environ.get("EQUASIS_PASSWORD")

    if equasis_user and equasis_pass:
        equasis = EquasisCollector(username=equasis_user, password=equasis_pass)
        if equasis.authenticate():
            enriched = 0
            for record in records:
                if record.get("IMO_NUMBER"):
                    continue  # Already has IMO
                name = record.get("VESSEL_NAME", "")
                result = equasis.lookup_vessel(name)
                if result and result.get("IMO_NUMBER"):
                    record["IMO_NUMBER"] = result["IMO_NUMBER"]
                    if not record.get("FLAG_STATE"):
                        record["FLAG_STATE"] = result.get("FLAG_STATE")
                    if not record.get("CLASSIFICATION_SOCIETY"):
                        record["CLASSIFICATION_SOCIETY"] = result.get("CLASSIFICATION_SOCIETY")
                    if not record.get("MMSI"):
                        record["MMSI"] = result.get("MMSI")
                    enriched += 1
            logger.info("Equasis enriched %d vessels", enriched)
    else:
        logger.info("Skipping Equasis (no credentials in EQUASIS_USERNAME/EQUASIS_PASSWORD)")

    # Classification society enrichment for vessels with IMO
    class_collector = ClassificationCollector()
    class_enriched = 0
    for record in records:
        imo = record.get("IMO_NUMBER")
        if not imo or record.get("CLASS_NOTATION"):
            continue
        society = record.get("CLASSIFICATION_SOCIETY", "").upper()
        result = None
        if "ABS" in society:
            result = class_collector.lookup_abs(imo)
        elif "DNV" in society:
            result = class_collector.lookup_dnv(imo)
        if result and result.get("CLASS_NOTATION"):
            record["CLASS_NOTATION"] = result["CLASS_NOTATION"]
            class_enriched += 1
    logger.info("Classification enriched %d vessels", class_enriched)

    # Save enriched data
    output_path = Path(args.output)
    output_store = ParquetStore(base_dir=output_path.parent)
    output_store.save(records, filename=output_path.name)
    logger.info("Saved enriched data to %s", args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
