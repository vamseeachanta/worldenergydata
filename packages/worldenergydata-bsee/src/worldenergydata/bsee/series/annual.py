"""Annual observations and five consecutive calendar-year means for BSEE series."""

import numpy as np
import pandas as pd

from worldenergydata.bsee.half_decade import _COLORS, BANDS, depth_band

__all__ = ["BANDS", "BAND_COLORS", "depth_band", "with_trends"]

BAND_COLORS = dict(zip(BANDS, _COLORS))


def _calendar_years(values):
    years = pd.to_numeric(values, errors="raise")
    if not (years.between(1, 9999) & years.mod(1).eq(0)).fillna(False).all():
        raise ValueError("Expected an integral calendar year")
    return years.astype(int)


def with_trends(rows, *, partial_year=None):
    """Sort observation records and append a trailing mean within each group.

    Required fields are group, year and value. A missing year or value, a
    partial observation, or an unavailable cell interrupts the five-year
    window. Additional columns are carried through to the result DataFrame.
    """
    data = pd.DataFrame(rows).copy()
    if data.empty and not len(data.columns):
        data = pd.DataFrame(columns=["group", "year", "value"])
    if not {"group", "year", "value"}.issubset(data.columns):
        raise ValueError("Annual observations require group, year and value")
    if data["group"].isna().any():
        raise ValueError("Annual observations require a group")
    data["year"] = _calendar_years(data["year"])
    data = data.sort_values(["group", "year"], ignore_index=True)
    if data.duplicated(["group", "year"]).any():
        raise ValueError("Duplicate annual observation")

    if "partial" not in data:
        data["partial"] = 0
    partial = pd.to_numeric(data["partial"].fillna(0), errors="raise")
    if not partial.isin([0, 1]).all():
        raise ValueError("Expected partial to be 0 or 1")
    if partial_year is not None:
        (cutoff,) = _calendar_years(pd.Series([partial_year]))
        partial = partial.where(data.year.ne(cutoff), 1)
    data["partial"] = partial.astype(int)
    if "availability" not in data:
        data["availability"] = "verified"
    availability = data["availability"].fillna("verified")
    if not availability.isin(["verified", "unavailable"]).all():
        raise ValueError("Expected verified or unavailable availability")
    data["availability"] = availability
    values = pd.to_numeric(data["value"], errors="raise")
    if np.isinf(values.dropna()).any():
        raise ValueError("Expected finite annual values")
    data["value"] = values.where(data.availability.eq("verified"))
    complete = data.value.where(data.partial.eq(0))
    rolling = complete.groupby(data.group).transform(
        lambda group: group.rolling(5, min_periods=5).mean()
    )
    # Five sorted distinct observations span four years only if none is missing.
    consecutive = data.groupby("group").year.diff(4).eq(4)
    data["moving_average"] = rolling.where(consecutive)
    return data
