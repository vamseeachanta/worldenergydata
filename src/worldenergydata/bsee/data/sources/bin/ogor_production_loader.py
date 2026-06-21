"""Loader for materialized BSEE OGOR-A production ``.bin`` pickles.

The yearly OGOR-A archives are stored on disk as pickled DataFrames at
``data/modules/bsee/bin/historical_production_yearly/ogora{year}delimit.bin``.
These pickles are **header-corrupted**: they were created by a ``read_csv``
that consumed the first data record as the column header, so every file
loads with garbage column labels and is missing its first physical row.

This module recovers them deterministically by positionally re-labelling
the 19 OGOR-A columns, then adapts the result to the column schema that
:class:`~worldenergydata.bsee.analysis.all_fields_runner.AllFieldsRunner`
expects.  This is the bridge between the materialized binary data and the
all-fields analysis pipeline (the canonical ``load_ogor_production`` reads
``.zip`` archives, which are not materialized on this deployment).

Known limitation: because the on-disk pickle lost its first record to the
corrupted header, each file contributes ~1 fewer row than the source.  On
~4.55M rows across 30 years this is ~30 rows (<0.001%); it is flagged via
:func:`load_all_fields_production` logging rather than silently fabricated.
"""

from __future__ import annotations

import logging
import pickle  # nosec B403
from pathlib import Path
from typing import Optional

import pandas as pd

from worldenergydata.common.data_resolver import get_module_data_safe

logger = logging.getLogger(__name__)

# Positional OGOR-A column schema (19 columns), matching
# ``lower_tertiary.v30_reproducer.load_ogor_production``.
OGOR_COLUMN_NAMES = [
    "LEASE_NUMBER",
    "COMPLETION_NAME",
    "PRODUCTION_DATE",  # YYYYMM integer
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
    "BOEM_FIELD",  # field code used for all-fields grouping
    "INJECTION_VOLUME",
    "PROD_INTERVAL_CD",
    "FIRST_PROD_DATE",
    "UNIT_AGT_NUMBER",
    "UNIT_ALOC_SUFFIX",
]

_N_COLS = len(OGOR_COLUMN_NAMES)
_DEFAULT_SUBDIR = "historical_production_yearly"


def _load_pickle_safe(path: Path) -> Optional[pd.DataFrame]:
    """Load a pickled DataFrame, returning ``None`` for LFS stubs/errors."""
    try:
        with open(path, "rb") as f:
            header = f.read(40)
        if b"version https://git-lfs" in header:
            logger.warning("LFS stub (not materialized): %s", path)
            return None
        with open(path, "rb") as f:
            obj = pickle.load(f)  # nosec B301
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error loading %s: %s", path, exc)
        return None

    if not isinstance(obj, pd.DataFrame):
        logger.warning("Not a DataFrame: %s", path)
        return None
    return obj


def load_ogor_bin(path: Path) -> pd.DataFrame:
    """Load one OGOR-A ``.bin`` pickle and positionally re-label its columns.

    Parameters
    ----------
    path:
        Path to an ``ogora{year}delimit.bin`` pickle.

    Returns
    -------
    pd.DataFrame
        DataFrame with the canonical :data:`OGOR_COLUMN_NAMES` columns.
        Returns an empty (correctly-typed) frame when the file is an LFS
        stub, unreadable, or does not have the expected 19 columns.
    """
    path = Path(path)
    if not path.exists():
        logger.warning("OGOR file not found: %s", path)
        return pd.DataFrame(columns=OGOR_COLUMN_NAMES)

    df = _load_pickle_safe(path)
    if df is None:
        return pd.DataFrame(columns=OGOR_COLUMN_NAMES)

    if df.shape[1] != _N_COLS:
        logger.warning(
            "Unexpected column count %d (need %d) in %s — skipping",
            df.shape[1],
            _N_COLS,
            path.name,
        )
        return pd.DataFrame(columns=OGOR_COLUMN_NAMES)

    # Positional re-label. If the file already carries the canonical names
    # (e.g. a non-corrupted source), this is a harmless rename.
    df = df.copy()
    df.columns = OGOR_COLUMN_NAMES
    return df


def to_runner_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Adapt raw OGOR-A columns to the AllFieldsRunner input schema.

    Produces the columns the runner detects and aggregates:
    ``FIELD_NAME_CODE``, ``LEASE_NUMBER``, ``API_WELL_NUMBER``,
    ``PROD_YEAR``, ``MON_O_PROD_VOL``, ``MON_G_PROD_VOL``,
    ``MON_WTR_PROD_VOL``, ``DAYS_ON_PROD``.
    """
    out_cols = [
        "FIELD_NAME_CODE",
        "LEASE_NUMBER",
        "API_WELL_NUMBER",
        "PROD_YEAR",
        "MON_O_PROD_VOL",
        "MON_G_PROD_VOL",
        "MON_WTR_PROD_VOL",
        "DAYS_ON_PROD",
    ]
    if df.empty:
        return pd.DataFrame(columns=out_cols)

    out = pd.DataFrame(index=df.index)

    # Field code (BOEM_FIELD) and identifiers — strip whitespace/quotes.
    out["FIELD_NAME_CODE"] = (
        df["BOEM_FIELD"].astype(str).str.replace('"', "", regex=False).str.strip()
    )
    out["LEASE_NUMBER"] = (
        df["LEASE_NUMBER"]
        .astype(str)
        .str.replace('"', "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.upper()
    )
    out["API_WELL_NUMBER"] = (
        df["API_WELL_NUMBER"].astype(str).str.replace('"', "", regex=False).str.strip()
    )

    # Production year from YYYYMM integer.
    prod_date = pd.to_numeric(df["PRODUCTION_DATE"], errors="coerce")
    out["PROD_YEAR"] = (prod_date // 100).astype("Int64")

    # Volumes and days — numeric, NaN -> 0.
    for col in ("MON_O_PROD_VOL", "MON_G_PROD_VOL", "MON_WTR_PROD_VOL", "DAYS_ON_PROD"):
        out[col] = pd.to_numeric(
            df[col].astype(str).str.replace('"', "", regex=False).str.strip(),
            errors="coerce",
        ).fillna(0.0)

    return out[out_cols]


def load_all_fields_production(
    data_dir: Optional[Path] = None,
    start_year: int = 1996,
    end_year: int = 2025,
) -> pd.DataFrame:
    """Load and concatenate all yearly OGOR-A bins into runner-ready data.

    Parameters
    ----------
    data_dir:
        Directory containing ``ogora{year}delimit.bin`` files.  Defaults to
        ``<bsee module>/bin/historical_production_yearly`` (resolved via the
        repo data resolver, which follows the materialized-data symlink).
    start_year, end_year:
        Inclusive year range to load.

    Returns
    -------
    pd.DataFrame
        Concatenated production in the AllFieldsRunner schema.  Empty (with
        correct columns) when no files are found.
    """
    if data_dir is None:
        data_dir = get_module_data_safe("bsee") / "bin" / _DEFAULT_SUBDIR
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
        frames.append(to_runner_schema(raw))
        loaded += 1

    if not frames:
        logger.warning("No OGOR production bins loaded from %s", data_dir)
        return to_runner_schema(pd.DataFrame())

    result = pd.concat(frames, ignore_index=True)
    logger.info(
        "Loaded %d OGOR years (%d missing/empty) from %s — %d rows. "
        "Note: ~1 row/file lost to source header-corruption.",
        loaded,
        missing,
        data_dir,
        len(result),
    )
    return result
