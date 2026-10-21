# ABOUTME: Late-life asset identification from production decline data.
# ABOUTME: Flags fields with >80% decline over 5 years or 12+ months idle.

"""Late-life asset identification for offshore fields.

Analyses historical production DataFrames to identify fields entering
or past the late-life phase, based on production decline and idle period
thresholds.
"""

from dataclasses import dataclass
from math import isfinite

import pandas as pd

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

_DECLINE_THRESHOLD_PCT = 80.0  # flag if production fell by this much over 5 yr
_IDLE_THRESHOLD_MONTHS = 12  # flag if idle (near-zero) for this many months
_NEAR_ZERO_BOPD = 10.0  # bopd considered "idle"
_CESSATION_LOOKBACK_YEARS = 5  # how many years of history to assess decline


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class LateLifeAssessment:
    """Result of late-life assessment for a single field."""

    field_name: str
    region: str
    peak_production_bopd: float | None
    current_production_bopd: float | None
    decline_pct_5yr: float | None  # % decline over last 5 years
    months_idle: int | None  # None if the final observation is unknown
    late_life_flag: bool
    trigger: str  # "decline_>80pct" | "idle_>12mo" | "both" | "none"
    estimated_cessation_year: int | None  # None if unknown; 0 if not applicable
    production_data_status: str = "available"  # or "unknown_final_month"


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _compute_decline_pct(prod_df: pd.DataFrame, lookback_years: int) -> float | None:
    """Compute percentage decline over *lookback_years* years.

    Args:
        prod_df: DataFrame with columns year, month, oil_bbl (monthly).
        lookback_years: Number of years to look back.

    Returns:
        Decline percentage (0-100+). Positive means production fell.
    """
    if prod_df.empty:
        return 0.0

    df = prod_df.sort_values(["year", "month"]).copy()
    # Identify the most recent year-month pair
    max_year = df["year"].max()
    recent_year_start = max_year - lookback_years

    past_mask = df["year"] <= recent_year_start
    recent_mask = df["year"] == max_year

    past_rows = df[past_mask]
    recent_rows = df[recent_mask]

    if past_rows.empty or recent_rows.empty:
        return 0.0

    past_avg = past_rows["oil_bbl"].mean() / 30.0  # convert monthly bbl → bopd
    recent_avg = recent_rows["oil_bbl"].mean() / 30.0

    if (
        pd.isna(past_avg)
        or pd.isna(recent_avg)
        or not isfinite(past_avg)
        or not isfinite(recent_avg)
    ):
        return None
    if past_avg <= 0:
        return 0.0

    decline_pct = (past_avg - recent_avg) / past_avg * 100.0
    return max(0.0, decline_pct)


def _compute_consecutive_idle_months(prod_df: pd.DataFrame) -> int | None:
    """Count consecutive months at the tail of the production history
    where production is below the near-zero threshold.

    Args:
        prod_df: DataFrame with columns year, month, oil_bbl.

    Returns:
        Number of consecutive idle rows at the end of the series, or None
        if the final production observation is missing or non-finite. Calendar
        gaps and duplicate dates are not resolved by this row-based screen.
    """
    if prod_df.empty:
        return 0

    df = prod_df.sort_values(["year", "month"]).copy()
    monthly_bopd = df["oil_bbl"] / 30.0

    final_value = monthly_bopd.iloc[-1]
    if pd.isna(final_value) or not isfinite(float(final_value)):
        return None

    idle_count = 0
    for val in reversed(monthly_bopd.tolist()):
        if pd.isna(val) or not isfinite(float(val)):
            break
        if val <= _NEAR_ZERO_BOPD:
            idle_count += 1
        else:
            break
    return idle_count


