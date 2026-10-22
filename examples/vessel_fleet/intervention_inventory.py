"""Run the artificial inventory example; no network requests or output files."""

from pathlib import Path

from worldenergydata.vessel_fleet.intervention_inventory import (
    load_intervention_inventory,
    query_intervention_inventory,
    summarize_intervention_inventory,
)


def main() -> None:
    assets = load_intervention_inventory([Path(__file__).with_suffix(".yml")])
    summary = summarize_intervention_inventory(assets)
    # The screening depth is an artificial example input, not a design limit.
    selected = query_intervention_inventory(
        assets,
        asset_class="rlwi_monohull",
        minimum_depth_m=200,
    )
    print(f"Distinct assets: {summary['distinct_assets']}")
    bounds = summary["gom_dedicated_observed"]
    print(f"Observed dedicated resident bounds: {bounds['lower']} to {bounds['upper']}")
    print(f"Conflicted assets: {summary['conflicted_assets']}")
    print(f"RLWI depth matches: {len(selected)}")


if __name__ == "__main__":
    main()
