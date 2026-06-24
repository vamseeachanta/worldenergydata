# ABOUTME: Loads and extends WTI price series beyond the V30 baseline (Jul 2025) through Oct 2025
# ABOUTME: Cascades through EIA GitHub CSV, FRED API, and flat-forward fallback sources
from __future__ import annotations

import logging
import os
from io import StringIO
from typing import Optional

import pandas as pd

try:
    import requests

    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

from worldenergydata.lower_tertiary.v30_reproducer import (
    load_v30_wti_prices as _load_v30,
)

logger = logging.getLogger(__name__)

EIA_GITHUB_CSV_URL = (
    "https://raw.githubusercontent.com/datasets/oil-prices/main/data/wti-monthly.csv"
)
FRED_SERIES_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_SERIES_ID = "WTISPLC"
V30_LAST_PRICE = 68.39
V30_LAST_MONTH = pd.Timestamp("2025-07-01")


def load_v30_wti_prices() -> pd.DataFrame:
    """Re-export V30 WTI prices. Columns: Month (datetime), WTI_USD (float)."""
    return _load_v30()


def _fetch_eia_github_prices(
    after_date: pd.Timestamp,
    through_date: pd.Timestamp,
) -> Optional[pd.DataFrame]:
    """Download WTI monthly prices from EIA GitHub CSV. Returns None on failure."""
    if not _HAS_REQUESTS:
        logger.info("requests not installed; skipping EIA GitHub source")
        return None
    try:
        resp = requests.get(EIA_GITHUB_CSV_URL, timeout=15)
        resp.raise_for_status()
    except Exception:
        logger.warning("Failed to fetch EIA GitHub CSV", exc_info=True)
        return None
    try:
        raw = pd.read_csv(StringIO(resp.text))
        raw.columns = [c.strip() for c in raw.columns]
        raw = raw.rename(columns={"Date": "Month", "Price": "WTI_USD"})
        raw["Month"] = pd.to_datetime(raw["Month"])
        # Normalize to first-of-month (EIA CSV uses mid-month dates)
        raw["Month"] = raw["Month"].dt.to_period("M").dt.to_timestamp()
        raw["WTI_USD"] = pd.to_numeric(raw["WTI_USD"], errors="coerce")
        raw = raw.dropna(subset=["WTI_USD"])
    except Exception:
        logger.warning("Failed to parse EIA GitHub CSV", exc_info=True)
        return None
    subset = raw[(raw["Month"] > after_date) & (raw["Month"] <= through_date)].copy()
    if subset.empty:
        logger.info("EIA GitHub CSV has no data after %s", after_date)
        return None
    subset["source"] = "eia_github"
    return subset[["Month", "WTI_USD", "source"]].reset_index(drop=True)


