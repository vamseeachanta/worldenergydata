"""Per-field gross oil & gas revenue atlas (deterministic, fabrication-free).

Computes, per BSEE field, the **cumulative gross oil revenue** as the sum over
every monthly OGOR-A record of ``monthly oil volume (bbl) x real monthly WTI
($/bbl)``, and the **cumulative gross gas revenue** as the sum of
``monthly gas volume (Mcf) x 1.037 MMBtu/Mcf x real monthly Henry Hub
($/MMBtu)``.  These are economics-tier deliverables: per the scoping memo,
true NPV cannot generalize across the basin (development costs are hand-curated
per field), but *gross* revenue is fully real — production is measured (OGOR-A)
and price is a real published series (WTI / Henry Hub).

Scope and honesty notes
------------------------
* **Gross, pre-royalty, pre-cost.**  No royalties, opex, capex, or working
  interest are applied — this is topline revenue, not value to any party.
* **Real WTI join (oil).**  Each monthly record is priced with the WTI for its
  ``PRODUCTION_DATE`` month.  Records whose month is missing from the WTI deck
  are *dropped* (and the drop is logged), never priced with a guessed value.
  The committed deck spans 1986-01..2026-05, so for the 1996-2025 atlas range
  the dropped count is ~0.
* **Real Henry Hub join (gas).**  Each monthly record's gas volume (Mcf) is
  converted to MMBtu via :data:`MCF_TO_MMBTU` (a labeled heat-content
  assumption, not a fabricated price) and priced with the Henry Hub spot for
  its month.  The committed deck spans 1997-01..2026-05, so 1996 gas is
  *unpriced* and dropped+logged honestly.
* Fields with no priced production get an honest ``NaN`` in
  :func:`apply_field_revenue` / :func:`apply_field_gas_revenue` (left join),
  not a fabricated ``0``.
* **Total.**  :func:`apply_field_gas_revenue` derives
  ``GROSS_TOTAL_REVENUE_MM_USD = GROSS_OIL_REVENUE_MM_USD +
  GROSS_GAS_REVENUE_MM_USD.fillna(0)`` *where oil is present*, else ``NaN``.
  Oil is the primary; a null gas means no gas was priced for that field, so
  treating it as 0 in the sum is honest (it adds nothing) — but a field with
  no priced oil at all stays ``NaN`` rather than reporting a gas-only total.
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
# the repo root.  After the Phase 2 batch-3 carve (#529) this file lives at
# ``packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/field_revenue.py``
# -> 7 parents (parents[6]) to the repo root (was parents[4] pre-carve).
_REPO_ROOT = Path(__file__).resolve().parents[6]
_FDAS_V30_DIR = (
    _REPO_ROOT / "docs" / "modules" / "bsee" / "analysis" / "production" / "FDAS_V30"
)
_DEFAULT_WTI_PATH = _FDAS_V30_DIR / "wti_monthly.xlsx"
_DEFAULT_HH_PATH = _FDAS_V30_DIR / "henry_hub_monthly.xlsx"

# Standard EIA average heat content of US natural gas: 1 Mcf ~= 1.037 MMBtu.
# This is a *labeled conversion assumption* used to translate OGOR-A gas
# volumes (Mcf) into the Henry Hub price basis ($/MMBtu) — it is not a
# fabricated price. See https://www.eia.gov (annual heat-content averages).
MCF_TO_MMBTU = 1.037

_REVENUE_COLUMNS = ["FIELD_NAME_CODE", "GROSS_OIL_REVENUE_MM_USD"]
_GAS_REVENUE_COLUMNS = ["FIELD_NAME_CODE", "GROSS_GAS_REVENUE_MM_USD"]


def _load_price_deck(path: Path, price_col: str, label: str) -> Dict[int, float]:
    """Load a monthly price ``.xlsx`` (``Month``, ``<price_col>``) to a map.

    Shared by :func:`load_wti_monthly` and :func:`load_hh_monthly`.  Returns an
    empty dict (graceful) when the file is missing, unreadable, or lacks the
    expected columns — callers degrade rather than fabricate.
    """
    if not path.exists():
        logger.warning("%s deck not found: %s", label, path)
        return {}

    try:
        df = pd.read_excel(path)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error reading %s deck %s: %s", label, path, exc)
        return {}

    if "Month" not in df.columns or price_col not in df.columns:
        logger.warning(
            "%s deck %s missing Month/%s columns (got %s)",
            label,
            path,
            price_col,
            list(df.columns),
        )
        return {}

    months = pd.to_datetime(df["Month"], errors="coerce")
    prices = pd.to_numeric(df[price_col], errors="coerce")
    out: Dict[int, float] = {}
    for ts, price in zip(months, prices):
        if pd.isna(ts) or pd.isna(price):
            continue
        yyyymm = ts.year * 100 + ts.month
        out[int(yyyymm)] = float(price)
    logger.info("Loaded %d monthly %s prices from %s", len(out), label, path)
    return out


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
    return _load_price_deck(path, "WTI_USD", "WTI")


def load_hh_monthly(path: Optional[Path] = None) -> Dict[int, float]:
    """Load the monthly Henry Hub deck as a ``{YYYYMM: HH_USD}`` mapping.

    Parameters
    ----------
    path:
        Path to the Henry Hub ``.xlsx`` (columns ``Month`` datetime month-start
        and ``HH_USD`` in $/MMBtu).  Defaults to the committed FDAS_V30 deck
        under ``docs/`` (spans 1997-01..2026-05).

    Returns
    -------
    dict[int, float]
        ``{YYYYMM_int: price_per_MMBtu}``.  Empty dict when the file is missing
        or unreadable (graceful — mirrors :func:`load_wti_monthly`).
    """
    path = Path(path) if path is not None else _DEFAULT_HH_PATH
    return _load_price_deck(path, "HH_USD", "Henry Hub")


def _read_ogor_volume(raw: pd.DataFrame, vol_col: str) -> pd.DataFrame:
    """Project a raw OGOR-A frame to ``FIELD_NAME_CODE/PRODUCTION_DATE/VOL``.

    ``vol_col`` is the volume column to extract (``MON_O_PROD_VOL`` for oil,
    ``MON_G_PROD_VOL`` for gas).  Quotes/whitespace are stripped; non-numeric
    volumes become ``0.0``; ``PRODUCTION_DATE`` is coerced to numeric YYYYMM.
    """
    return pd.DataFrame(
        {
            "FIELD_NAME_CODE": raw["BOEM_FIELD"]
            .astype(str)
            .str.replace('"', "", regex=False)
            .str.strip(),
            "PRODUCTION_DATE": pd.to_numeric(raw["PRODUCTION_DATE"], errors="coerce"),
            "VOL": pd.to_numeric(
                raw[vol_col].astype(str).str.replace('"', "", regex=False).str.strip(),
                errors="coerce",
            ).fillna(0.0),
        }
    )


def _build_field_revenue(
    data_dir: Path,
    prices: Dict[int, float],
    vol_col: str,
    out_col: str,
    out_columns: list,
    vol_factor: float,
    vol_unit: str,
    start_year: int,
    end_year: int,
) -> pd.DataFrame:
    """Shared OGOR-iteration: price ``vol_col x vol_factor x price`` per field.

    For each year's OGOR-A ``.bin`` (loaded via :func:`load_ogor_bin`), each
    record's monthly volume is converted by ``vol_factor`` and multiplied by the
    monthly price for its ``PRODUCTION_DATE``; the product is summed per
    ``BOEM_FIELD`` and divided by 1e6.  Records whose month is absent from the
    price deck are dropped and logged (never fabricated).  Returns a frame with
    ``[FIELD_NAME_CODE, out_col]``, empty (typed) when nothing is priced.
    """
    frames = []
    loaded, missing = 0, 0
    dropped_rows, dropped_vol = 0, 0.0
    for year in range(start_year, end_year + 1):
        path = data_dir / f"ogora{year}delimit.bin"
        if not path.exists():
            missing += 1
            continue
        raw = load_ogor_bin(path)
        if raw.empty:
            missing += 1
            continue

        work = _read_ogor_volume(raw, vol_col)
        work["PRICE"] = work["PRODUCTION_DATE"].map(
            lambda d: prices.get(int(d)) if pd.notna(d) else None
        )

        unpriced = work["PRICE"].isna()
        if unpriced.any():
            dropped_rows += int(unpriced.sum())
            dropped_vol += float(work.loc[unpriced, "VOL"].sum())
        priced = work[~unpriced].copy()
        if priced.empty:
            loaded += 1
            continue

        priced["REVENUE"] = priced["VOL"] * vol_factor * priced["PRICE"]
        frames.append(priced[["FIELD_NAME_CODE", "REVENUE"]])
        loaded += 1

    if dropped_rows:
        logger.warning(
            "Dropped %d OGOR rows (%.1f %s) with no price in deck "
            "(month outside deck coverage) — not fabricated.",
            dropped_rows,
            dropped_vol,
            vol_unit,
        )

    if not frames:
        logger.warning(
            "No priced OGOR production loaded from %s (%d years missing/empty)",
            data_dir,
            missing,
        )
        return pd.DataFrame(columns=out_columns)

    combined = pd.concat(frames, ignore_index=True)
    grouped = (
        combined.groupby("FIELD_NAME_CODE", as_index=False)["REVENUE"]
        .sum()
        .rename(columns={"REVENUE": out_col})
    )
    grouped[out_col] = grouped[out_col] / 1e6
    logger.info(
        "Built %s for %d fields from %d OGOR years (%d missing/empty); "
        "basin total $%.1f MM.",
        out_col,
        len(grouped),
        loaded,
        missing,
        float(grouped[out_col].sum()),
    )
    return grouped[out_columns]


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

    return _build_field_revenue(
        data_dir=data_dir,
        prices=wti,
        vol_col="MON_O_PROD_VOL",
        out_col="GROSS_OIL_REVENUE_MM_USD",
        out_columns=_REVENUE_COLUMNS,
        vol_factor=1.0,
        vol_unit="bbl oil",
        start_year=start_year,
        end_year=end_year,
    )


def build_field_gas_revenue(
    data_dir: Optional[Path] = None,
    hh_path: Optional[Path] = None,
    start_year: int = 1996,
    end_year: int = 2025,
) -> pd.DataFrame:
    """Build per-field cumulative gross gas revenue from OGOR-A x Henry Hub.

    For each year in ``[start_year, end_year]`` the OGOR-A ``.bin`` is loaded
    monthly, each record's gas volume is converted to MMBtu via
    :data:`MCF_TO_MMBTU`, priced with the Henry Hub spot for its
    ``PRODUCTION_DATE`` month, and ``MON_G_PROD_VOL x 1.037 x HH`` is summed per
    ``BOEM_FIELD`` and divided by 1e6.

    Records whose month is missing from the Henry Hub deck are dropped and
    logged.  The committed deck starts 1997-01, so 1996 gas is *unpriced* (and
    honestly reported as dropped), never priced with a guessed value.

    Parameters
    ----------
    data_dir:
        Directory of ``ogora{year}delimit.bin`` files.  Defaults to the
        resolved ``<bsee>/bin/historical_production_yearly``.
    hh_path:
        Henry Hub deck path (see :func:`load_hh_monthly`).
    start_year, end_year:
        Inclusive year range.

    Returns
    -------
    pd.DataFrame
        Columns ``FIELD_NAME_CODE``, ``GROSS_GAS_REVENUE_MM_USD`` (millions of
        USD).  Empty (correctly-typed) when no priced production is found.
    """
    if data_dir is None:
        data_dir = get_module_data_safe("bsee") / "bin" / _DEFAULT_SUBDIR
    data_dir = Path(data_dir)

    hh = load_hh_monthly(hh_path)
    if not hh:
        logger.warning("No Henry Hub prices loaded — gross gas revenue empty.")
        return pd.DataFrame(columns=_GAS_REVENUE_COLUMNS)

    return _build_field_revenue(
        data_dir=data_dir,
        prices=hh,
        vol_col="MON_G_PROD_VOL",
        out_col="GROSS_GAS_REVENUE_MM_USD",
        out_columns=_GAS_REVENUE_COLUMNS,
        vol_factor=MCF_TO_MMBTU,
        vol_unit="Mcf gas",
        start_year=start_year,
        end_year=end_year,
    )


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


def apply_field_gas_revenue(
    result_df: pd.DataFrame, gas_df: pd.DataFrame
) -> pd.DataFrame:
    """Merge gross gas revenue and derive a gross total into a result frame.

    Left-joins ``gas_df`` (keyed on ``FIELD_NAME_CODE``) onto ``result_df``
    (keyed on ``FIELD_CODE``), adding ``GROSS_GAS_REVENUE_MM_USD`` (honest
    ``NaN`` for fields with no priced gas).  Then derives
    ``GROSS_TOTAL_REVENUE_MM_USD``.

    Total rule (documented honest choice)
    -------------------------------------
    ``GROSS_TOTAL_REVENUE_MM_USD = GROSS_OIL_REVENUE_MM_USD +
    GROSS_GAS_REVENUE_MM_USD.fillna(0)`` **only where oil is present**; ``NaN``
    otherwise.  Oil is the primary stream — a null gas means no gas was priced
    for that field, so adding 0 is honest (contributes nothing).  A field with
    no priced oil at all stays ``NaN`` rather than reporting a gas-only total.
    Requires :func:`apply_field_revenue` to have already added the oil column;
    if it is absent, the total is all ``NaN`` and a warning is logged.

    ``result_df`` is not mutated.
    """
    out = result_df.copy()
    if "FIELD_CODE" not in out.columns:
        logger.warning("result_df has no FIELD_CODE — gas revenue not merged.")
        out["GROSS_GAS_REVENUE_MM_USD"] = pd.NA
        out["GROSS_TOTAL_REVENUE_MM_USD"] = pd.NA
        return out

    if gas_df is None or gas_df.empty:
        out["GROSS_GAS_REVENUE_MM_USD"] = pd.NA
    else:
        rev = gas_df[["FIELD_NAME_CODE", "GROSS_GAS_REVENUE_MM_USD"]].copy()
        rev["FIELD_NAME_CODE"] = rev["FIELD_NAME_CODE"].astype(str).str.strip()
        out["_join_code"] = out["FIELD_CODE"].astype(str).str.strip()
        out = out.merge(
            rev,
            how="left",
            left_on="_join_code",
            right_on="FIELD_NAME_CODE",
        ).drop(columns=["_join_code", "FIELD_NAME_CODE"])

    if "GROSS_OIL_REVENUE_MM_USD" not in out.columns:
        logger.warning(
            "GROSS_OIL_REVENUE_MM_USD absent — total left null. Call "
            "apply_field_revenue first."
        )
        out["GROSS_TOTAL_REVENUE_MM_USD"] = pd.NA
        return out

    oil = pd.to_numeric(out["GROSS_OIL_REVENUE_MM_USD"], errors="coerce")
    gas = pd.to_numeric(out["GROSS_GAS_REVENUE_MM_USD"], errors="coerce")
    total = oil + gas.fillna(0.0)
    # NaN where oil is missing (gas-only fields are not reported as a total).
    out["GROSS_TOTAL_REVENUE_MM_USD"] = total.where(oil.notna())
    return out
