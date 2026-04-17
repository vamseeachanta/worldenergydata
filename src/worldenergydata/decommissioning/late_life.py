# ABOUTME: Late-life asset identification from production decline data.
# ABOUTME: Flags fields with >80% decline over 5 years or 12+ months idle.

"""Late-life asset identification for offshore fields.

Analyses historical production DataFrames to identify fields entering
or past the late-life phase, based on production decline and idle period
thresholds.
"""

from dataclasses import dataclass
from typing import Optional

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
    peak_production_bopd: float
    current_production_bopd: float
    decline_pct_5yr: float  # % decline over last 5 years
    months_idle: int  # consecutive months of near-zero production
    late_life_flag: bool
    trigger: str  # "decline_>80pct" | "idle_>12mo" | "both" | "none"
    estimated_cessation_year: int  # 0 if not applicable


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _compute_decline_pct(prod_df: pd.DataFrame, lookback_years: int) -> float:
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

    if past_avg <= 0:
        return 0.0

    decline_pct = (past_avg - recent_avg) / past_avg * 100.0
    return max(0.0, decline_pct)


def _compute_consecutive_idle_months(prod_df: pd.DataFrame) -> int:
    """Count consecutive months at the tail of the production history
    where production is below the near-zero threshold.

    Args:
        prod_df: DataFrame with columns year, month, oil_bbl.

    Returns:
        Number of consecutive idle months at the end of the series.
    """
    if prod_df.empty:
        return 0

    df = prod_df.sort_values(["year", "month"]).copy()
    monthly_bopd = df["oil_bbl"] / 30.0

    idle_count = 0
    for val in reversed(monthly_bopd.tolist()):
        if val <= _NEAR_ZERO_BOPD:
            idle_count += 1
        else:
            break
    return idle_count


def _estimate_cessation_year(
    prod_df: pd.DataFrame,
    current_bopd: float,
    decline_pct_5yr: float,
) -> int:
    """Rough extrapolation of when production might cease.

    Uses the 5-year decline rate to project forward.  Returns 0 if
    production is already zero or no meaningful decline detected.

    Args:
        prod_df: Historical production DataFrame.
        current_bopd: Current production in bopd.
        decline_pct_5yr: Percentage decline over 5 years.

    Returns:
        Estimated cessation year (calendar year), or 0 if not applicable.
    """
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

        peak_bopd = float(monthly_bopd.max())
        current_bopd = float(monthly_bopd.iloc[-1])

        decline_pct = _compute_decline_pct(df, _CESSATION_LOOKBACK_YEARS)
        idle_months = _compute_consecutive_idle_months(df)

        high_decline = decline_pct >= _DECLINE_THRESHOLD_PCT
        long_idle = idle_months >= _IDLE_THRESHOLD_MONTHS

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
            peak_production_bopd=round(peak_bopd, 2),
            current_production_bopd=round(current_bopd, 2),
            decline_pct_5yr=round(decline_pct, 2),
            months_idle=idle_months,
            late_life_flag=late_life_flag,
            trigger=trigger,
            estimated_cessation_year=cessation_year,
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
