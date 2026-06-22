"""All-Fields Production Runner for BSEE data.

Aggregates production data across all BSEE fields, resolves field names,
classifies geological eras, and optionally runs financial analysis for
Tier 2 (lower tertiary) fields.
"""

import logging
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Unit conversions
_BBL_TO_MMBBL = 1e-6
_MCF_TO_BCF = 1e-6


class AllFieldsRunner:
    """Orchestrates all-field production analysis.

    Tier 1: All fields get production aggregation + geological era + names.
    Tier 2: Lower tertiary fields additionally get financial metrics.
    """

    def __init__(self, field_resolver, era_classifier):
        self._field_resolver = field_resolver
        self._era_classifier = era_classifier

    def run(
        self,
        production_data: pd.DataFrame,
        water_depth_data: Optional[pd.DataFrame] = None,
        field_water_depth: Optional[dict] = None,
        latest_year: Optional[int] = None,
    ) -> pd.DataFrame:
        """Run all-fields analysis.

        Args:
            production_data: DataFrame with columns including FIELD_NAME_CODE,
                LEASE_NUMBER, API_WELL_NUMBER, PROD_YEAR, MON_O_PROD_VOL,
                MON_G_PROD_VOL, MON_WTR_PROD_VOL, DAYS_ON_PROD, OPERATOR.
            water_depth_data: Optional DataFrame with LEASE_NUMBER, MAX_WTR_DPTH
                (legacy lease-based water-depth path).
            field_water_depth: Optional ``{FIELD_CODE: avg_water_depth_ft}`` map.
                When provided it takes precedence over ``water_depth_data`` for
                fields it covers (the new field-level path).
            latest_year: Most recent PROD_YEAR in the dataset, used to flag
                STILL_PRODUCING.  Defaults to the max PROD_YEAR in the input.

        Returns:
            DataFrame with one row per field, sorted by CUM_OIL_MMBBL descending.
        """
        if production_data.empty:
            logger.warning("Empty production data — returning empty result")
            return self._empty_result()

        field_col = self._detect_field_column(production_data)
        if field_col is None:
            logger.error("No field code column found in production data")
            return self._empty_result()

        if latest_year is None:
            year_col = self._pick_col(production_data, ["PROD_YEAR", "PRODUCTION_DATE"])
            if year_col:
                years = pd.to_numeric(production_data[year_col], errors="coerce").dropna()
                latest_year = int(years.max()) if not years.empty else None

        # Group by field and compute production metrics
        rows = []
        for field_code, field_df in production_data.groupby(field_col):
            row = self._compute_field_production(
                str(field_code), field_df, latest_year
            )

            # Resolve field name
            row["FIELD_NAME"] = self._field_resolver.resolve(str(field_code))

            # Classify geological era
            well_apis = field_df["API_WELL_NUMBER"].astype(str).unique().tolist()
            row["GEOLOGICAL_ERA"] = self._era_classifier.classify_field(well_apis)

            # Join water depth: field-level map wins, else legacy lease path.
            wd = None
            if field_water_depth is not None:
                wd = field_water_depth.get(str(field_code))
            if wd is None:
                wd = self._get_avg_water_depth(field_df, water_depth_data)
            row["WATER_DEPTH_AVG"] = wd

            # Tier 2 financial placeholders
            row["NPV10_MM_USD"] = None
            row["IRR_PCT"] = None
            row["PAYBACK_YRS"] = None

            rows.append(row)

        result = pd.DataFrame(rows)
        result = result.sort_values("CUM_OIL_MMBBL", ascending=False).reset_index(
            drop=True
        )

        logger.info("Analyzed %d fields", len(result))
        return result

    def _compute_field_production(
        self,
        field_code: str,
        field_df: pd.DataFrame,
        latest_year: Optional[int] = None,
    ) -> Dict:
        """Compute production + benchmarking metrics for a single field."""
        oil_col = self._pick_col(field_df, ["MON_O_PROD_VOL", "OIL_STB"])
        gas_col = self._pick_col(field_df, ["MON_G_PROD_VOL", "GAS_MCF"])
        water_col = self._pick_col(field_df, ["MON_WTR_PROD_VOL"])
        year_col = self._pick_col(field_df, ["PROD_YEAR", "PRODUCTION_DATE"])
        days_col = self._pick_col(field_df, ["DAYS_ON_PROD"])
        api_col = self._pick_col(field_df, ["API_WELL_NUMBER"])
        op_col = self._pick_col(field_df, ["OPERATOR", "SORT_NAME"])

        cum_oil = field_df[oil_col].sum() if oil_col else 0.0
        cum_gas = field_df[gas_col].sum() if gas_col else 0.0
        cum_water = field_df[water_col].sum() if water_col else 0.0
        days_on_prod_sum = (
            pd.to_numeric(field_df[days_col], errors="coerce").sum()
            if days_col
            else 0.0
        )

        # Peak oil rate: max annual oil / 365
        peak_oil_bopd = 0.0
        if oil_col and year_col:
            annual = field_df.groupby(year_col)[oil_col].sum()
            if not annual.empty:
                peak_oil_bopd = annual.max() / 365.0

        # Well count
        well_count = field_df[api_col].nunique() if api_col else 0

        # Production year range
        first_prod = None
        last_prod = None
        if year_col:
            years = pd.to_numeric(field_df[year_col], errors="coerce").dropna()
            if not years.empty:
                first_prod = int(years.min())
                last_prod = int(years.max())

        # Operator concentration within the field.
        n_operators = None
        top_operator_share = None
        dominant_operator = None
        if op_col and oil_col:
            by_op = field_df.groupby(op_col)[oil_col].sum()
            by_op = by_op[by_op.index.astype(str).str.strip() != ""]
            if not by_op.empty:
                n_operators = int(by_op.shape[0])
                total = by_op.sum()
                dominant_operator = str(by_op.idxmax())
                if total > 0:
                    top_operator_share = round(float(by_op.max() / total), 4)

        # Production span (inclusive years).
        prod_span = None
        if first_prod is not None and last_prod is not None:
            prod_span = last_prod - first_prod + 1

        # Still-producing flag relative to the dataset's most recent year.
        still_producing = None
        if last_prod is not None and latest_year is not None:
            still_producing = bool(last_prod == latest_year)

        return {
            "FIELD_CODE": field_code,
            "WELL_COUNT": well_count,
            "FIRST_PRODUCTION": first_prod,
            "LAST_PRODUCTION": last_prod,
            "CUM_OIL_MMBBL": round(cum_oil * _BBL_TO_MMBBL, 3),
            "CUM_GAS_BCF": round(cum_gas * _MCF_TO_BCF, 3),
            "CUM_WATER_MMBBL": round(cum_water * _BBL_TO_MMBBL, 3),
            "PEAK_OIL_BOPD": round(peak_oil_bopd, 0),
            "REC_PER_WELL_MMBBL": (
                round(cum_oil * _BBL_TO_MMBBL / well_count, 4)
                if well_count
                else None
            ),
            "AVG_BOPD_PER_WELL": (
                round(cum_oil / days_on_prod_sum, 1)
                if days_on_prod_sum
                else None
            ),
            "PROD_SPAN_YRS": prod_span,
            "WOR_CUM": round(cum_water / cum_oil, 3) if cum_oil else None,
            "PEAK_TO_CUM": (
                round(peak_oil_bopd * 365.0 / cum_oil, 4) if cum_oil else None
            ),
            "N_OPERATORS": n_operators,
            "TOP_OPERATOR_SHARE": top_operator_share,
            "DOMINANT_OPERATOR": dominant_operator,
            "STILL_PRODUCING": still_producing,
        }

    def _detect_field_column(self, df: pd.DataFrame) -> Optional[str]:
        """Detect which column contains the field code."""
        candidates = ["FIELD_NAME_CODE", "BOTM_FLD_NAME_CD", "FIELD_CODE"]
        for col in candidates:
            if col in df.columns:
                return col
        return None

    def _pick_col(self, df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
        """Pick the first matching column from candidates."""
        for col in candidates:
            if col in df.columns:
                return col
        return None

    def _get_avg_water_depth(
        self,
        field_df: pd.DataFrame,
        water_depth_data: Optional[pd.DataFrame],
    ) -> Optional[float]:
        """Get average water depth for leases in this field."""
        if water_depth_data is None or water_depth_data.empty:
            return None

        if "LEASE_NUMBER" not in field_df.columns:
            return None

        leases = field_df["LEASE_NUMBER"].unique()
        matched = water_depth_data[water_depth_data["LEASE_NUMBER"].isin(leases)]

        if matched.empty:
            return None

        return round(matched["MAX_WTR_DPTH"].mean(), 0)

    def _empty_result(self) -> pd.DataFrame:
        """Return an empty DataFrame with the expected schema."""
        return pd.DataFrame(
            columns=[
                "FIELD_CODE",
                "FIELD_NAME",
                "GEOLOGICAL_ERA",
                "WATER_DEPTH_AVG",
                "WELL_COUNT",
                "FIRST_PRODUCTION",
                "LAST_PRODUCTION",
                "CUM_OIL_MMBBL",
                "CUM_GAS_BCF",
                "CUM_WATER_MMBBL",
                "PEAK_OIL_BOPD",
                "REC_PER_WELL_MMBBL",
                "AVG_BOPD_PER_WELL",
                "PROD_SPAN_YRS",
                "WOR_CUM",
                "PEAK_TO_CUM",
                "N_OPERATORS",
                "TOP_OPERATOR_SHARE",
                "DOMINANT_OPERATOR",
                "STILL_PRODUCING",
                "NPV10_MM_USD",
                "IRR_PCT",
                "PAYBACK_YRS",
            ]
        )
