#!/usr/bin/env python3
"""
ABOUTME: Reproduces FDAS V30 lower tertiary results from raw BSEE OGOR data
ABOUTME: Uses V30 assumptions and methodology for WRK-009 repeatability verification
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd
import yaml

from worldenergydata.common.data_resolver import get_module_data_safe
from worldenergydata.common.logging import get_logger

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
FDAS_V30_DIR = PROJECT_ROOT / "docs/modules/bsee/analysis/production/FDAS_V30"
OGOR_ZIP_DIR = get_module_data_safe("bsee") / "zip" / "historical_production_yearly"
GOLDEN_BASELINE_PATH = (
    PROJECT_ROOT / "config/analysis/lower_tertiary/golden_baseline_v30.yml"
)


def load_v30_leases() -> pd.DataFrame:
    """Load V30 lease-to-development mapping from leases.xlsx.

    Columns: LEASE_NUM, Lease_Numeric, LEASE_NAME, DEV_NAME,
             WATER_DEPTH, DEV_SYSTEM
    """
    leases_path = FDAS_V30_DIR / "leases.xlsx"
    df = pd.read_excel(leases_path)
    # Normalize LEASE_NUM: strip, uppercase, remove quotes/spaces
    df["LEASE_NUM"] = (
        df["LEASE_NUM"]
        .astype(str)
        .str.strip()
        .str.upper()
        .str.replace('"', "", regex=False)
        .str.replace(" ", "", regex=False)
    )
    return df


def load_v30_assumptions() -> pd.DataFrame:
    """Load V30 lease assumptions from lease_assumptions.xlsx.

    Returns transposed DataFrame with DEV_SYSTEM as index and assumption
    rows as columns (subsea15, subsea20, dry, tieback15, tieback20).
    """
    assumptions_path = FDAS_V30_DIR / "lease_assumptions.xlsx"
    df = pd.read_excel(assumptions_path)
    return df


def load_v30_wti_prices() -> pd.DataFrame:
    """Load V30 WTI monthly price series from wti_monthly.xlsx.

    Columns: Month (datetime), WTI_USD (float)
    """
    wti_path = FDAS_V30_DIR / "wti_monthly.xlsx"
    df = pd.read_excel(wti_path)
    df["Month"] = pd.to_datetime(df["Month"])
    return df


def load_v30_drilling() -> pd.DataFrame:
    """Load V30 drilling and completion days.

    Columns: LEASE_NAME, SURF_LEASE_NUM, WATER_DEPTH, API_WELL_NUMBER,
             WELL_NAME, WELL_SPUD_DATE, TOTAL_DEPTH_DATE, DRILLING_DAYS,
             COMPLETION_DAYS, MAX_BH_TOTAL_MD, MAX_WELL_BORE_TVD,
             MAX_DRILL_FLUID_WGT
    """
    dnc_path = FDAS_V30_DIR / "drilling_and_completion_days.xlsx"
    df = pd.read_excel(dnc_path)
    return df


def load_ogor_production(start_year: int = 2000, end_year: int = 2025) -> pd.DataFrame:
    """Load production from BSEE OGOR delimited zip files.

    Reads yearly OGOR-A archives, parses the fixed-width CSV, and returns
    a DataFrame with normalised LEASE_NUMBER, MON_O_PROD_VOL, and date.
    """
    column_names = [
        "LEASE_NUMBER",
        "COMPLETION_NAME",
        "PRODUCTION_DATE",
        "DAYS_ON_PROD",
        "PRODUCT_CODE",
        "MON_O_PROD_VOL",
        "MON_G_PROD_VOL",
        "MON_WTR_PROD_VOL",
        "API_WELL_NUMBER",
        "WELL_STAT_CD",
        "AREA_CODE_BLOCK_NUM",
        "OPERATOR_NUM",
        "SORT_NAME",
        "BOEM_FIELD",
        "INJECTION_VOLUME",
        "PROD_INTERVAL_CD",
        "FIRST_PROD_DATE",
        "UNIT_AGT_NUMBER",
        "UNIT_ALOC_SUFFIX",
    ]

    frames: list[pd.DataFrame] = []
    for year in range(start_year, end_year + 1):
        zip_path = OGOR_ZIP_DIR / f"ogora{year}delimit.zip"
        if not zip_path.exists():
            continue
        with zipfile.ZipFile(zip_path, "r") as archive:
            inner_name = f"ogora{year}delimit.txt"
            if inner_name not in archive.namelist():
                inner_name = "ogoradelimit.txt"
            if inner_name not in archive.namelist():
                continue
            with archive.open(inner_name) as handle:
                frame = pd.read_csv(
                    handle,
                    sep=",",
                    names=column_names,
                    low_memory=False,
                    quotechar='"',
                )
                frames.append(frame)

    if not frames:
        raise FileNotFoundError("No OGOR production files loaded")

    df = pd.concat(frames, ignore_index=True)

    # Normalise lease numbers: strip whitespace, remove quotes, uppercase
    df["LEASE_NUMBER"] = (
        df["LEASE_NUMBER"]
        .astype(str)
        .str.strip()
        .str.replace('"', "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.upper()
    )

    # Parse oil volume
    df["MON_O_PROD_VOL"] = pd.to_numeric(
        df["MON_O_PROD_VOL"].astype(str).str.replace('"', "", regex=False).str.strip(),
        errors="coerce",
    ).fillna(0.0)

    # Clean OGOR code columns for downstream classification
    for col in ("PRODUCT_CODE", "WELL_STAT_CD"):
        df[col] = (
            df[col]
            .astype(str)
            .str.strip()
            .str.replace('"', "", regex=False)
            .str.upper()
        )

    # Parse production date to datetime
    df["PRODUCTION_DATE"] = pd.to_numeric(df["PRODUCTION_DATE"], errors="coerce")
    df["date"] = pd.to_datetime(df["PRODUCTION_DATE"], format="%Y%m", errors="coerce")

    return df


def aggregate_production_by_development(
    ogor_df: pd.DataFrame,
    leases_df: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Aggregate OGOR production by V30 development.

    Uses the LEASE_NUM -> DEV_NAME mapping from leases.xlsx to group
    raw OGOR lease-level production into development-level monthly
    totals.
    """
    # Build lease -> development mapping
    lease_to_dev = dict(zip(leases_df["LEASE_NUM"], leases_df["DEV_NAME"]))

    # Filter OGOR for V30 leases only
    v30_leases = set(lease_to_dev.keys())
    ogor_filtered = ogor_df[ogor_df["LEASE_NUMBER"].isin(v30_leases)].copy()
    ogor_filtered["development"] = ogor_filtered["LEASE_NUMBER"].map(lease_to_dev)

    # Aggregate by development and month
    result: dict[str, pd.DataFrame] = {}
    for dev_name, group in ogor_filtered.groupby("development"):
        monthly = (
            group.groupby("date", as_index=False)["MON_O_PROD_VOL"]
            .sum()
            .rename(columns={"MON_O_PROD_VOL": "oil_bbl"})
            .sort_values("date")
        )
        result[dev_name] = monthly

    return result


