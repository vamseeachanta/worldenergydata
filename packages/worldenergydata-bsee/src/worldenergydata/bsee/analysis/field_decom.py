"""Per-field decommissioning liability view (deterministic, fabrication-free).

Rolls up **BSEE-provided** P50/P70/P90 future abandonment cost estimates to the
field level.  This is the Rank-2 economics deliverable: unlike NPV (which needs
hand-curated per-field development costs), decom liability is sourced directly
from BSEE's ``mv_decom_cost_totals`` materialized view — these are BSEE
estimates with their own uncertainty bands (hence P50/P70/P90), not anything
this repo computes or guesses.

Pipeline
--------
1. :func:`load_decom_totals` reads the lease-level cost rows (one per cost
   category ``TYPE``) and coerces P50/P70/P90 to numbers.
2. :func:`build_lease_to_field` builds a lease->field crosswalk from OGOR-A,
   mapping each lease to its **dominant** producing field (most OGOR rows).
3. :func:`build_field_decom_liability` sums each lease across its TYPE rows,
   maps lease->field, sums per field, and divides by 1e6 (-> $MM).
4. :func:`apply_field_decom` left-joins the three DECOM_* columns onto an
   AllFieldsRunner result.

Honesty notes
-------------
* **BSEE estimate, not our model.**  P50/P70/P90 are BSEE's own probabilistic
  abandonment cost bands.  We only sum and roll up.
* **Future liability.**  These are *future* abandonment costs, not realized
  spend; treat the rollup as an order-of-magnitude liability, not a precise
  obligation.
* **Honest coverage.**  Decom rows are keyed by ``AUTH_NUMBER`` (lease, ROW,
  or RUE).  Only leases that map to a producing field via OGOR-A are rolled in;
  leases/ROW/RUE that map to no producing field are **dropped and logged**
  (with their unmapped P50 total) — never forced onto an arbitrary field.
* Fields with no decom estimate get an honest ``NaN`` in
  :func:`apply_field_decom` (left join), not a fabricated ``0``.
"""

from __future__ import annotations

import logging
import pickle  # nosec B403
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from worldenergydata.bsee.data.sources.bin.ogor_production_loader import (
    load_ogor_bin,
)
from worldenergydata.common.data_resolver import get_module_data_safe

logger = logging.getLogger(__name__)

_DECOM_SUBDIR = ("bin", "decomcost")
_DECOM_FILE = "mv_decom_cost_totals.bin"
_OGOR_SUBDIR = "historical_production_yearly"

_DECOM_OUT_COLUMNS = [
    "FIELD_NAME_CODE",
    "DECOM_P50_MM_USD",
    "DECOM_P70_MM_USD",
    "DECOM_P90_MM_USD",
]
_LOADED_COLUMNS = ["AUTH_NUMBER", "TYPE", "P50_COST", "P70_COST", "P90_COST"]


