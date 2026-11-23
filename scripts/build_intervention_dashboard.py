"""Generate the intervention insights dashboard from WAR data.

Usage:
    PYTHONPATH=src python scripts/build_intervention_dashboard.py
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path


def main() -> None:
    """Load WAR + fleet data, then generate the intervention dashboard."""
    fleet_path = Path("data/modules/bsee/.local/rig_fleet/rig_fleet_full.bin")
    if not fleet_path.exists():
        print(
            "ERROR: Fleet data not found at "
            f"{fleet_path}. Run build_rig_fleet_from_war.py first."
        )
        sys.exit(1)

    print("Loading fleet data...")
    with open(fleet_path, "rb") as f:
        fleet = pickle.load(f)

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

    print(f"Loaded {len(war):,} WAR records and {len(fleet):,} fleet entries")

    from worldenergydata.bsee.analysis.intervention.dashboard import (
        InterventionDashboard,
    )

    output_dir = Path("reports/bsee/intervention")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(output_dir / "intervention_dashboard.html")

    print("Generating dashboard...")
    dashboard = InterventionDashboard(war, fleet)
    result_path = dashboard.generate(output_path)
    print(f"Dashboard saved to {result_path}")


if __name__ == "__main__":
    main()