def load_golden_baseline() -> dict:
    """Load the golden baseline YAML for V30 comparison."""
    with GOLDEN_BASELINE_PATH.open("r") as f:
        return yaml.safe_load(f)


def _build_first_oil_map(baseline: dict) -> dict[str, pd.Timestamp]:
    """Extract first_oil dates per development display name from baseline."""
    first_oil_map: dict[str, pd.Timestamp] = {}
    for proj_data in baseline["projects"].values():
        if proj_data.get("first_oil"):
            first_oil_map[proj_data["display_name"]] = pd.Timestamp(
                proj_data["first_oil"]
            )
    return first_oil_map


def reproduce_v30_production(
    end_date: str | None = None,
    first_oil_overrides: dict[str, str] | None = None,
) -> dict[str, dict]:
    """Reproduce V30 production totals from BSEE OGOR data.

    Parameters
    ----------
    end_date : str | None
        Optional upper date bound (YYYY-MM-DD format). When *None* (default),
        uses the original V30 window ending 2025-05-31. When provided, uses
        that date as the upper bound instead.
    first_oil_overrides : dict, optional
        Mapping of development display name -> corrected first_oil date string.
        Applied on top of golden baseline dates to fix known errors without
        modifying the golden baseline itself.

    Returns a dict keyed by development display name, each containing:
      - total_oil_bbl: cumulative oil barrels
      - months: count of producing months
      - first_date: earliest production date
      - last_date: latest production date
      - monthly_production: DataFrame with date, oil_bbl columns
    """
    leases_df = load_v30_leases()
    end_year = 2025
    if end_date is not None:
        end_year = max(2025, int(end_date[:4]))
    ogor_df = load_ogor_production(start_year=2000, end_year=end_year)

    # Apply V30 time window: the V30 production data covers Sep 2000 through
    # May 2025 (the latest OGOR data Roy had when building V30).
    upper_date = end_date if end_date is not None else "2025-05-31"
    ogor_df = ogor_df[
        (ogor_df["date"] >= "2000-09-01") & (ogor_df["date"] <= upper_date)
    ]

    dev_production = aggregate_production_by_development(ogor_df, leases_df)

    # Load per-development first_oil dates from golden baseline to exclude
    # pre-first-oil test/exploration production that Roy excluded in V30.
    baseline = load_golden_baseline()
    first_oil_map = _build_first_oil_map(baseline)

    # Apply corrected first_oil dates (preserves golden baseline untouched)
    if first_oil_overrides:
        for dev_name, date_str in first_oil_overrides.items():
            first_oil_map[dev_name] = pd.Timestamp(date_str)

    results: dict[str, dict] = {}
    for dev_name, monthly_df in dev_production.items():
        monthly_df = monthly_df[monthly_df["oil_bbl"] > 0]
        # Apply per-development first_oil filter
        if dev_name in first_oil_map:
            monthly_df = monthly_df[monthly_df["date"] >= first_oil_map[dev_name]]
        if monthly_df.empty:
            continue
        results[dev_name] = {
            "total_oil_bbl": monthly_df["oil_bbl"].sum(),
            "months": len(monthly_df),
            "first_date": monthly_df["date"].min(),
            "last_date": monthly_df["date"].max(),
            "monthly_production": monthly_df,
        }

    return results


if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("V30 Production Reproduction from BSEE OGOR Data")
    logger.info("=" * 80)

    baseline = load_golden_baseline()
    results = reproduce_v30_production()

    logger.info(f"\nDevelopments found: {len(results)}")
    header = (
        f"{'Development':<25} {'OGOR Oil (BBL)':>18} "
        f"{'V30 Oil (BBL)':>18} {'Delta %':>10}"
    )
    logger.info(header)
    logger.info("-" * 75)

    for _proj_id, proj_data in baseline["projects"].items():
        dev_name = proj_data["display_name"]
        expected = proj_data["total_oil_bbl"]

        if dev_name in results:
            actual = results[dev_name]["total_oil_bbl"]
            delta = ((actual - expected) / expected * 100) if expected else 0
            logger.info(
                f"{dev_name:<25} {actual:>18,.0f} "
                f"{expected:>18,.0f} {delta:>+10.2f}%"
            )
        else:
            logger.info(f"{dev_name:<25} {'NOT FOUND':>18} {expected:>18,.0f}")