def _normalize_lease(series: pd.Series) -> pd.Series:
    """Normalize a lease/AUTH series: strip, drop quotes + internal spaces, upper.

    OGOR leases arrive as ``' 00016'`` (leading-space shelf) and ``'G23740'``;
    decom ``AUTH_NUMBER`` is clean ``'G#'``.  Both sides are normalized through
    here so they join.
    """
    return (
        series.astype(str)
        .str.replace('"', "", regex=False)
        .str.replace("'", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.strip()
        .str.upper()
    )


def load_decom_totals(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """Load the lease-level BSEE decom cost totals.

    Parameters
    ----------
    data_dir:
        Directory containing :data:`_DECOM_FILE`.  Defaults to the resolved
        ``<bsee module>/bin/decomcost``.

    Returns
    -------
    pd.DataFrame
        Columns ``AUTH_NUMBER``, ``TYPE``, ``P50_COST``, ``P70_COST``,
        ``P90_COST`` (costs coerced numeric, NaN->0).  Empty (correctly-typed)
        when the file is an LFS stub, missing, unreadable, or not a DataFrame.
    """
    if data_dir is None:
        data_dir = get_module_data_safe("bsee").joinpath(*_DECOM_SUBDIR)
    path = Path(data_dir) / _DECOM_FILE

    if not path.exists():
        logger.warning("Decom totals file not found: %s", path)
        return pd.DataFrame(columns=_LOADED_COLUMNS)

    try:
        with open(path, "rb") as f:
            header = f.read(40)
        if b"version https://git-lfs" in header:
            logger.warning("Decom totals is an LFS stub (not materialized): %s", path)
            return pd.DataFrame(columns=_LOADED_COLUMNS)
        with open(path, "rb") as f:
            obj = pickle.load(f)  # nosec B301
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error loading decom totals %s: %s", path, exc)
        return pd.DataFrame(columns=_LOADED_COLUMNS)

    if not isinstance(obj, pd.DataFrame):
        logger.warning("Decom totals is not a DataFrame: %s", path)
        return pd.DataFrame(columns=_LOADED_COLUMNS)

    required = {"AUTH_NUMBER", "TYPE", "P50_COST", "P70_COST", "P90_COST"}
    if not required <= set(obj.columns):
        logger.warning(
            "Decom totals %s missing required columns (got %s)",
            path,
            list(obj.columns),
        )
        return pd.DataFrame(columns=_LOADED_COLUMNS)

    out = pd.DataFrame(
        {
            "AUTH_NUMBER": obj["AUTH_NUMBER"],
            "TYPE": obj["TYPE"],
        }
    )
    for col in ("P50_COST", "P70_COST", "P90_COST"):
        out[col] = pd.to_numeric(
            obj[col].astype(str).str.replace('"', "", regex=False).str.strip(),
            errors="coerce",
        ).fillna(0.0)
    logger.info("Loaded %d decom cost rows from %s", len(out), path)
    return out[_LOADED_COLUMNS]


def build_lease_to_field(
    data_dir: Optional[Path] = None,
    start_year: int = 1996,
    end_year: int = 2025,
) -> Dict[str, str]:
    """Build a normalized ``{lease: dominant BOEM_FIELD}`` crosswalk from OGOR-A.

    Each lease is mapped to its **dominant** field, chosen as the field with the
    most OGOR-A rows for that lease (row count, not oil — simplest deterministic
    tiebreak; documented choice).  Lease numbers are normalized via
    :func:`_normalize_lease` so the ``' 00016'`` shelf format and clean ``'G#'``
    format both join against decom ``AUTH_NUMBER``.

    Parameters
    ----------
    data_dir:
        Directory of ``ogora{year}delimit.bin`` files.  Defaults to the
        resolved ``<bsee>/bin/historical_production_yearly``.
    start_year, end_year:
        Inclusive year range.

    Returns
    -------
    dict[str, str]
        ``{normalized_lease: field_code}``.  Empty when no OGOR data is found.
    """
    if data_dir is None:
        data_dir = get_module_data_safe("bsee") / "bin" / _OGOR_SUBDIR
    data_dir = Path(data_dir)

    frames = []
    loaded, missing = 0, 0
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
                "LEASE": _normalize_lease(raw["LEASE_NUMBER"]),
                "FIELD": raw["BOEM_FIELD"]
                .astype(str)
                .str.replace('"', "", regex=False)
                .str.strip(),
            }
        )
        frames.append(work)
        loaded += 1

    if not frames:
        logger.warning("No OGOR production bins loaded from %s", data_dir)
        return {}

    combined = pd.concat(frames, ignore_index=True)
    combined = combined[(combined["LEASE"] != "") & (combined["FIELD"] != "")]
    if combined.empty:
        return {}

    counts = combined.groupby(["LEASE", "FIELD"]).size().reset_index(name="N")
    # Dominant field per lease: most rows; deterministic tiebreak by field code.
    counts = counts.sort_values(["LEASE", "N", "FIELD"], ascending=[True, False, True])
    dominant = counts.drop_duplicates("LEASE", keep="first")
    mapping = dict(zip(dominant["LEASE"], dominant["FIELD"]))
    logger.info(
        "Built lease->field crosswalk: %d leases from %d OGOR years "
        "(%d missing/empty)",
        len(mapping),
        loaded,
        missing,
    )
    return mapping


