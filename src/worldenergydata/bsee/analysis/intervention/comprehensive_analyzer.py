"""Cross-cutting analyzer for enriched WAR data (WRK-116 Phase 3).

Computes structured analysis across 7 modules from the enriched DataFrame
produced by ``ActivityEnrichmentEngine.enrich()``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

_DUR_COLS = ["mean_days", "median_days", "count"]
_DEPTH_COLS = ["mean_md", "max_md", "count"]


def _empty_df(cols: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=cols)


class ComprehensiveActivityAnalyzer:
    """Cross-cutting analyzer for enriched WAR data."""

    def __init__(self, enriched_df: pd.DataFrame) -> None:
        self._df = enriched_df.copy()

    def analyze(self) -> dict:
        """Run all 7 analysis modules and return combined results."""
        return {
            "drilling_efficiency": self._analyze_drilling_efficiency(),
            "well_depth": self._analyze_well_depth(),
            "geological_era": self._analyze_geological_era(),
            "cross_activity": self._analyze_cross_activity(),
            "well_lifecycle": self._analyze_well_lifecycle(),
            "operator_portfolio": self._analyze_operator_portfolio(),
            "duration_benchmarking": self._analyze_duration_benchmarking(),
        }

    # -- Module 1: Drilling Efficiency ----------------------------------------

    def _analyze_drilling_efficiency(self) -> dict:
        empty = {
            "total_wells_with_duration": 0,
            "mean_drilling_days": 0.0,
            "median_drilling_days": 0.0,
            "by_rig_type": _empty_df(["RIG_TYPE"] + _DUR_COLS),
            "by_depth_class": _empty_df(["WATER_DEPTH_CLASS"] + _DUR_COLS),
            "by_year": _empty_df(["YEAR"] + _DUR_COLS),
        }
        if not {"DRILLING_DAYS", "ACTIVITY_CATEGORY"}.issubset(self._df.columns):
            return empty
        mask = self._df["DRILLING_DAYS"].notna() & (
            self._df["ACTIVITY_CATEGORY"].astype(str) == "drilling"
        )
        sub = self._df.loc[mask]
        if sub.empty:
            return empty
        return {
            "total_wells_with_duration": len(sub),
            "mean_drilling_days": float(sub["DRILLING_DAYS"].mean()),
            "median_drilling_days": float(sub["DRILLING_DAYS"].median()),
            "by_rig_type": self._grouped_duration(sub, "RIG_TYPE"),
            "by_depth_class": self._grouped_duration(sub, "WATER_DEPTH_CLASS"),
            "by_year": self._grouped_duration(sub, "YEAR"),
        }

    @staticmethod
    def _grouped_duration(df: pd.DataFrame, col: str) -> pd.DataFrame:
        if col not in df.columns:
            return _empty_df([col] + _DUR_COLS)
        grp = df.groupby(df[col].astype(str), dropna=False)["DRILLING_DAYS"]
        result = grp.agg(mean_days="mean", median_days="median", count="count")
        result = result.reset_index()
        result.columns = [col, "mean_days", "median_days", "count"]
        return result

    # -- Module 2: Well Depth -------------------------------------------------

    def _analyze_well_depth(self) -> dict:
        empty = {
            "mean_total_md": 0.0,
            "max_total_md": 0.0,
            "by_rig_type": _empty_df(["RIG_TYPE"] + _DEPTH_COLS),
            "by_area": _empty_df(["AREA_CODE"] + _DEPTH_COLS),
            "by_year": _empty_df(["YEAR"] + _DEPTH_COLS),
        }
        if "BH_TOTAL_MD" not in self._df.columns:
            return empty
        sub = self._df.loc[self._df["BH_TOTAL_MD"].notna()]
        if sub.empty:
            return empty
        return {
            "mean_total_md": float(sub["BH_TOTAL_MD"].mean()),
            "max_total_md": float(sub["BH_TOTAL_MD"].max()),
            "by_rig_type": self._grouped_depth(sub, "RIG_TYPE"),
            "by_area": self._grouped_depth(sub, "AREA_CODE"),
            "by_year": self._grouped_depth(sub, "YEAR"),
        }

    @staticmethod
    def _grouped_depth(df: pd.DataFrame, col: str) -> pd.DataFrame:
        if col not in df.columns:
            return _empty_df([col] + _DEPTH_COLS)
        grp = df.groupby(df[col].astype(str), dropna=False)["BH_TOTAL_MD"]
        result = grp.agg(mean_md="mean", max_md="max", count="count")
        result = result.reset_index()
        result.columns = [col, "mean_md", "max_md", "count"]
        return result

    # -- Module 3: Geological Era ---------------------------------------------

    def _analyze_geological_era(self) -> dict:
        empty = {
            "wells_with_era": 0,
            "era_distribution": _empty_df(
                ["GEOLOGICAL_ERA", "activity_count", "unique_wells"],
            ),
            "era_by_category": _empty_df(
                ["GEOLOGICAL_ERA", "ACTIVITY_CATEGORY", "count"],
            ),
        }
        if "GEOLOGICAL_ERA" not in self._df.columns:
            return empty
        sub = self._df.loc[self._df["GEOLOGICAL_ERA"].notna()]
        if sub.empty:
            return empty

        dist = (
            sub.groupby("GEOLOGICAL_ERA", dropna=False)
            .agg(
                activity_count=("API_WELL_NUMBER", "count"),
                unique_wells=("API_WELL_NUMBER", "nunique"),
            )
            .reset_index()
        )

        era_by_cat = (
            sub.groupby(
                [
                    sub["GEOLOGICAL_ERA"].astype(str),
                    sub["ACTIVITY_CATEGORY"].astype(str),
                ],
                dropna=False,
            )
            .size()
            .reset_index(name="count")
        )
        era_by_cat.columns = ["GEOLOGICAL_ERA", "ACTIVITY_CATEGORY", "count"]

        return {
            "wells_with_era": len(sub),
            "era_distribution": dist,
            "era_by_category": era_by_cat,
        }

    # -- Module 4: Cross Activity ---------------------------------------------

    def _analyze_cross_activity(self) -> dict:
        cat_col = "ACTIVITY_CATEGORY"
        _ratio_cols = ["drilling", "intervention", "ratio"]
        empty = {
            "drilling_count": 0,
            "intervention_count": 0,
            "ratio": 0.0,
            "by_depth_class": _empty_df(["WATER_DEPTH_CLASS"] + _ratio_cols),
            "by_area": _empty_df(["AREA_CODE"] + _ratio_cols),
        }
        if cat_col not in self._df.columns or self._df.empty:
            return empty

        cat_str = self._df[cat_col].astype(str)
        d_count = int((cat_str == "drilling").sum())
        i_count = int((cat_str == "intervention").sum())
        ratio = d_count / i_count if i_count > 0 else 0.0
        return {
            "drilling_count": d_count,
            "intervention_count": i_count,
            "ratio": float(ratio),
            "by_depth_class": self._cross_ratio(
                self._df,
                cat_col,
                "WATER_DEPTH_CLASS",
            ),
            "by_area": self._cross_ratio(self._df, cat_col, "AREA_CODE"),
        }

    @staticmethod
    def _cross_ratio(
        df: pd.DataFrame,
        cat_col: str,
        group_col: str,
    ) -> pd.DataFrame:
        cols = [group_col, "drilling", "intervention", "ratio"]
        if group_col not in df.columns:
            return _empty_df(cols)
        pivot = (
            df.assign(**{cat_col: df[cat_col].astype(str)})
            .groupby(
                [df[group_col].astype(str), df[cat_col].astype(str)],
                dropna=False,
            )
            .size()
            .reset_index(name="cnt")
        )
        pivot.columns = [group_col, cat_col, "cnt"]
        table = pivot.pivot_table(
            index=group_col,
            columns=cat_col,
            values="cnt",
            aggfunc="sum",
            fill_value=0,
        ).reset_index()
        for c in ("drilling", "intervention"):
            if c not in table.columns:
                table[c] = 0
        table["ratio"] = table.apply(
            lambda r: (
                r["drilling"] / r["intervention"] if r["intervention"] > 0 else 0.0
            ),
            axis=1,
        )
        return table[[group_col, "drilling", "intervention", "ratio"]].copy()

    # -- Module 5: Well Lifecycle ---------------------------------------------

    def _analyze_well_lifecycle(self) -> dict:
        empty = {
            "status_distribution": _empty_df(["WELL_STATUS", "count", "pct"]),
            "by_depth_class": _empty_df(
                ["WATER_DEPTH_CLASS", "WELL_STATUS", "count"],
            ),
            "completion_rate": 0.0,
        }
        if "WELL_STATUS" not in self._df.columns:
            return empty
        sub = self._df.loc[self._df["WELL_STATUS"].notna()].copy()
        if sub.empty:
            return empty

        status_str = sub["WELL_STATUS"].astype(str)
        counts = status_str.value_counts().reset_index()
        counts.columns = ["WELL_STATUS", "count"]
        total = int(counts["count"].sum())
        counts["pct"] = counts["count"] / total if total > 0 else 0.0

        if "WATER_DEPTH_CLASS" in sub.columns:
            by_dc = (
                sub.groupby(
                    [sub["WATER_DEPTH_CLASS"].astype(str), status_str],
                    dropna=False,
                )
                .size()
                .reset_index(name="count")
            )
            by_dc.columns = ["WATER_DEPTH_CLASS", "WELL_STATUS", "count"]
        else:
            by_dc = _empty_df(["WATER_DEPTH_CLASS", "WELL_STATUS", "count"])

        com_count = int((status_str == "COM").sum())
        return {
            "status_distribution": counts,
            "by_depth_class": by_dc,
            "completion_rate": float(com_count / total) if total else 0.0,
        }

    # -- Module 6: Operator Portfolio -----------------------------------------

    def _analyze_operator_portfolio(self) -> dict:
        _top_cols = ["BUS_ASC_NAME", "activity_count", "unique_wells", "unique_areas"]
        empty = {
            "top_operators": _empty_df(_top_cols),
            "by_depth_class": _empty_df(
                ["BUS_ASC_NAME", "WATER_DEPTH_CLASS", "count"],
            ),
            "by_rig_type": _empty_df(["BUS_ASC_NAME", "RIG_TYPE", "count"]),
        }
        if "BUS_ASC_NAME" not in self._df.columns or self._df.empty:
            return empty

        top = (
            self._df.groupby("BUS_ASC_NAME", dropna=False)
            .agg(
                activity_count=("API_WELL_NUMBER", "count"),
                unique_wells=("API_WELL_NUMBER", "nunique"),
                unique_areas=("AREA_CODE", "nunique"),
            )
            .reset_index()
        )
        top = top.sort_values(
            "activity_count",
            ascending=False,
        ).reset_index(drop=True)

        return {
            "top_operators": top,
            "by_depth_class": self._operator_cross(self._df, "WATER_DEPTH_CLASS"),
            "by_rig_type": self._operator_cross(self._df, "RIG_TYPE"),
        }

    @staticmethod
    def _operator_cross(df: pd.DataFrame, col: str) -> pd.DataFrame:
        if col not in df.columns:
            return _empty_df(["BUS_ASC_NAME", col, "count"])
        result = (
            df.groupby([df["BUS_ASC_NAME"], df[col].astype(str)], dropna=False)
            .size()
            .reset_index(name="count")
        )
        result.columns = ["BUS_ASC_NAME", col, "count"]
        return result

    # -- Module 7: Duration Benchmarking --------------------------------------

    def _analyze_duration_benchmarking(self) -> dict:
        _bench_cols = [
            "WATER_DEPTH_CLASS",
            "RIG_TYPE",
            "mean_days",
            "p25",
            "p50",
            "p75",
            "count",
        ]
        empty = {
            "by_depth_and_type": _empty_df(_bench_cols),
            "quartiles": _empty_df(["quartile", "min_days", "max_days"]),
        }
        if not {"DRILLING_DAYS", "ACTIVITY_CATEGORY"}.issubset(self._df.columns):
            return empty
        mask = self._df["DRILLING_DAYS"].notna() & (
            self._df["ACTIVITY_CATEGORY"].astype(str) == "drilling"
        )
        sub = self._df.loc[mask]
        if sub.empty:
            return empty
        return {
            "by_depth_and_type": self._bench_by_group(sub),
            "quartiles": self._quartile_boundaries(sub["DRILLING_DAYS"]),
        }

    @staticmethod
    def _bench_by_group(df: pd.DataFrame) -> pd.DataFrame:
        cols_out = [
            "WATER_DEPTH_CLASS",
            "RIG_TYPE",
            "mean_days",
            "p25",
            "p50",
            "p75",
            "count",
        ]
        if not {"WATER_DEPTH_CLASS", "RIG_TYPE"}.issubset(df.columns):
            return _empty_df(cols_out)
        grp = df.groupby(
            [df["WATER_DEPTH_CLASS"].astype(str), df["RIG_TYPE"].astype(str)],
            dropna=False,
        )["DRILLING_DAYS"]
        result = grp.agg(
            mean_days="mean",
            p25=lambda x: float(np.nanpercentile(x, 25)),
            p50="median",
            p75=lambda x: float(np.nanpercentile(x, 75)),
            count="count",
        ).reset_index()
        result.columns = cols_out
        return result

    @staticmethod
    def _quartile_boundaries(days: pd.Series) -> pd.DataFrame:
        if days.empty:
            return _empty_df(["quartile", "min_days", "max_days"])
        q25 = float(np.nanpercentile(days, 25))
        q50 = float(np.nanpercentile(days, 50))
        q75 = float(np.nanpercentile(days, 75))
        return pd.DataFrame(
            {
                "quartile": ["Q1", "Q2", "Q3", "Q4"],
                "min_days": [float(days.min()), q25, q50, q75],
                "max_days": [q25, q50, q75, float(days.max())],
            }
        )
