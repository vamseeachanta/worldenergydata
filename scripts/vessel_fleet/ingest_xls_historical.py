#!/usr/bin/env python3
"""Ingest historical XLS fleet data into vessel fleet Parquet store.

Usage:
    python scripts/vessel_fleet/ingest_xls_historical.py <xls_path> [--output-dir <dir>]

Arguments:
    xls_path      Path to the master XLS file
    --output-dir  Output directory (default: data/modules/vessel_fleet/raw/xls_historical)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add src to path for script execution
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from worldenergydata.vessel_fleet.parsers.xls import XlsFleetParser
from worldenergydata.vessel_fleet.storage.parquet import ParquetStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_DIR = (
    _PROJECT_ROOT / "data" / "modules" / "vessel_fleet" / "raw" / "xls_historical"
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest XLS fleet data")
    parser.add_argument("xls_path", help="Path to the master XLS file")
    parser.add_argument(
        "--output-dir",
        default=str(_DEFAULT_OUTPUT_DIR),
        help="Output directory for Parquet files",
    )
    args = parser.parse_args()

    xls_path = Path(args.xls_path)
    if not xls_path.exists():
        logger.error("File not found: %s", xls_path)
        return 1

    logger.info("Parsing %s ...", xls_path.name)
    xls_parser = XlsFleetParser(xls_path)
    records = xls_parser.parse()

    logger.info("Parsed %d rigs", len(records))

    store = ParquetStore(base_dir=args.output_dir)
    store.save(records, filename="floaters.parquet")
    store.export_csv("floaters.parquet", "floaters.csv")

    logger.info("Done. Output: %s", args.output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
