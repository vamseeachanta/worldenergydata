"""Shared API well number normalizer for cross-dataset joins (WRK-116)."""

from __future__ import annotations

import re

import pandas as pd

_TRAILING_DOT_ZERO = re.compile(r"\.0$")


def normalize_api_well_number(series: pd.Series) -> pd.Series:
    """Normalize API well numbers to stripped strings without trailing .0.

    Handles: float64 -> str (drop .0), int64 -> str, object str cleanup,
    and whitespace stripping.  NaN/None values are preserved as NaN.

    Args:
        series: A pandas Series containing API well numbers in any format.

    Returns:
        Series of string-typed API well numbers, NaN preserved.
    """
    result = series.astype(str).str.strip()
    result = result.str.replace(_TRAILING_DOT_ZERO, "", regex=True)
    # Restore NaN for values that converted to the literal strings "nan" / "None"
    result = result.replace({"nan": pd.NA, "None": pd.NA, "<NA>": pd.NA})
    return result


def api_matches(series: pd.Series, api: object) -> pd.Series:
    """Boolean mask of ``series`` entries matching ``api``, dtype-safely.

    Use this where the result is combined with other conditions; use
    :func:`select_by_api` where a filtered frame is wanted. See that function
    for why a plain ``==`` is unsafe here.
    """
    wanted = normalize_api_well_number(pd.Series([api])).iloc[0]
    if pd.isna(wanted):
        # A null argument must match nothing, rather than matching every row
        # whose own API is null.
        return pd.Series(False, index=series.index)
    return normalize_api_well_number(series) == wanted


def select_by_api(
    df: pd.DataFrame,
    api: object,
    column: str = "API_WELL_NUMBER",
) -> pd.DataFrame:
    """Rows of ``df`` whose ``column`` matches ``api``, comparing dtype-safely.

    ``df[column] == api`` is the obvious spelling and it is a trap. The API
    column arrives as int64 from the BSEE ``.bin`` pickles, as float64 wherever
    heterogeneous frames have been concatenated, and as str wherever it has
    been treated as the identifier it is. Comparing across two of those
    evaluates to all-``False`` *without raising*, so the filter silently yields
    zero rows and the well reports as having no data at all -- a type mismatch
    that reads exactly like absent coverage.

    Both sides are normalised through :func:`normalize_api_well_number` first,
    so int, float and string spellings of the same API all match.

    .. note:: This does not recover a leading zero lost to integer storage.
       An API held as int64 has already dropped it before this function sees
       it; that is a storage concern, not a comparison one.
    """
    if column not in df.columns:
        raise KeyError(
            f"{column!r} not in frame; have: {', '.join(map(str, df.columns))}"
        )
    return df[api_matches(df[column], api)]


def normalize_api_column_name(df: pd.DataFrame) -> pd.DataFrame:
    """Rename 'API Well Number' (with spaces) to 'API_WELL_NUMBER' if present.

    Returns a new DataFrame; the original is not mutated.
    """
    if "API Well Number" in df.columns:
        return df.rename(columns={"API Well Number": "API_WELL_NUMBER"})
    return df.copy()
