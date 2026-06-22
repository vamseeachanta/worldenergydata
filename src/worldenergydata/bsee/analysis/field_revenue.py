"""Per-field gross oil revenue atlas (deterministic, fabrication-free).

Computes, per BSEE field, the **cumulative gross oil revenue** as the sum over
every monthly OGOR-A record of ``monthly oil volume (bbl) x real monthly WTI
($/bbl)``.  This is the first economics-tier deliverable: per the scoping memo,
true NPV cannot generalize across the basin (development costs are hand-curated
per field), but *gross* revenue is fully real — production is measured (OGOR-A)
and price is a real published series (WTI).

Scope and honesty notes
------------------------
* **Oil only.**  There is no Henry Hub gas price deck in this repo, so gas
  revenue is intentionally *not* computed (it would be fabricated).  The
  ``GROSS_OIL_REVENUE_MM_USD`` name says so explicitly.
* **Gross, pre-royalty, pre-cost.**  No royalties, opex, capex, or working
  interest are applied — this is topline revenue, not value to any party.
* **Real WTI join.**  Each monthly record is priced with the WTI for its
  ``PRODUCTION_DATE`` month.  Records whose month is missing from the WTI deck
  are *dropped* (and the drop is logged), never priced with a guessed value.
  The committed deck spans 1986-01..2025-07, so for the 1996-2025 atlas range
  the dropped count is ~0.
* Fields with no priced production get an honest ``NaN`` in
  :func:`apply_field_revenue` (left join), not a fabricated ``0``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from worldenergydata.bsee.data.sources.bin.ogor_production_loader import (
    load_ogor_bin,
)
from worldenergydata.common.data_resolver import get_module_data_safe

logger = logging.getLogger(__name__)

_DEFAULT_SUBDIR = "historical_production_yearly"

# Repo-relative default WTI deck (under docs/, not data/).  Resolved the same
# way as ``field_names.py`` resolves its data dir: walk up from this file to
# the repo root.  field_revenue.py lives at
# ``src/worldenergydata/bsee/analysis/field_revenue.py`` -> 5 parents to root.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_WTI_PATH = (
    _REPO_ROOT
    / "docs"
    / "modules"
    / "bsee"
    / "analysis"
    / "production"
    / "FDAS_V30"
    / "wti_monthly.xlsx"
)

_REVENUE_COLUMNS = ["FIELD_NAME_CODE", "GROSS_OIL_REVENUE_MM_USD"]


def load_wti_monthly(path: Optional[Path] = None) -> Dict[int, float]:
    """Load the monthly WTI deck as a ``{YYYYMM: WTI_USD}`` mapping.

    Parameters
    ----------
    path:
        Path to the WTI ``.xlsx`` (columns ``Month`` datetime month-start and
        ``WTI_USD``).  Defaults to the committed FDAS_V30 deck under ``docs/``.

    Returns
    -------
    dict[int, float]
        ``{YYYYMM_int: price}``.  Empty dict when the file is missing or
        unreadable (graceful — callers degrade rather than fabricate).
    """
    path = Path(path) if path is not None else _DEFAULT_WTI_PATH
    if not path.exists():
        logger.warning("WTI deck not found: %s", path)
        return {}

    try:
        df = pd.read_excel(path)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error reading WTI deck %s: %s", path, exc)
        return {}

    if "Month" not in df.columns or "WTI_USD" not in df.columns:
        logger.warning(
            "WTI deck %s missing Month/WTI_USD columns (got %s)",
            path,
            list(df.columns),
        )
        return {}

    months = pd.to_datetime(df["Month"], errors="coerce")
    prices = pd.to_numeric(df["WTI_USD"], errors="coerce")
    out: Dict[int, float] = {}
    for ts, price in zip(months, prices):
        if pd.isna(ts) or pd.isna(price):
            continue
        yyyymm = ts.year * 100 + ts.month
        out[int(yyyymm)] = float(price)
    logger.info("Loaded %d monthly WTI prices from %s", len(out), path)
    return out


def build_field_oil_revenue(
    data_dir: Optional[Path] = None,
    wti_path: Optional[Path] = None,
    start_year: int = 1996,
    end_year: int = 2025,
) -> pd.DataFrame:
    """Build per-field cumulative gross oil revenue from OGOR-A x WTI.

    For each year in ``[start_year, end_year]`` the OGOR-A ``.bin`` is loaded
    monthly (via :func:`load_ogor_bin` — *not* the annual runner schema), each
    record's ``PRODUCTION_DATE`` (YYYYMM) is priced with the matching WTI, and
    ``MON_O_PROD_VOL x WTI`` is summed per ``BOEM_FIELD`` and divided by 1e6.

    Records whose month is missing from the WTI deck are dropped and logged.

    Parameters
    ----------
    data_dir:
        Directory of ``ogora{year}delimit.bin`` files.  Defaults to the
        resolved ``<bsee>/bin/historical_production_yearly``.
    wti_path:
        WTI deck path (see :func:`load_wti_monthly`).
    start_year, end_year:
        Inclusive year range.

    Returns
    -------
    pd.DataFrame
        Columns ``FIELD_NAME_CODE``, ``GROSS_OIL_REVENUE_MM_USD`` (millions of
        USD).  Empty (correctly-typed) when no priced production is found.
    """
    if data_dir is None:
        data_dir = get_module_data_safe("bsee") / "bin" / _DEFAULT_SUBDIR
    data_dir = Path(data_dir)

    wti = load_wti_monthly(wti_path)
    if not wti:
        logger.warning("No WTI prices loaded — gross oil revenue will be empty.")
        return pd.DataFrame(columns=_REVENUE_COLUMNS)

    frames = []
    loaded, missing = 0, 0
    dropped_rows, dropped_oil = 0, 0.0
    for year in range(start_year, end_year + 1):
        path = data_dir / f"ogora{year}delimit.bin"
        if not path.exists():
            missing += 1
            continue
        raw = load_ogor_bin(path)
        if raw.empty:
            missing += 1
            continue

        work = pd.DataFrame(
            {
                "FIELD_NAME_CODE": raw["BOEM_FIELD"]
                .astype(str)
                .str.replace('"', "", regex=False)
                .str.strip(),
                "PRODUCTION_DATE": pd.to_numeric(
                    raw["PRODUCTION_DATE"], errors="coerce"
                ),
                "MON_O_PROD_VOL": pd.to_numeric(
                    raw["MON_O_PROD_VOL"]
                    .astype(str)
                    .str.replace('"', "", regex=False)
                    .str.strip(),
                    errors="coerce",
                ).fillna(0.0),
            }
        )
        work["WTI"] = work["PRODUCTION_DATE"].map(
            lambda d: wti.get(int(d)) if pd.notna(d) else None
        )

        unpriced = work["WTI"].isna()
        if unpriced.any():
            dropped_rows += int(unpriced.sum())
            dropped_oil += float(work.loc[unpriced, "MON_O_PROD_VOL"].sum())
        priced = work[~unpriced].copy()
        if priced.empty:
            loaded += 1
            continue

        priced["REVENUE"] = priced["MON_O_PROD_VOL"] * priced["WTI"]
        frames.append(priced[["FIELD_NAME_CODE", "REVENUE"]])
        loaded += 1

    if dropped_rows:
        logger.warning(
            "Dropped %d OGOR rows (%.1f bbl oil) with no WTI price in deck "
            "(month outside deck coverage) — not fabricated.",
            dropped_rows,
            dropped_oil,
        )

    if not frames:
        logger.warning(
            "No priced OGOR production loaded from %s (%d years missing/empty)",
            data_dir,
            missing,
        )
        return pd.DataFrame(columns=_REVENUE_COLUMNS)

    combined = pd.concat(frames, ignore_index=True)
    grouped = (
        combined.groupby("FIELD_NAME_CODE", as_index=False)["REVENUE"]
        .sum()
        .rename(columns={"REVENUE": "GROSS_OIL_REVENUE_MM_USD"})
    )
    grouped["GROSS_OIL_REVENUE_MM_USD"] = grouped["GROSS_OIL_REVENUE_MM_USD"] / 1e6
    logger.info(
        "Built gross oil revenue for %d fields from %d OGOR years "
        "(%d missing/empty); basin total $%.1f MM.",
        len(grouped),
        loaded,
        missing,
        float(grouped["GROSS_OIL_REVENUE_MM_USD"].sum()),
    )
    return grouped[_REVENUE_COLUMNS]


def apply_field_revenue(
    result_df: pd.DataFrame, revenue_df: pd.DataFrame
) -> pd.DataFrame:
    """Merge ``GROSS_OIL_REVENUE_MM_USD`` into an AllFieldsRunner result.

    Left-joins ``revenue_df`` (keyed on ``FIELD_NAME_CODE``) onto ``result_df``
    (keyed on ``FIELD_CODE``).  Fields with no revenue row get an honest
    ``NaN`` — never a fabricated zero.  ``result_df`` is not mutated.

    Parameters
    ----------
    result_df:
        Per-field result with a ``FIELD_CODE`` column.
    revenue_df:
        Output of :func:`build_field_oil_revenue`.

    Returns
    -------
    pd.DataFrame
        Copy of ``result_df`` with a ``GROSS_OIL_REVENUE_MM_USD`` column.
    """
    out = result_df.copy()
    if "FIELD_CODE" not in out.columns:
        logger.warning("result_df has no FIELD_CODE — revenue not merged.")
        out["GROSS_OIL_REVENUE_MM_USD"] = pd.NA
        return out

    if revenue_df is None or revenue_df.empty:
        out["GROSS_OIL_REVENUE_MM_USD"] = pd.NA
        return out

    rev = revenue_df[["FIELD_NAME_CODE", "GROSS_OIL_REVENUE_MM_USD"]].copy()
    rev["FIELD_NAME_CODE"] = rev["FIELD_NAME_CODE"].astype(str).str.strip()

    out["_join_code"] = out["FIELD_CODE"].astype(str).str.strip()
    merged = out.merge(
        rev,
        how="left",
        left_on="_join_code",
        right_on="FIELD_NAME_CODE",
    )
    merged = merged.drop(columns=["_join_code", "FIELD_NAME_CODE"])
    return merged
