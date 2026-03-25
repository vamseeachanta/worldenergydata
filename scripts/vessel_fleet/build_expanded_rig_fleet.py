#!/usr/bin/env python3
"""Build expanded rig fleet binary files for legacy BSEE loader.

Reads the curated vessel_fleet parquet, converts to legacy format via the
bridge module, and writes pickle .bin files to the BSEE .local directory
where RigFleetLoader picks them up automatically.

Outputs:
    data/modules/bsee/.local/rig_fleet/rig_fleet_full.bin
        Full fleet (all curated rigs).  The only .bin in this directory
        so that RigFleetLoader (which concatenates ALL .bin files in a
        directory) loads exactly the full fleet without duplicates.

    data/modules/bsee/.local/rig_fleet/subsets/rig_fleet.bin
        Subset matching the 16 originally committed sample rig names.
        Stored in a subdirectory so the loader does not auto-load it.

Usage:
    python3 scripts/vessel_fleet/build_expanded_rig_fleet.py

    # With custom paths:
    python3 scripts/vessel_fleet/build_expanded_rig_fleet.py \
        --curated data/modules/vessel_fleet/curated/drilling_rigs.parquet \
        --output-dir data/modules/bsee/.local/rig_fleet
"""

from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path

# Ensure src/ is on the path when running as a script
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "src"))

import pandas as pd

from worldenergydata.vessel_fleet.bridge.rig_fleet_bridge import (
    convert_curated_to_rig_fleet,
)

# Default paths relative to repo root
DEFAULT_CURATED = _REPO_ROOT / "data/modules/vessel_fleet/curated/drilling_rigs.parquet"
DEFAULT_OUTPUT_DIR = _REPO_ROOT / "data/modules/bsee/.local/rig_fleet"
DEFAULT_SAMPLE_BIN = _REPO_ROOT / "data/modules/bsee/bin/rig_fleet/rig_fleet.bin"


def _load_sample_rig_names(sample_bin: Path) -> list[str]:
    """Read rig names from the committed 16-rig sample bin."""
    if not sample_bin.exists():
        print(f"WARNING: sample bin not found at {sample_bin}")
        return []

    # Check for LFS stub
    with open(sample_bin, "rb") as f:
        header = f.read(40)
    if header.startswith(b"version https://git-lfs"):
        print(f"WARNING: {sample_bin} is a Git LFS stub, cannot read names")
        return []

    with open(sample_bin, "rb") as f:
        df = pickle.load(f)  # nosec B301

    if isinstance(df, pd.DataFrame) and "RIG_NAME" in df.columns:
        return df["RIG_NAME"].tolist()
    return []


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build expanded rig fleet .bin files for BSEE loader",
    )
    parser.add_argument(
        "--curated",
        type=Path,
        default=DEFAULT_CURATED,
        help="Path to curated drilling_rigs.parquet",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory for .bin files",
    )
    parser.add_argument(
        "--sample-bin",
        type=Path,
        default=DEFAULT_SAMPLE_BIN,
        help="Path to committed 16-rig sample .bin (for subset matching)",
    )
    args = parser.parse_args()

    # Validate input
    if not args.curated.exists():
        print(f"ERROR: curated parquet not found: {args.curated}")
        sys.exit(1)

    # Read and convert
    print(f"Reading curated parquet: {args.curated}")
    curated_df = pd.read_parquet(args.curated)
    print(f"  Curated records: {len(curated_df)}")

    print("Converting to legacy rig fleet format...")
    fleet_df = convert_curated_to_rig_fleet(curated_df)
    print(f"  Converted records: {len(fleet_df)}")
    print(f"  Columns: {list(fleet_df.columns)}")

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Save full fleet
    full_path = args.output_dir / "rig_fleet_full.bin"
    with open(full_path, "wb") as f:
        pickle.dump(fleet_df, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"\nSaved full fleet: {full_path}")
    print(f"  Size: {full_path.stat().st_size:,} bytes")

    # Save subset matching original 16 names (in subsets/ subdirectory
    # so the loader does not concatenate it with the full fleet)
    sample_names = _load_sample_rig_names(args.sample_bin)
    if sample_names:
        mask = fleet_df["RIG_NAME"].isin(sample_names)
        subset_df = fleet_df[mask].copy().reset_index(drop=True)
        subsets_dir = args.output_dir / "subsets"
        subsets_dir.mkdir(parents=True, exist_ok=True)
        subset_path = subsets_dir / "rig_fleet.bin"
        with open(subset_path, "wb") as f:
            pickle.dump(subset_df, f, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"\nSaved sample subset: {subset_path}")
        print(f"  Matched {len(subset_df)} of {len(sample_names)} "
              f"original rig names")
        if len(subset_df) < len(sample_names):
            matched = set(subset_df["RIG_NAME"])
            missing = [n for n in sample_names if n not in matched]
            print(f"  Missing names: {missing}")
    else:
        print("\nSkipped sample subset (no sample rig names available)")

    # Summary stats
    print("\n--- Summary ---")
    print(f"Total rigs:          {len(fleet_df)}")
    if "RIG_TYPE" in fleet_df.columns:
        type_counts = fleet_df["RIG_TYPE"].value_counts()
        print("\nRig type distribution:")
        for rt, count in type_counts.items():
            print(f"  {rt:25s} {count:5d}")
    if "DATA_SOURCE" in fleet_df.columns:
        source_counts = fleet_df["DATA_SOURCE"].value_counts()
        print("\nData source distribution:")
        for ds, count in source_counts.items():
            print(f"  {ds:25s} {count:5d}")
    null_pct = fleet_df.isnull().mean() * 100
    high_null = null_pct[null_pct > 50].sort_values(ascending=False)
    if not high_null.empty:
        print("\nColumns with >50% null:")
        for col, pct in high_null.items():
            print(f"  {col:30s} {pct:5.1f}%")


if __name__ == "__main__":
    main()
