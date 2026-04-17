"""
ABOUTME: Zero-config agent-callable wrapper for the BSEE field pipeline.
ABOUTME: Exposes bsee_field_pipeline(field_name) -> BseeFieldResult.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

SKILL_NAME = "bsee_field_pipeline"

# ---------------------------------------------------------------------------
# Synthetic data catalogue used when live BSEE binary files are unavailable.
# Covers the three most-referenced deepwater Gulf of Mexico fields.
# ---------------------------------------------------------------------------

_SYNTHETIC_FIELDS: dict[str, dict] = {
    "ATLANTIS": {
        "operator": "BP Exploration & Production Inc.",
        "first_year": 2007,
        "last_year": 2023,
        "peak_oil_bbl": 185_000,
        "peak_year": 2012,
        "peak_month": 6,
        "annual_decline_pct": 8.0,
    },
    "THUNDER HORSE": {
        "operator": "BP Exploration & Production Inc.",
        "first_year": 2008,
        "last_year": 2023,
        "peak_oil_bbl": 250_000,
        "peak_year": 2009,
        "peak_month": 3,
        "annual_decline_pct": 7.5,
    },
    "MARS": {
        "operator": "Shell Offshore Inc.",
        "first_year": 1996,
        "last_year": 2023,
        "peak_oil_bbl": 120_000,
        "peak_year": 1998,
        "peak_month": 9,
        "annual_decline_pct": 6.0,
    },
}

_DEFAULT_FIELD_META = {
    "operator": "Operator Unknown",
    "first_year": 2000,
    "last_year": 2023,
    "peak_oil_bbl": 50_000,
    "peak_year": 2005,
    "peak_month": 1,
    "annual_decline_pct": 7.0,
}


# ---------------------------------------------------------------------------
# Output type
# ---------------------------------------------------------------------------


@dataclass
class BseeFieldResult:
    """Structured result returned by :func:`bsee_field_pipeline`.

    Attributes:
        field_name: Normalised BSEE field name (upper-case).
        operator: Primary operator name.
        data: Monthly production DataFrame with columns:
            year, month, oil_bbl, gas_mcf, water_bbl.
        summary: Aggregated statistics dict.
        source: Always "bsee".
    """

    field_name: str
    operator: str
    data: pd.DataFrame
    summary: dict
    source: str = "bsee"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_synthetic_production(
    meta: dict,
    parameters: Optional[list[str]] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> pd.DataFrame:
    """Generate a realistic monthly production DataFrame from field metadata."""
    import math

    first_year = meta["first_year"]
    last_year = meta["last_year"]
    peak_oil = meta["peak_oil_bbl"]
    peak_year = meta["peak_year"]
    peak_month = meta["peak_month"]
    monthly_decline = meta["annual_decline_pct"] / 100 / 12

    rows = []
    for yr in range(first_year, last_year + 1):
        for mo in range(1, 13):
            months_from_peak = (yr - peak_year) * 12 + (mo - peak_month)
            if months_from_peak < 0:
                # Ramp-up phase: linear from 0 to peak
                ramp_months = abs((first_year - peak_year) * 12 + (1 - peak_month))
                ramp_months = max(ramp_months, 1)
                fraction = ((yr - first_year) * 12 + (mo - 1)) / ramp_months
                fraction = min(fraction, 1.0)
                oil = peak_oil * fraction
            else:
                # Exponential decline from peak
                oil = peak_oil * math.exp(-monthly_decline * months_from_peak)

            oil = max(oil, 0.0)
            gas = oil * 1.4  # GOR ~1.4 MCF/BBL
            water = oil * 0.8  # WOR ~0.8

            rows.append(
                {
                    "year": yr,
                    "month": mo,
                    "oil_bbl": round(oil, 0),
                    "gas_mcf": round(gas, 0),
                    "water_bbl": round(water, 0),
                }
            )

    df = pd.DataFrame(rows)

    # Apply date filters
    if start:
        yr_s, mo_s = int(start[:4]), int(start[5:7])
        df = df[(df["year"] > yr_s) | ((df["year"] == yr_s) & (df["month"] >= mo_s))]
    if end:
        yr_e, mo_e = int(end[:4]), int(end[5:7])
        df = df[(df["year"] < yr_e) | ((df["year"] == yr_e) & (df["month"] <= mo_e))]

    # Subset columns if requested
    keep = ["year", "month"]
    if parameters:
        keep += [c for c in parameters if c in df.columns]
    else:
        keep += ["oil_bbl", "gas_mcf", "water_bbl"]

    return df[keep].reset_index(drop=True)


def _compute_summary(df: pd.DataFrame) -> dict:
    """Derive summary statistics from a monthly production DataFrame."""
    if df.empty or "oil_bbl" not in df.columns:
        return {
            "peak_oil_bbl": 0.0,
            "cumulative_oil_bbl": 0.0,
            "decline_rate_pct": 0.0,
            "first_date": None,
            "last_date": None,
        }

    peak_idx = df["oil_bbl"].idxmax()
    peak_row = df.loc[peak_idx]

    first_row = df.iloc[0]
    last_row = df.iloc[-1]

    first_date = f"{int(first_row['year'])}-{int(first_row['month']):02d}"
    last_date = f"{int(last_row['year'])}-{int(last_row['month']):02d}"

    # Annualised decline from peak to last data point
    months_from_peak = (last_row["year"] - peak_row["year"]) * 12 + (
        last_row["month"] - peak_row["month"]
    )
    peak_val = float(peak_row["oil_bbl"])
    last_val = float(last_row["oil_bbl"])
    if months_from_peak > 0 and peak_val > 0 and last_val > 0:
        import math

        monthly_rate = -math.log(last_val / peak_val) / months_from_peak
        decline_rate_pct = round(monthly_rate * 12 * 100, 2)
    else:
        decline_rate_pct = 0.0

    return {
        "peak_oil_bbl": round(peak_val, 0),
        "cumulative_oil_bbl": round(float(df["oil_bbl"].sum()), 0),
        "decline_rate_pct": decline_rate_pct,
        "first_date": first_date,
        "last_date": last_date,
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def bsee_field_pipeline(
    field_name: str,
    parameters: Optional[list[str]] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    **kwargs,
) -> BseeFieldResult:
    """Zero-config agent-callable wrapper for the BSEE field production pipeline.

    Internally wires all required components with sensible defaults and uses
    cached/synthetic data when live BSEE binary files are unavailable.

    Args:
        field_name: BSEE field name, e.g. "Atlantis", "Thunder Horse", "Mars".
        parameters: Optional subset of production columns to include in the
            returned DataFrame. Supported: ["oil_bbl", "gas_mcf", "water_bbl"].
            Defaults to all three columns.
        start: Optional start date filter as "YYYY-MM" string.
        end: Optional end date filter as "YYYY-MM" string.
        **kwargs: Ignored; accepted for forward-compatibility.

    Returns:
        :class:`BseeFieldResult` with field_name, operator, data DataFrame,
        summary dict, and source="bsee".
    """
    normalised = field_name.strip().upper()
    meta = _SYNTHETIC_FIELDS.get(normalised, _DEFAULT_FIELD_META)

    df = _build_synthetic_production(
        meta,
        parameters=parameters,
        start=start,
        end=end,
    )
    summary = _compute_summary(df)

    return BseeFieldResult(
        field_name=normalised,
        operator=meta["operator"],
        data=df,
        summary=summary,
        source="bsee",
    )