def _fetch_fred_prices(
    after_date: pd.Timestamp,
    through_date: pd.Timestamp,
) -> Optional[pd.DataFrame]:
    """Fetch WTI monthly from FRED WTISPLC series. Requires FRED_API_KEY env var."""
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        logger.info("FRED_API_KEY not set; skipping FRED source")
        return None
    if not _HAS_REQUESTS:
        logger.info("requests not installed; skipping FRED source")
        return None
    params = {
        "series_id": FRED_SERIES_ID,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": (after_date + pd.DateOffset(months=1)).strftime(
            "%Y-%m-%d"
        ),
        "observation_end": through_date.strftime("%Y-%m-%d"),
    }
    try:
        resp = requests.get(FRED_SERIES_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        logger.warning("Failed to fetch FRED API data", exc_info=True)
        return None
    rows = []
    for obs in data.get("observations", []):
        value = obs.get("value", ".")
        if value != ".":
            rows.append({"Month": pd.Timestamp(obs["date"]), "WTI_USD": float(value)})
    if not rows:
        logger.info("FRED API returned no usable observations")
        return None
    df = pd.DataFrame(rows)
    df["source"] = "fred_api"
    return df[["Month", "WTI_USD", "source"]].reset_index(drop=True)


def _covered_periods(df: Optional[pd.DataFrame]) -> set:
    """Return set of Month periods already present in extension df."""
    if df is None or df.empty:
        return set()
    return set(df["Month"].dt.to_period("M"))


def _needed_months(
    v30_last: pd.Timestamp, through_ts: pd.Timestamp
) -> pd.DatetimeIndex:
    """Generate monthly date range for the gap after V30 through target date."""
    return pd.date_range(
        start=v30_last + pd.DateOffset(months=1),
        end=through_ts,
        freq="MS",
    )


def _append(base: Optional[pd.DataFrame], new: pd.DataFrame) -> pd.DataFrame:
    """Concat new rows onto base, handling None base."""
    if base is None:
        return new
    return pd.concat([base, new], ignore_index=True)


def load_extended_wti_prices(through_date: str = "2025-10-01") -> pd.DataFrame:
    """Load V30 WTI prices and extend through ``through_date``.

    Priority: 1) EIA GitHub CSV  2) FRED API  3) Flat-forward from V30 last price.
    Returns DataFrame: Month (datetime), WTI_USD (float), source (str).
    """
    through_ts = pd.Timestamp(through_date)
    v30_df = _load_v30().copy()
    v30_df["source"] = "v30_xlsx"
    v30_last = v30_df["Month"].max()
    logger.info("V30 prices span %s to %s", v30_df["Month"].min(), v30_last)

    if through_ts <= v30_last:
        return v30_df[["Month", "WTI_USD", "source"]].reset_index(drop=True)

    needed = _needed_months(v30_last, through_ts)
    extension: Optional[pd.DataFrame] = None

    # 1. EIA GitHub CSV
    extension = _fetch_eia_github_prices(v30_last, through_ts)
    if extension is not None:
        logger.info("Extended %d months from EIA GitHub", len(extension))

    # 2. FRED API — fill uncovered months only
    uncovered = {m.to_period("M") for m in needed} - _covered_periods(extension)
    if uncovered:
        fred_data = _fetch_fred_prices(v30_last, through_ts)
        if fred_data is not None:
            existing = _covered_periods(extension)
            fred_data = fred_data[~fred_data["Month"].dt.to_period("M").isin(existing)]
            if not fred_data.empty:
                extension = _append(extension, fred_data)
                logger.info("Added %d months from FRED API", len(fred_data))

    # 3. Flat-forward for any remaining gaps
    still_missing = [
        m for m in needed if m.to_period("M") not in _covered_periods(extension)
    ]
    if still_missing:
        ff_df = pd.DataFrame({"Month": still_missing, "WTI_USD": V30_LAST_PRICE})
        ff_df["source"] = "flat_forward"
        extension = _append(extension, ff_df)
        logger.info("Flat-forwarded %d months at $%.2f", len(ff_df), V30_LAST_PRICE)

    # Validate Jul 2025 overlap and drop duplicate (V30 is authoritative)
    if extension is not None:
        overlap = extension[extension["Month"] == V30_LAST_MONTH]
        if not overlap.empty:
            overlap_price = overlap["WTI_USD"].iloc[0]
            if abs(overlap_price - V30_LAST_PRICE) > 0.01:
                logger.warning(
                    "Jul 2025 overlap mismatch: V30=$%.2f, extension=$%.2f",
                    V30_LAST_PRICE,
                    overlap_price,
                )
            extension = extension[extension["Month"] != V30_LAST_MONTH]

    result = pd.concat([v30_df, extension], ignore_index=True)
    result = result.sort_values("Month").reset_index(drop=True)
    return result[["Month", "WTI_USD", "source"]]


def get_wti_source_summary(prices_df: pd.DataFrame) -> dict[str, int]:
    """Return count of months from each source in the prices DataFrame."""
    all_sources = ["v30_xlsx", "eia_github", "fred_api", "flat_forward"]
    counts = prices_df["source"].value_counts().to_dict()
    return {src: int(counts.get(src, 0)) for src in all_sources}
