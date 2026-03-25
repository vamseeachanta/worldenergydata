"""Build rig fleet inventory from WAR (Well Activity Report) data.

Usage:
    uv run python scripts/build_rig_fleet_from_war.py --source download
    uv run python scripts/build_rig_fleet_from_war.py --source local
    uv run python scripts/build_rig_fleet_from_war.py --dry-run

Sources:
    download  - Download full WAR zip via BSEEWebScraper (default)
    local     - Read existing WAR CSV from data/modules/bsee/current/
"""

from __future__ import annotations

import argparse
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from worldenergydata.bsee.data.loaders.rig_fleet.rig_fleet_loader import (
    RigFleetLoader,
)

WAR_CSV = Path("data/modules/bsee/current/operations/well_activity_summary.csv")
OVERRIDES_CSV = Path("data/modules/bsee/bin/rig_fleet/rig_type_overrides.csv")
LOCAL_DIR = Path("data/modules/bsee/.local/rig_fleet")
OUTPUT_FILE = LOCAL_DIR / "rig_fleet_full.bin"
METADATA_FILE = LOCAL_DIR / "rig_fleet_metadata.json"


def _load_war_from_download() -> pd.DataFrame:
    """Download full WAR via BSEEWebScraper + MemoryProcessor."""
    from worldenergydata.bsee.data.loaders.rig_fleet.war_acquirer import (
        WARDataAcquirer,
    )
    from worldenergydata.bsee.data.processors.in_memory import MemoryProcessor
    from worldenergydata.bsee.data.scrapers.bsee_web import BSEEWebScraper

    scraper = BSEEWebScraper()
    processor = MemoryProcessor(use_optimized=False)
    acquirer = WARDataAcquirer(scraper=scraper, processor=processor)

    war_df = acquirer.acquire_war_dataframe()
    if war_df is None:
        raise RuntimeError("WAR download/extraction failed")
    return war_df


def _load_war_from_local() -> pd.DataFrame:
    """Read WAR data from local CSV."""
    if not WAR_CSV.exists():
        raise FileNotFoundError(f"WAR CSV not found at {WAR_CSV}")
    return pd.read_csv(WAR_CSV)


def main() -> None:
    """Build rig fleet from WAR data."""
    parser = argparse.ArgumentParser(description="Build rig fleet from WAR data")
    parser.add_argument(
        "--source",
        choices=["download", "local"],
        default="download",
        help="Data source: download full WAR or read local CSV (default: download)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print fleet stats without saving to disk",
    )
    args = parser.parse_args()

    # Step 1: Load WAR data
    print(f"Loading WAR data (source={args.source}) ...")
    if args.source == "download":
        war_df = _load_war_from_download()
    else:
        war_df = _load_war_from_local()
    print(f"  Loaded {len(war_df)} WAR records with columns: {list(war_df.columns)}")

    # Step 2: Build fleet
    loader = RigFleetLoader()
    fleet_df = loader.build_fleet_from_war(war_df)

    if fleet_df.empty:
        print("ERROR: No rig fleet data was produced.")
        return

    # Step 3: Apply overrides
    fleet_df = loader.load_overrides(OVERRIDES_CSV, fleet_df)

    # Step 4: Print fleet summary
    print(f"\n=== Rig Fleet ({len(fleet_df)} rigs) ===\n")
    display_cols = ["RIG_NAME", "RIG_TYPE", "WELLS_DRILLED_COUNT", "DATA_SOURCE"]
    available_display = [c for c in display_cols if c in fleet_df.columns]
    pd.set_option("display.max_rows", None)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 140)
    pd.set_option("display.max_colwidth", 50)
    print(fleet_df[available_display].to_string(index=False))

    # Step 5: Print unknown rigs report
    if "RIG_TYPE" in fleet_df.columns:
        unknown_rigs = fleet_df[fleet_df["RIG_TYPE"] == "unknown"]
        if not unknown_rigs.empty:
            print(f"\n=== Unknown Rigs ({len(unknown_rigs)}) ===")
            print("  Add these to rig_type_overrides.csv:")
            for _, row in unknown_rigs.iterrows():
                wells = row.get("WELLS_DRILLED_COUNT", "?")
                print(f"  {row['RIG_NAME']},{wells} wells")

    # Step 6: Summary stats
    print(f"\n=== Summary ===")
    print(f"  Total unique rigs: {len(fleet_df)}")
    if "RIG_TYPE" in fleet_df.columns:
        print("  Rig types breakdown:")
        for rig_type, count in fleet_df["RIG_TYPE"].value_counts().items():
            print(f"    {rig_type}: {count}")
    if "WELLS_DRILLED_COUNT" in fleet_df.columns:
        print(f"  Total unique wells covered: {fleet_df['WELLS_DRILLED_COUNT'].sum()}")

    if args.dry_run:
        print("\n[DRY RUN] Skipping file save.")
        return

    # Step 7: Save to .local/
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "wb") as f:
        pickle.dump(fleet_df, f)
    print(f"\nFleet saved to {OUTPUT_FILE} ({OUTPUT_FILE.stat().st_size} bytes)")

    # Step 8: Save metadata
    metadata = {
        "built_at": datetime.now(tz=timezone.utc).isoformat(),
        "source": args.source,
        "war_records": len(war_df),
        "rig_count": len(fleet_df),
        "rig_types": fleet_df["RIG_TYPE"].value_counts().to_dict()
        if "RIG_TYPE" in fleet_df.columns
        else {},
        "unknown_count": int(
            (fleet_df["RIG_TYPE"] == "unknown").sum()
        )
        if "RIG_TYPE" in fleet_df.columns
        else 0,
        "output_file": str(OUTPUT_FILE),
        "output_size_bytes": OUTPUT_FILE.stat().st_size,
    }
    METADATA_FILE.write_text(json.dumps(metadata, indent=2))
    print(f"Metadata saved to {METADATA_FILE}")

    # Step 9: Update data index
    _update_data_index(fleet_df, metadata)


def _update_data_index(fleet_df: pd.DataFrame, build_meta: dict) -> None:
    """Write or update the .local/data_index.json manifest."""
    index_path = Path("data/modules/bsee/.local/data_index.json")
    index_path.parent.mkdir(parents=True, exist_ok=True)

    if index_path.exists():
        try:
            index = json.loads(index_path.read_text())
        except (json.JSONDecodeError, OSError):
            index = {}
    else:
        index = {}

    index["generated_at"] = datetime.now(tz=timezone.utc).isoformat()
    index.setdefault("datasets", {})
    index["datasets"]["rig_fleet_full"] = {
        "path": str(OUTPUT_FILE),
        "size_bytes": build_meta["output_size_bytes"],
        "built_at": build_meta["built_at"],
        "built_from": build_meta["source"],
        "rig_count": build_meta["rig_count"],
    }

    index_path.write_text(json.dumps(index, indent=2))
    print(f"Data index updated at {index_path}")


if __name__ == "__main__":
    main()
