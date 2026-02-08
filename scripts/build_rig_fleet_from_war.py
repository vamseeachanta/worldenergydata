"""Build initial rig fleet inventory from WAR (Well Activity Report) data.

Reads the well_activity_summary CSV, uses RigFleetLoader.build_fleet_from_war()
to extract unique rigs with aggregated stats, prints the fleet, and saves the
result to a pickle binary file.
"""

from __future__ import annotations

import pickle
from pathlib import Path

import pandas as pd

from worldenergydata.modules.bsee.data.loaders.rig_fleet.rig_fleet_loader import (
    RigFleetLoader,
)

WAR_CSV = Path("data/modules/bsee/current/operations/well_activity_summary.csv")
OUTPUT_DIR = Path("data/modules/bsee/bin/rig_fleet")
OUTPUT_FILE = OUTPUT_DIR / "rig_fleet.bin"


def main() -> None:
    """Load WAR data, build fleet, print results, and save to pickle."""
    # Step 1: Read the WAR CSV
    print(f"Reading WAR data from {WAR_CSV} ...")
    war_df = pd.read_csv(WAR_CSV)
    print(f"  Loaded {len(war_df)} WAR records with columns: {list(war_df.columns)}")

    # Step 2: Build fleet using RigFleetLoader
    loader = RigFleetLoader()
    fleet_df = loader.build_fleet_from_war(war_df)

    if fleet_df.empty:
        print("ERROR: No rig fleet data was produced.")
        return

    # Step 3: Print the fleet DataFrame (all rows)
    print(f"\n=== Rig Fleet ({len(fleet_df)} rigs) ===\n")
    display_cols = ["RIG_NAME", "RIG_TYPE", "WELLS_DRILLED_COUNT"]
    available_display = [c for c in display_cols if c in fleet_df.columns]
    pd.set_option("display.max_rows", None)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 120)
    pd.set_option("display.max_colwidth", 50)
    print(fleet_df[available_display].to_string(index=False))

    # Also print full DataFrame with all columns for reference
    print(f"\n=== Full Fleet Details ===\n")
    print(fleet_df.to_string(index=False))

    # Step 4: Save to pickle
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "wb") as f:
        pickle.dump(fleet_df, f)
    print(f"\nFleet saved to {OUTPUT_FILE} ({OUTPUT_FILE.stat().st_size} bytes)")

    # Step 5: Summary stats
    print(f"\n=== Summary ===")
    print(f"  Total unique rigs: {len(fleet_df)}")
    if "RIG_TYPE" in fleet_df.columns:
        print(f"  Rig types breakdown:")
        for rig_type, count in fleet_df["RIG_TYPE"].value_counts().items():
            print(f"    {rig_type}: {count}")
    if "WELLS_DRILLED_COUNT" in fleet_df.columns:
        print(f"  Total unique wells covered: {fleet_df['WELLS_DRILLED_COUNT'].sum()}")


if __name__ == "__main__":
    main()
