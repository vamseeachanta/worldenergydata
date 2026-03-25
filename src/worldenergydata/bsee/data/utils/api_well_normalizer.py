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


def normalize_api_column_name(df: pd.DataFrame) -> pd.DataFrame:
    """Rename 'API Well Number' (with spaces) to 'API_WELL_NUMBER' if present.

    Returns a new DataFrame; the original is not mutated.
    """
    if "API Well Number" in df.columns:
        return df.rename(columns={"API Well Number": "API_WELL_NUMBER"})
    return df.copy()
