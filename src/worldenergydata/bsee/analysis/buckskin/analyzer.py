"""Buckskin field analyzer — production, wellbore, and benchmark analytics.

Receives the dict output of ``BuckskinExtractor.extract_all()`` and computes
production summaries, wellbore inventories, drilling timelines, WAR activity
summaries, operator histories, decline curve analysis, and benchmark
validations for the Buckskin development (KC 785/828/829/830/871/872).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import pandas as pd

from .buckskin_config import BUCKSKIN

logger = logging.getLogger(__name__)

# Unit conversions
_BBL_TO_MMBBL = 1e-6
_MCF_TO_BCF = 1e-6


def _pick_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Return the first column name present in *df*, or ``None``."""
    for col in candidates:
        if col in df.columns:
            return col
    return None


class BuckskinAnalyzer:
    """Field-level analytics for the Buckskin development.

    Parameters
    ----------
    data:
        Dict keyed by dataset name (``"production"``, ``"wells"``,
        ``"war_activity"``, ``"leases"``, ``"completions"``), each value
        a :class:`~pandas.DataFrame`.
    """

    def __init__(self, data: dict[str, pd.DataFrame]) -> None:
        self._data = data

    # ------------------------------------------------------------------
    # Production
    # ------------------------------------------------------------------

    def production_summary(self) -> dict[str, Any]:
        """Return cumulative production summary with per-block breakdown."""
        df = self._data.get("production", pd.DataFrame())

        if df.empty:
            return self._empty_production_summary()

        oil_col = _pick_col(df, ["MON_O_PROD_VOL", "OIL_STB"])
        gas_col = _pick_col(df, ["MON_G_PROD_VOL", "GAS_MCF"])
        water_col = _pick_col(df, ["MON_WTR_PROD_VOL", "WTR_STB"])
        year_col = _pick_col(df, ["PROD_YEAR", "YEAR"])
        well_col = _pick_col(df, ["API_WELL_NUMBER", "API"])
        block_col = _pick_col(df, ["BOTM_BLOCK_NUM", "BLOCK_NUM"])

        cum_oil = float(df[oil_col].sum()) if oil_col else 0.0
        cum_gas = float(df[gas_col].sum()) if gas_col else 0.0
        cum_water = float(df[water_col].sum()) if water_col else 0.0

        # Peak annual rate
        peak_bopd = 0.0
        if oil_col and year_col:
            annual = df.groupby(year_col)[oil_col].sum()
            peak_bopd = float(annual.max()) / 365.0

        # Well count
        well_count = int(df[well_col].nunique()) if well_col else 0

        # Year range
        first_year: int | None = None
        last_year: int | None = None
        if year_col:
            first_year = int(df[year_col].min())
            last_year = int(df[year_col].max())

        # Per-block breakdown
        per_block: dict[int, dict[str, float]] = {}
        if block_col:
            for block_num, block_df in df.groupby(block_col):
                per_block[int(block_num)] = {
                    "oil_bbl": float(block_df[oil_col].sum()) if oil_col else 0.0,
                    "gas_mcf": float(block_df[gas_col].sum()) if gas_col else 0.0,
                    "water_bbl": float(block_df[water_col].sum()) if water_col else 0.0,
                }

        return {
            "cumulative_oil_mmbbl": cum_oil * _BBL_TO_MMBBL,
            "cumulative_gas_bcf": cum_gas * _MCF_TO_BCF,
            "cumulative_water_mmbbl": cum_water * _BBL_TO_MMBBL,
            "peak_oil_rate_bopd": peak_bopd,
            "producing_well_count": well_count,
            "first_production_year": first_year,
            "last_production_year": last_year,
            "per_block": per_block,
        }

    @staticmethod
    def _empty_production_summary() -> dict[str, Any]:
        return {
            "cumulative_oil_mmbbl": 0.0,
            "cumulative_gas_bcf": 0.0,
            "cumulative_water_mmbbl": 0.0,
            "peak_oil_rate_bopd": 0.0,
            "producing_well_count": 0,
            "first_production_year": None,
            "last_production_year": None,
            "per_block": {},
        }

    # ------------------------------------------------------------------
    # Wellbore inventory
    # ------------------------------------------------------------------

    def wellbore_inventory(self) -> dict[str, Any]:
        """Return wellbore inventory with type classification per block."""
        df = self._data.get("wells", pd.DataFrame())

        if df.empty:
            return {
                "total_wells": 0,
                "development_count": 0,
                "exploration_count": 0,
                "per_block": {},
            }

        type_col = _pick_col(df, ["WELL_TYPE_CODE", "TYPE_CODE"])
        block_col = _pick_col(df, ["BOTM_BLOCK_NUM", "BLOCK_NUM"])

        dev_count = 0
        exp_count = 0
        if type_col:
            dev_count = int((df[type_col] == "D").sum())
            exp_count = int((df[type_col] == "E").sum())

        per_block: dict[int, int] = {}
        if block_col:
            counts = df.groupby(block_col).size()
            per_block = {int(k): int(v) for k, v in counts.items()}

        return {
            "total_wells": len(df),
            "development_count": dev_count,
            "exploration_count": exp_count,
            "per_block": per_block,
        }

    # ------------------------------------------------------------------
    # Drilling timeline
    # ------------------------------------------------------------------

    def drilling_timeline(self) -> pd.DataFrame:
        """Return wells sorted chronologically by spud date."""
        df = self._data.get("wells", pd.DataFrame())

        if df.empty:
            return pd.DataFrame()

        spud_col = _pick_col(df, ["WELL_SPUD_DATE", "SPUD_DATE"])
        if spud_col is None:
            logger.warning("No spud-date column found; returning unsorted wells")
            return df.copy()

        result = df.copy()
        result[spud_col] = pd.to_datetime(result[spud_col])
        return result.sort_values(spud_col).reset_index(drop=True)

    # ------------------------------------------------------------------
    # WAR activity summary
    # ------------------------------------------------------------------

    def war_activity_summary(self) -> dict[str, int]:
        """Return WAR activity counts keyed by activity code."""
        df = self._data.get("war_activity", pd.DataFrame())

        if df.empty:
            return {}

        code_col = _pick_col(df, ["WAR_ACTIVITY_CODE", "ACTIVITY_CODE"])
        if code_col is None:
            return {}

        counts = df[code_col].value_counts()
        return {str(k): int(v) for k, v in counts.items()}

    # ------------------------------------------------------------------
    # Operator history
    # ------------------------------------------------------------------

    def operator_history(self) -> list[dict[str, Any]]:
        """Extract operator history from WAR and lease data.

        Returns a list of dicts with operator information. Returns an
        empty list when no relevant data is available.
        """
        war_df = self._data.get("war_activity", pd.DataFrame())

        if war_df.empty:
            return []

        operator_col = _pick_col(war_df, ["OPERATOR_NAME", "OPERATOR"])
        if operator_col is None:
            return []

        records: list[dict[str, Any]] = []
        for name, group in war_df.groupby(operator_col):
            records.append(
                {
                    "operator_name": str(name),
                    "record_count": len(group),
                }
            )
        return records

    # ------------------------------------------------------------------
    # Benchmark validation
    # ------------------------------------------------------------------

    def validate_benchmarks(self) -> dict[str, Any]:
        """Validate production data against known Buckskin benchmarks."""
        prod = self.production_summary()

        first_year = prod["first_production_year"]
        well_count = prod["producing_well_count"]

        return {
            "first_oil_year": first_year,
            "producing_well_count": well_count,
            "expected_first_oil_year": BUCKSKIN.expected_first_oil_year,
            "expected_peak_rate_bopd": BUCKSKIN.expected_peak_rate_bopd,
            "first_oil_year_match": first_year == BUCKSKIN.expected_first_oil_year,
            "geological_era": BUCKSKIN.geological_era,
        }

    # ------------------------------------------------------------------
    # Well count over time
    # ------------------------------------------------------------------

    def well_count_by_year(self) -> pd.DataFrame:
        """Return cumulative well count by spud year.

        Used for the "well count over time" visualization.
        """
        df = self._data.get("wells", pd.DataFrame())
        if df.empty:
            return pd.DataFrame(columns=["year", "cumulative_wells"])

        spud_col = _pick_col(df, ["WELL_SPUD_DATE", "SPUD_DATE"])
        if spud_col is None:
            return pd.DataFrame(columns=["year", "cumulative_wells"])

        dates = pd.to_datetime(df[spud_col], errors="coerce")
        years = dates.dt.year.dropna().astype(int)
        if years.empty:
            return pd.DataFrame(columns=["year", "cumulative_wells"])

        counts = years.value_counts().sort_index()
        cum = counts.cumsum()
        return pd.DataFrame({
            "year": cum.index,
            "cumulative_wells": cum.values,
        })

    # ------------------------------------------------------------------
    # BOEM lease mapping
    # ------------------------------------------------------------------

    def boem_lease_table(self) -> pd.DataFrame:
        """Return BOEM lease-to-block mapping as a DataFrame."""
        rows = []
        for ocs_id, blocks in BUCKSKIN.boem_leases.items():
            rows.append({"BOEM_OCS_Lease": ocs_id, "Blocks": blocks})
        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Decline curve analysis
    # ------------------------------------------------------------------

    def decline_curve_analysis(
        self,
        product: str = "oil",
        forecast_periods: int = 10,
    ) -> Optional[Dict[str, Any]]:
        """Run decline curve analysis on Buckskin production data.

        Returns a dict with keys: comparison, forecast, eur, or None if
        the decline curve modules are not available or data is insufficient.
        """
        try:
            from worldenergydata.bsee.analysis.forecasting.bsee_decline_adapter import (
                BseeDeclineAdapter,
            )
            from worldenergydata.bsee.analysis.forecasting.decline_analysis import (
                DeclineAnalysis,
            )
        except ImportError:
            logger.warning("Decline curve modules not available")
            return None

        df = self._data.get("production", pd.DataFrame())
        if df.empty:
            return None

        adapter = BseeDeclineAdapter(min_points=5)
        try:
            ts = adapter.extract_from_dataframe(
                df, product=product, label=BUCKSKIN.field_name,
            )
        except (ValueError, KeyError) as exc:
            logger.warning("Cannot extract decline data: %s", exc)
            return None

        if ts is None:
            return None

        analysis = DeclineAnalysis(
            forecast_periods=forecast_periods, economic_limit=100.0,
        )
        try:
            comparison = analysis.fit_all_models(ts)
            forecast = analysis.forecast(comparison)
            eur = analysis.calculate_eur(comparison)
        except (ValueError, RuntimeError) as exc:
            logger.warning("Decline curve fitting failed: %s", exc)
            return None

        return {
            "time_series": ts,
            "comparison": comparison,
            "forecast": forecast,
            "eur": eur,
        }