def _estimate_cessation_year(
    prod_df: pd.DataFrame,
    current_bopd: float | None,
    decline_pct_5yr: float | None,
) -> int | None:
    """Rough extrapolation of when production might cease.

    Uses the 5-year decline rate to project forward.  Returns 0 if
    production is already zero or no meaningful decline detected.

    Args:
        prod_df: Historical production DataFrame.
        current_bopd: Current production in bopd.
        decline_pct_5yr: Percentage decline over 5 years.

    Returns:
        Estimated cessation year (calendar year), 0 if not applicable, or
        None when a missing/non-finite rate prevents evaluation.
    """
    if (
        current_bopd is None
        or not isfinite(current_bopd)
        or decline_pct_5yr is None
        or not isfinite(decline_pct_5yr)
    ):
        return None
    if current_bopd <= _NEAR_ZERO_BOPD:
        return 0
    if decline_pct_5yr <= 0:
        return 0

    df = prod_df.sort_values(["year", "month"])
    latest_year = int(df["year"].max()) if not df.empty else 2025

    # Annual decline rate (approximate)
    annual_decline_rate = decline_pct_5yr / 100.0 / 5.0
    if annual_decline_rate <= 0:
        return 0

    # Years until production drops to near-zero (< 10 bopd)
    years_remaining = 0
    projected = current_bopd
    while projected > _NEAR_ZERO_BOPD and years_remaining < 50:
        projected *= 1.0 - annual_decline_rate
        years_remaining += 1

    return latest_year + years_remaining


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class LateLifeIdentifier:
    """Identifies late-life offshore fields from production history data.

    A field is flagged as late-life when one or more of these conditions hold:
    - Production declined more than 80% over the last 5 years.
    - Production has been idle (< 10 bopd) for 12+ consecutive months.
    """

    def assess_field(
        self,
        field_name: str,
        production_df: pd.DataFrame,
        region: str = "unknown",
    ) -> LateLifeAssessment:
        """Assess a single field for late-life indicators.

        Args:
            field_name: Identifier for the field.
            production_df: Monthly production history with columns:
                year (int), month (int), oil_bbl (float).
            region: Geographic region label (informational).

        Returns:
            LateLifeAssessment populated with computed metrics and flags.
            Missing/non-finite final oil_bbl gives None for current rate,
            months_idle and cessation year, with unknown_final_month status.
            An independently observed decline may still flag the field.
        """
        if production_df.empty:
            return LateLifeAssessment(
                field_name=field_name,
                region=region,
                peak_production_bopd=0.0,
                current_production_bopd=0.0,
                decline_pct_5yr=0.0,
                months_idle=0,
                late_life_flag=False,
                trigger="none",
                estimated_cessation_year=0,
            )

        df = production_df.sort_values(["year", "month"]).copy()
        monthly_bopd = df["oil_bbl"] / 30.0

        peak_value = monthly_bopd.max()
        peak_bopd = None if pd.isna(peak_value) else float(peak_value)
        final_value = monthly_bopd.iloc[-1]
        current_bopd = None if pd.isna(final_value) else float(final_value)
        if current_bopd is not None and not isfinite(current_bopd):
            current_bopd = None

        decline_pct = (
            _compute_decline_pct(df, _CESSATION_LOOKBACK_YEARS)
            if monthly_bopd.notna().any()
            else None
        )
        idle_months = _compute_consecutive_idle_months(df)

        high_decline = decline_pct is not None and decline_pct >= _DECLINE_THRESHOLD_PCT
        long_idle = idle_months is not None and idle_months >= _IDLE_THRESHOLD_MONTHS

        if high_decline and long_idle:
            trigger = "both"
            late_life_flag = True
        elif high_decline:
            trigger = "decline_>80pct"
            late_life_flag = True
        elif long_idle:
            trigger = "idle_>12mo"
            late_life_flag = True
        else:
            trigger = "none"
            late_life_flag = False

        cessation_year = _estimate_cessation_year(df, current_bopd, decline_pct)

        return LateLifeAssessment(
            field_name=field_name,
            region=region,
            peak_production_bopd=(
                round(peak_bopd, 2) if peak_bopd is not None else None
            ),
            current_production_bopd=(
                round(current_bopd, 2) if current_bopd is not None else None
            ),
            decline_pct_5yr=(
                round(decline_pct, 2) if decline_pct is not None else None
            ),
            months_idle=idle_months,
            late_life_flag=late_life_flag,
            trigger=trigger,
            estimated_cessation_year=cessation_year,
            production_data_status=(
                "available" if current_bopd is not None else "unknown_final_month"
            ),
        )

    def screen_portfolio(
        self,
        fields: dict[str, pd.DataFrame],
        region: str = "unknown",
    ) -> list[LateLifeAssessment]:
        """Screen a portfolio of fields for late-life indicators.

        Args:
            fields: Mapping of field_name to production DataFrame.
            region: Default region label applied to all fields.

        Returns:
            List of LateLifeAssessment, one per field.
        """
        return [self.assess_field(name, df, region) for name, df in fields.items()]

    def late_life_fields(
        self, assessments: list[LateLifeAssessment]
    ) -> list[LateLifeAssessment]:
        """Filter assessments to return only fields flagged as late-life.

        Args:
            assessments: List of LateLifeAssessment objects.

        Returns:
            Subset where late_life_flag is True.
        """
        return [a for a in assessments if a.late_life_flag]
