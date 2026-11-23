"""Download and cache BSEE borehole data for WRK-116 pipeline.

Usage:
    python scripts/build_borehole_data.py --source local
    python scripts/build_borehole_data.py --source local --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from worldenergydata.bsee.data.loaders.well.borehole_acquirer import (
    BoreholeDataAcquirer,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download and cache BSEE borehole data"
    )
    parser.add_argument(
        "--source",
        choices=["download", "local"],
        default="local",
        help="'local' reads from cache; 'download' fetches from BSEE",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without executing",
    )
    args = parser.parse_args()

    if args.source == "download":
        print("Download mode not yet implemented -- use --source local")
        sys.exit(1)

    acquirer = BoreholeDataAcquirer()

    if args.dry_run:
        print("Dry run: would acquire borehole data from local cache")
        return

    df = acquirer.acquire_borehole_dataframe()
    if df is not None:
        print(f"Loaded {len(df)} borehole records")
        print(f"Columns: {list(df.columns)}")
        print("\nBOREHOLE_STAT_CD distribution:")
        print(df["BOREHOLE_STAT_CD"].value_counts())
    else:
        print("Failed to acquire borehole data")
        sys.exit(1)


if __name__ == "__main__":
    main()
