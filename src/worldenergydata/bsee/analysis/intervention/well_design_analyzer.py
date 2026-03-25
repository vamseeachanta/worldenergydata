"""Well design analyzer for casing, completions, geology, and BOP data (WRK-116 Phase 6).

Analyzes well design across 5 modules from BSEE source CSVs:
casing program, casing grade analysis, completion analysis,
geology analysis, and pressure envelope.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _empty_df(cols: list[str]) -> pd.DataFrame:
    """Return an empty DataFrame with the given columns."""
    return pd.DataFrame(columns=cols)


class WellDesignAnalyzer:
    """Analyze well design data -- casing program, completions, geology, BOP."""

    def __init__(
        self,
        tubulars_df: pd.DataFrame | None = None,
        perforations_df: pd.DataFrame | None = None,
        geology_df: pd.DataFrame | None = None,
        hc_intervals_df: pd.DataFrame | None = None,
        bop_df: pd.DataFrame | None = None,
    ) -> None:
        self._tubulars = tubulars_df.copy() if tubulars_df is not None else None
        self._perforations = perforations_df.copy() if perforations_df is not None else None
        self._geology = geology_df.copy() if geology_df is not None else None
        self._hc_intervals = hc_intervals_df.copy() if hc_intervals_df is not None else None
        self._bop = bop_df.copy() if bop_df is not None else None

    def analyze(self) -> dict:
        """Run all 5 analysis modules and return combined results."""
        return {
            "casing_program": self._analyze_casing_program(),
            "casing_grade_analysis": self._analyze_casing_grade(),
            "completion_analysis": self._analyze_completions(),
            "geology_analysis": self._analyze_geology(),
            "pressure_envelope": self._analyze_pressure_envelope(),
        }

    # -- Module 1: Casing Program ----------------------------------------------

    def _analyze_casing_program(self) -> dict:
        """Summarize the casing program from tubulars data."""
        if self._tubulars is None or self._tubulars.empty:
            return {
                "total_casing_records": 0,
                "unique_wells": 0,
                "by_interval_type": _empty_df(["CSNG_INTV_TYPE_CD", "count"]),
                "hole_size_distribution": _empty_df(["CSNG_HOLE_SIZE", "count"]),
                "casing_size_distribution": _empty_df(["CASING_SIZE", "count"]),
                "grade_distribution": _empty_df(["CASING_GRADE", "count"]),
                "depth_stats": {"mean_setting_depth": 0.0, "max_setting_depth": 0.0},
            }

        df = self._tubulars

        by_interval = (
            df.groupby("CSNG_INTV_TYPE_CD", as_index=False)
            .size()
            .rename(columns={"size": "count"})
        )

        hole_sizes = (
            df.groupby("CSNG_HOLE_SIZE", as_index=False)
            .size()
            .rename(columns={"size": "count"})
            .sort_values("CSNG_HOLE_SIZE")
            .reset_index(drop=True)
        )

        casing_sizes = (
            df.groupby("CASING_SIZE", as_index=False)
            .size()
            .rename(columns={"size": "count"})
            .sort_values("CASING_SIZE")
            .reset_index(drop=True)
        )

        grades = (
            df.groupby("CASING_GRADE", as_index=False)
            .size()
            .rename(columns={"size": "count"})
            .sort_values("count", ascending=False)
            .reset_index(drop=True)
        )

        depth_col = "CSNG_SETTING_BOTM_MD"
        valid_depths = df[depth_col].dropna()

        return {
            "total_casing_records": len(df),
            "unique_wells": df["API_WELL_NUMBER"].nunique(),
            "by_interval_type": by_interval,
            "hole_size_distribution": hole_sizes,
            "casing_size_distribution": casing_sizes,
            "grade_distribution": grades,
            "depth_stats": {
                "mean_setting_depth": float(valid_depths.mean()) if len(valid_depths) else 0.0,
                "max_setting_depth": float(valid_depths.max()) if len(valid_depths) else 0.0,
            },
        }

    # -- Module 2: Casing Grade Analysis ---------------------------------------

    def _analyze_casing_grade(self) -> dict:
        """Deep-dive analysis by casing grade."""
        if self._tubulars is None or self._tubulars.empty:
            return {
                "grades_found": [],
                "most_common_grade": "",
                "by_grade": _empty_df(
                    ["CASING_GRADE", "count", "avg_weight", "avg_setting_depth"]
                ),
            }

        df = self._tubulars
        grades_found = sorted(df["CASING_GRADE"].dropna().unique().tolist())

        by_grade = (
            df.groupby("CASING_GRADE", as_index=False)
            .agg(
                count=("CASING_GRADE", "size"),
                avg_weight=("CASING_WEIGHT", "mean"),
                avg_setting_depth=("CSNG_SETTING_BOTM_MD", "mean"),
            )
            .sort_values("count", ascending=False)
            .reset_index(drop=True)
        )

        most_common = by_grade.iloc[0]["CASING_GRADE"] if len(by_grade) else ""

        return {
            "grades_found": grades_found,
            "most_common_grade": most_common,
            "by_grade": by_grade,
        }

    # -- Module 3: Completion Analysis -----------------------------------------

    def _analyze_completions(self) -> dict:
        """Analyze perforation/completion data."""
        if self._perforations is None or self._perforations.empty:
            return {
                "total_perforations": 0,
                "unique_wells": 0,
                "depth_stats": {
                    "mean_perf_top": 0.0,
                    "mean_perf_base": 0.0,
                    "max_depth": 0.0,
                },
                "by_well": _empty_df(
                    ["API_WELL_NUMBER", "perf_count", "min_top", "max_base", "interval_ft"]
                ),
            }

        df = self._perforations
        top_col = "PERF_TOP_MD"
        base_col = "PERF_BASE_MD"

        by_well = (
            df.groupby("API_WELL_NUMBER", as_index=False)
            .agg(
                perf_count=("API_WELL_NUMBER", "size"),
                min_top=(top_col, "min"),
                max_base=(base_col, "max"),
            )
        )
        by_well["interval_ft"] = by_well["max_base"] - by_well["min_top"]

        return {
            "total_perforations": len(df),
            "unique_wells": df["API_WELL_NUMBER"].nunique(),
            "depth_stats": {
                "mean_perf_top": float(df[top_col].mean()),
                "mean_perf_base": float(df[base_col].mean()),
                "max_depth": float(df[base_col].max()),
            },
            "by_well": by_well,
        }

    # -- Module 4: Geology Analysis --------------------------------------------

    def _analyze_geology(self) -> dict:
        """Analyze geological markers and hydrocarbon intervals."""
        if self._geology is None or self._geology.empty:
            return {
                "total_markers": 0,
                "unique_formations": 0,
                "formation_distribution": _empty_df(
                    ["GEO_MARKER_NAME", "count", "mean_depth"]
                ),
                "hydrocarbon_summary": None,
            }

        df = self._geology

        formation_dist = (
            df.groupby("GEO_MARKER_NAME", as_index=False)
            .agg(
                count=("GEO_MARKER_NAME", "size"),
                mean_depth=("TOP_MD", "mean"),
            )
            .sort_values("count", ascending=False)
            .reset_index(drop=True)
        )

        hc_summary = None
        if self._hc_intervals is not None and not self._hc_intervals.empty:
            hc_df = self._hc_intervals
            by_type = (
                hc_df["HYDROCARBON_TYPE_CD"]
                .value_counts()
                .to_dict()
            )
            hc_summary = {
                "total_intervals": len(hc_df),
                "by_type": by_type,
            }

        return {
            "total_markers": len(df),
            "unique_formations": df["GEO_MARKER_NAME"].nunique(),
            "formation_distribution": formation_dist,
            "hydrocarbon_summary": hc_summary,
        }

    # -- Module 5: Pressure Envelope -------------------------------------------

    def _analyze_pressure_envelope(self) -> dict:
        """Analyze BOP test pressure data."""
        if self._bop is None or self._bop.empty:
            return {
                "total_tests": 0,
                "ram_pressure_stats": {"mean": 0.0, "max": 0.0},
                "annular_pressure_stats": {"mean": 0.0, "max": 0.0},
            }

        df = self._bop
        ram_col = "RAM_TST_PRSS"
        ann_col = "ANNULAR_TST_PRSS"

        ram_valid = df[ram_col].dropna()
        ann_valid = df[ann_col].dropna()

        return {
            "total_tests": len(df),
            "ram_pressure_stats": {
                "mean": float(ram_valid.mean()) if len(ram_valid) else 0.0,
                "max": float(ram_valid.max()) if len(ram_valid) else 0.0,
            },
            "annular_pressure_stats": {
                "mean": float(ann_valid.mean()) if len(ann_valid) else 0.0,
                "max": float(ann_valid.max()) if len(ann_valid) else 0.0,
            },
        }