def build_field_decom_liability(
    data_dir: Optional[Path] = None,
    ogor_dir: Optional[Path] = None,
    start_year: int = 1996,
    end_year: int = 2025,
) -> pd.DataFrame:
    """Build per-field decom liability (BSEE P50/P70/P90 estimates, $MM).

    Sums each lease across its cost-category (``TYPE``) rows, maps lease->field
    via :func:`build_lease_to_field`, sums per field, and divides by 1e6.

    The lease-join hit-rate (how many decom leases mapped to a producing field
    vs unmapped) and the unmapped P50 total are logged for honest coverage.
    Leases that map to no producing field are dropped (and logged), not forced.

    Parameters
    ----------
    data_dir:
        Directory of the decom totals bin (see :func:`load_decom_totals`).
    ogor_dir:
        Directory of the OGOR ``.bin`` files for the lease->field crosswalk.
        Defaults to the resolved ``<bsee>/bin/historical_production_yearly``.
    start_year, end_year:
        Inclusive OGOR year range for the crosswalk.

    Returns
    -------
    pd.DataFrame
        Columns ``FIELD_NAME_CODE``, ``DECOM_P50_MM_USD``, ``DECOM_P70_MM_USD``,
        ``DECOM_P90_MM_USD`` (millions of USD).  Empty (correctly-typed) when
        no decom data is found.
    """
    decom = load_decom_totals(data_dir)
    if decom.empty:
        logger.warning("No decom totals loaded — field decom liability empty.")
        return pd.DataFrame(columns=_DECOM_OUT_COLUMNS)

    # Sum each lease across its cost-category TYPE rows.
    decom = decom.copy()
    decom["LEASE"] = _normalize_lease(decom["AUTH_NUMBER"])
    per_lease = decom.groupby("LEASE", as_index=False)[
        ["P50_COST", "P70_COST", "P90_COST"]
    ].sum()

    crosswalk = build_lease_to_field(
        data_dir=ogor_dir, start_year=start_year, end_year=end_year
    )
    per_lease["FIELD_NAME_CODE"] = per_lease["LEASE"].map(crosswalk)

    mapped = per_lease[per_lease["FIELD_NAME_CODE"].notna()]
    unmapped = per_lease[per_lease["FIELD_NAME_CODE"].isna()]
    logger.info(
        "Decom lease join: %d/%d leases mapped to a producing field "
        "(%d unmapped, $%.1f MM P50 dropped — leases/ROW/RUE with no "
        "producing field, not fabricated).",
        len(mapped),
        len(per_lease),
        len(unmapped),
        float(unmapped["P50_COST"].sum()) / 1e6,
    )

    if mapped.empty:
        logger.warning("No decom leases mapped to a producing field.")
        return pd.DataFrame(columns=_DECOM_OUT_COLUMNS)

    by_field = mapped.groupby("FIELD_NAME_CODE", as_index=False)[
        ["P50_COST", "P70_COST", "P90_COST"]
    ].sum()
    out = pd.DataFrame(
        {
            "FIELD_NAME_CODE": by_field["FIELD_NAME_CODE"],
            "DECOM_P50_MM_USD": by_field["P50_COST"] / 1e6,
            "DECOM_P70_MM_USD": by_field["P70_COST"] / 1e6,
            "DECOM_P90_MM_USD": by_field["P90_COST"] / 1e6,
        }
    )
    logger.info(
        "Built decom liability for %d fields; basin P50 $%.1f MM, "
        "P90 $%.1f MM (BSEE estimates).",
        len(out),
        float(out["DECOM_P50_MM_USD"].sum()),
        float(out["DECOM_P90_MM_USD"].sum()),
    )
    return out[_DECOM_OUT_COLUMNS]


def apply_field_decom(result_df: pd.DataFrame, decom_df: pd.DataFrame) -> pd.DataFrame:
    """Merge the three DECOM_* columns into an AllFieldsRunner result.

    Left-joins ``decom_df`` (keyed on ``FIELD_NAME_CODE``) onto ``result_df``
    (keyed on ``FIELD_CODE``).  Fields with no decom estimate get an honest
    ``NaN`` — never a fabricated zero.  ``result_df`` is not mutated.

    Parameters
    ----------
    result_df:
        Per-field result with a ``FIELD_CODE`` column.
    decom_df:
        Output of :func:`build_field_decom_liability`.

    Returns
    -------
    pd.DataFrame
        Copy of ``result_df`` with the three ``DECOM_*`` columns.
    """
    decom_cols = ["DECOM_P50_MM_USD", "DECOM_P70_MM_USD", "DECOM_P90_MM_USD"]
    out = result_df.copy()

    if "FIELD_CODE" not in out.columns:
        logger.warning("result_df has no FIELD_CODE — decom not merged.")
        for col in decom_cols:
            out[col] = pd.NA
        return out

    if decom_df is None or decom_df.empty:
        for col in decom_cols:
            out[col] = pd.NA
        return out

    dec = decom_df[["FIELD_NAME_CODE", *decom_cols]].copy()
    dec["FIELD_NAME_CODE"] = dec["FIELD_NAME_CODE"].astype(str).str.strip()

    out["_join_code"] = out["FIELD_CODE"].astype(str).str.strip()
    merged = out.merge(
        dec,
        how="left",
        left_on="_join_code",
        right_on="FIELD_NAME_CODE",
    )
    merged = merged.drop(columns=["_join_code", "FIELD_NAME_CODE"])
    return merged
