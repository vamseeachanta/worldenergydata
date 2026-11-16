"""Synthetic WAR inputs and interval-union answers for the legacy replacement.

Run with the repository environment: ``uv run python examples/bsee/war_rig_days.py``.
Method and independent hand calculation:
docs/modules/bsee/analysis/legacy_component_retirement.md (2026-10-20).
All numeric weights and dates below are synthetic inputs, not design limits.
"""

import pandas as pd

from worldenergydata.bsee.analysis.war_rig_days import (
    rig_days_by_bore,
    rig_days_by_well,
)

API = "120000000100"  # Synthetic API12, with a second bore of the same API10.
SIDETRACK_API = "120000000101"


def inputs():
    """Joined WAR rows; the caller supplies DRILL_FLUID_WGT in ppg.

    Source of units: Form BSEE-0133 (expiration 2024), item 10, MW / PPG.
    Zero is unreported under the retained input contract; infinity represents
    an invalid input to demonstrate filtering, not a physical measurement.
    """
    return pd.DataFrame(
        [
            [API, "2024-01-07", "2024-01-13", "DRL", "Unit A", 12.0],
            [API, "2024-01-10", "2024-01-16", "DRL", " unit a ", "14.0"],
            [API, "2024-01-14", "2024-01-20", "ST", "Unit B", 13.5],
            [API, "2024-01-21", "2024-01-27", "TA", None, 0],
            [API, "2024-02-04", "2024-02-10", "PA", "Unit B", None],
            [API, "2024-02-11", "2024-02-17", "COM", "Unit B", float("inf")],
            [SIDETRACK_API, "2024-01-14", "2024-01-20", "DRL", "Unit A", 11.5],
        ],
        columns=[
            "API_WELL_NUMBER",
            "WAR_START_DT",
            "WAR_END_DT",
            "WELL_ACTIVITY_CD",
            "RIG_NAME",
            "DRILL_FLUID_WGT",
        ],
    )


def analyse():
    """Return bore measurements and a well union; no input files are needed."""
    war = inputs()
    return rig_days_by_bore(war), rig_days_by_well(war)


def main():
    bores, wells = analyse()
    print("Synthetic joined WAR inputs (fluid weight in ppg):")
    print(inputs().to_string(index=False))
    print("\nInclusive WAR interval results:")
    print(
        bores[
            [
                "api12",
                "drilling_days",
                "completion_days",
                "sidetrack_days",
                "temp_abandonment_days",
                "perm_abandonment_days",
                "war_days_total",
            ]
        ].to_string(index=False)
    )
    row = bores.set_index("api12").loc[API]
    print(f"Rig credits: {row.rig_days_by_rig}")
    print(
        f"Maximum valid reported drilling-fluid weight: {row.max_drill_fluid_wgt:.1f} ppg"
    )
    print(f"Basis: {row.basis}")
    print("\nWell union (overlapping bore days counted once):")
    print(wells[["api10", "drilling_days", "war_days_total"]].to_string(index=False))


if __name__ == "__main__":
    main()
