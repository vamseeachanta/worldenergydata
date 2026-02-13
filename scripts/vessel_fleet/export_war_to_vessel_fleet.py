#!/usr/bin/env python3
"""Export BSEE WAR fleet data to vessel_fleet Parquet format.

Reads the WAR full fleet binary, maps columns to vessel_fleet schema,
filters invalid entries, and writes to Parquet via ParquetStore.

Usage:
    python scripts/vessel_fleet/export_war_to_vessel_fleet.py [--war-bin <path>] [--output-dir <dir>]
"""

from __future__ import annotations

import logging
import pickle
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

import pandas as pd

from worldenergydata.vessel_fleet.exporters.war_export import (
    export_war_to_vessel_fleet,
)
from worldenergydata.vessel_fleet.storage.parquet import ParquetStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_DEFAULT_WAR_BIN = (
    _PROJECT_ROOT / "data/modules/bsee/.local/rig_fleet/rig_fleet_full.bin"
)
_DEFAULT_OUTPUT_DIR = _PROJECT_ROOT / "data/modules/vessel_fleet/raw/bsee_war"
_OUTPUT_FILENAME = "war_fleet.parquet"


def _load_war_fleet(war_bin_path: Path) -> pd.DataFrame:
    """Load WAR fleet DataFrame from a pickle binary file."""
    if not war_bin_path.exists():
        logger.error("WAR fleet binary not found: %s", war_bin_path)
        return pd.DataFrame()

    with open(war_bin_path, "rb") as f:
        df = pickle.load(f)  # nosec B301

    if not isinstance(df, pd.DataFrame):
        logger.error("WAR binary does not contain a DataFrame")
        return pd.DataFrame()

    logger.info("Loaded %d records from %s", len(df), war_bin_path)
    return df


def _print_summary(records: list[dict]) -> None:
    """Print summary of exported records."""
    if not records:
        print("No records exported.")
        return

    df = pd.DataFrame(records)
    print(f"\nTotal rigs exported: {len(df)}")
    print(f"\nRig type distribution:")
    if "RIG_TYPE" in df.columns:
        type_counts = df["RIG_TYPE"].value_counts(dropna=False)
        for rig_type, count in type_counts.items():
            label = rig_type if pd.notna(rig_type) else "(unclassified)"
            print(f"  {label}: {count}")
    else:
        print("  (no RIG_TYPE column)")


def main() -> int:
    """Run the WAR-to-vessel_fleet export."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Export BSEE WAR fleet to vessel_fleet format"
    )
    parser.add_argument(
        "--war-bin",
        default=str(_DEFAULT_WAR_BIN),
        help="Path to WAR fleet binary (pickle)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(_DEFAULT_OUTPUT_DIR),
        help="Output directory for Parquet file",
    )
    args = parser.parse_args()

    war_bin_path = Path(args.war_bin)
    output_dir = Path(args.output_dir)

    # Load WAR fleet
    war_df = _load_war_fleet(war_bin_path)
    if war_df.empty:
        logger.error("No WAR fleet data loaded. Exiting.")
        return 1

    # Export to vessel_fleet format
    records = export_war_to_vessel_fleet(war_df)
    if not records:
        logger.error("No records after export. Exiting.")
        return 1

    # Save to Parquet
    store = ParquetStore(base_dir=output_dir)
    filepath = store.save(records, filename=_OUTPUT_FILENAME)
    logger.info("Saved to %s", filepath)

    # Print summary
    _print_summary(records)

    return 0


if __name__ == "__main__":
    sys.exit(main())
