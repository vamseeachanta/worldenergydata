"""WAR activity aggregation engine (WRK-115 Phase 1).

Classifies WAR (Well Activity Report) records by rig type and activity
category (drilling / intervention / unknown), then provides yearly
aggregations for downstream analysis.
"""

from __future__ import annotations

import pandas as pd

from worldenergydata.bsee.data.loaders.rig_fleet.constants import (
    RigType,
    classify_rig_type,
)

_DRILLING_TYPES: frozenset[str] = frozenset(
    {
        RigType.DRILLSHIP.value,
        RigType.SEMI_SUBMERSIBLE.value,
        RigType.JACK_UP.value,
        RigType.PLATFORM_RIG.value,
        RigType.TENDER_ASSISTED.value,
        RigType.INLAND_BARGE.value,
        RigType.SUBMERSIBLE.value,
    }
)

_INTERVENTION_TYPES: frozenset[str] = frozenset(
    {
        RigType.WIRELINE_UNIT.value,
        RigType.COIL_TUBING_UNIT.value,
        RigType.LIFT_BOAT.value,
        RigType.SNUBBING_UNIT.value,
        RigType.WORKOVER_RIG.value,
        RigType.SUPPORT_VESSEL.value,
        RigType.PUMPING_UNIT.value,
    }
)


def classify_activity(rig_type: str) -> str:
    """Map a rig-type string to an activity category.

    Returns:
        ``"drilling"``, ``"intervention"``, or ``"unknown"``.
    """
    if rig_type in _DRILLING_TYPES:
        return "drilling"
    if rig_type in _INTERVENTION_TYPES:
        return "intervention"
    return "unknown"


# -- Aggregation columns used by both groupby helpers -----------------------

_AGG_SPEC: dict[str, tuple[str, str]] = {
    "activity_count": ("API_WELL_NUMBER", "count"),
    "unique_wells": ("API_WELL_NUMBER", "nunique"),
    "unique_leases": ("BOTM_LEASE_NUM", "nunique"),
    "unique_areas": ("AREA_CODE", "nunique"),
}


class WARActivityAggregator:
    """Enrich and aggregate WAR records by rig type / activity category."""

    def __init__(self, war_df: pd.DataFrame, fleet_df: pd.DataFrame) -> None:
        self._war_df = war_df.copy()
        self._fleet_df = fleet_df.copy()

    # -- internal enrichment ------------------------------------------------

    def _join_rig_types(self) -> pd.DataFrame:
        """Left-join WAR to fleet and apply heuristic fallback."""
        df = self._war_df.merge(
            self._fleet_df[["RIG_NAME", "RIG_TYPE"]],
            on="RIG_NAME",
            how="left",
        )

        # Heuristic fallback for unmatched rigs.
        mask = df["RIG_TYPE"].isna()
        if mask.any():
            df.loc[mask, "RIG_TYPE"] = df.loc[mask, "RIG_NAME"].apply(
                lambda name: classify_rig_type(str(name)).value
                if pd.notna(name)
                else RigType.UNKNOWN.value
            )

        # Activity category.
        df["ACTIVITY_CATEGORY"] = df["RIG_TYPE"].map(classify_activity)

        # Parse year from WAR_START_DT, falling back to WAR_END_DT.
        dt = pd.to_datetime(
            df["WAR_START_DT"], format="mixed", dayfirst=False, errors="coerce"
        )
        if "WAR_END_DT" in df.columns:
            fallback = pd.to_datetime(
                df["WAR_END_DT"],
                format="mixed",
                dayfirst=False,
                errors="coerce",
            )
            dt = dt.fillna(fallback)

        df["YEAR"] = dt.dt.year.astype("Int64")

        return df

    # -- public aggregations ------------------------------------------------

    def aggregate_by_year_and_type(self) -> pd.DataFrame:
        """Group WAR data by ``[YEAR, RIG_TYPE]``."""
        enriched = self._join_rig_types()
        if enriched.empty:
            return pd.DataFrame(
                columns=["YEAR", "RIG_TYPE", *_AGG_SPEC.keys()]
            )
        result = (
            enriched.groupby(["YEAR", "RIG_TYPE"], dropna=False)
            .agg(**_AGG_SPEC)
            .reset_index()
            .sort_values(["YEAR", "RIG_TYPE"])
            .reset_index(drop=True)
        )
        return result

    def aggregate_by_year_and_category(self) -> pd.DataFrame:
        """Group WAR data by ``[YEAR, ACTIVITY_CATEGORY]``."""
        enriched = self._join_rig_types()
        if enriched.empty:
            return pd.DataFrame(
                columns=["YEAR", "ACTIVITY_CATEGORY", *_AGG_SPEC.keys()]
            )
        result = (
            enriched.groupby(["YEAR", "ACTIVITY_CATEGORY"], dropna=False)
            .agg(**_AGG_SPEC)
            .reset_index()
            .sort_values(["YEAR", "ACTIVITY_CATEGORY"])
            .reset_index(drop=True)
        )
        return result

    def get_summary(self) -> dict:
        """Return a high-level summary of the WAR dataset."""
        by_type = self.aggregate_by_year_and_type()
        by_cat = self.aggregate_by_year_and_category()

        total = int(by_type["activity_count"].sum()) if len(by_type) else 0

        if by_type.empty:
            year_range: tuple[int | None, int | None] = (None, None)
        else:
            year_range = (
                int(by_type["YEAR"].min()),
                int(by_type["YEAR"].max()),
            )

        rig_type_counts: dict[str, int] = {}
        for _, row in by_type.iterrows():
            rt = row["RIG_TYPE"]
            rig_type_counts[rt] = rig_type_counts.get(rt, 0) + int(
                row["activity_count"]
            )

        category_counts: dict[str, int] = {}
        for _, row in by_cat.iterrows():
            cat = row["ACTIVITY_CATEGORY"]
            category_counts[cat] = category_counts.get(cat, 0) + int(
                row["activity_count"]
            )

        return {
            "total_war_records": total,
            "year_range": year_range,
            "rig_type_counts": rig_type_counts,
            "category_counts": category_counts,
        }
