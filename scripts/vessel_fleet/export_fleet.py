#!/usr/bin/env python3
"""Export curated fleet data to Parquet + CSV.

Usage:
    python scripts/vessel_fleet/export_fleet.py [--data-dir <dir>]
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from worldenergydata.vessel_fleet.storage.parquet import ParquetStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Export curated fleet")
    parser.add_argument(
        "--data-dir",
        default=str(_PROJECT_ROOT / "data/modules/vessel_fleet/curated"),
        help="Curated data directory",
    )
    args = parser.parse_args()

    store = ParquetStore(base_dir=args.data_dir)

    for pq_file in store.list_files():
        csv_name = pq_file.stem + ".csv"
        store.export_csv(pq_file.name, csv_name)
        logger.info("Exported %s → %s", pq_file.name, csv_name)

    return 0


if __name__ == "__main__":
    sys.exit(main())
