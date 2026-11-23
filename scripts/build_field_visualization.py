#!/usr/bin/env python3
"""Build field visualization outputs (WRK-116 Phase 7).

Generates interactive well location map and 3D subsurface view
from enriched WAR data and borehole coordinates.

Usage:
    PYTHONPATH=src python scripts/build_field_visualization.py
    PYTHONPATH=src python scripts/build_field_visualization.py --area-code MC
    PYTHONPATH=src python scripts/build_field_visualization.py --output-dir reports/bsee/viz
"""

from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate field visualization outputs from WAR data.",
    )
    parser.add_argument(
        "--area-code",
        type=str,
        default=None,
        help="Filter to a specific OCS area code (e.g. MC, GC, WR).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports/bsee/visualization",
        help="Output directory for HTML/SVG files.",
    )
    return parser.parse_args()


def main() -> None:
    """Load data and generate field visualizations."""
    args = _parse_args()

    fleet_path = Path("data/modules/bsee/.local/rig_fleet/rig_fleet_full.bin")
    if not fleet_path.exists():
        print(f"ERROR: Fleet data not found at {fleet_path}.")
        print("Run build_rig_fleet_from_war.py first.")
        sys.exit(1)

    print("Loading fleet data...")
    with open(fleet_path, "rb") as fh:
        fleet = pickle.load(fh)

    print("Loading WAR data...")
    from worldenergydata.bsee.data.loaders.rig_fleet.war_acquirer import (
        WARDataAcquirer,
    )
    from worldenergydata.bsee.data.scrapers.bsee_web import BSEEWebScraper
    from worldenergydata.bsee.data.processors.in_memory import MemoryProcessor

    acquirer = WARDataAcquirer(BSEEWebScraper(), MemoryProcessor())
    war = acquirer.acquire_war_dataframe()
    if war is None:
        print("ERROR: Could not load WAR data.")
        sys.exit(1)

    borehole = acquirer.acquire_borehole_dataframe()
    print(f"Loaded {len(war):,} WAR records")

    # Build enriched DataFrame
    from worldenergydata.bsee.analysis.intervention.enrichment_engine import (
        ActivityEnrichmentEngine,
    )

    engine = ActivityEnrichmentEngine(war_df=war, fleet_df=fleet, borehole_df=borehole)
    enriched = engine.enrich()
    print(f"Enriched DataFrame: {len(enriched):,} rows")

    if args.area_code:
        enriched = enriched[enriched["AREA_CODE"] == args.area_code]
        print(f"Filtered to area {args.area_code}: {len(enriched):,} rows")

    from worldenergydata.bsee.analysis.intervention.field_visualization import (
        FieldVisualizationModule,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    viz = FieldVisualizationModule(
        enriched_df=enriched,
        borehole_df=borehole,
    )

    map_path = viz.generate_map(str(output_dir / "well_map.html"))
    print(f"Map saved to {map_path}")

    view_path = viz.generate_3d_view(str(output_dir / "subsurface_3d.html"))
    print(f"3D view saved to {view_path}")

    print("Done.")


if __name__ == "__main__":
    main()
