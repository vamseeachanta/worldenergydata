"""Aggregate disjoint rig-count records and calculate trailing means."""

import math
from numbers import Integral, Number

import pandas as pd
from pandas.api.types import is_any_real_numeric_dtype, is_bool_dtype, is_numeric_dtype


def aggregate_rig_counts(df: pd.DataFrame, *, window: int) -> pd.DataFrame:
    """Return sorted calendar-date totals and a full-window trailing mean.

    ``df`` must contain ``date`` and ``rig_count`` columns. Counts must be
    finite, nonnegative whole numbers; dates must be timezone-naive dates or
    ISO 8601 date strings. Locale-dependent strings such as DD/MM/YYYY are
    rejected. Times within a calendar date are combined.

    Each row must represent a disjoint part of the requested population.
    Filter to the desired population before calling; combining overlapping
    totals and detail records would double count rigs. No deduplication or
    population-completeness inference is performed.

    Known loader limit: ``load_summary`` and ``load_pivot_table`` replace
    missing or unparseable counts with zero before aggregation. Validate
    source counts before loading; aggregation cannot distinguish those
    replacements from observed zeros.

    The required ``window`` counts observed dates, not elapsed weeks. Absent
    dates are not filled. Incomplete windows yield NaN; an observed zero is
    retained. Input data are not modified. Output columns are ``date``,
    ``rig_count`` (the date total) and ``rolling_mean`` (in rigs).

    Reference: NIST/SEMATECH e-Handbook of Statistical Methods, section
    6.4.2.1, Single Moving Average, online edition accessed 2026-10-19,
    https://www.itl.nist.gov/div898/handbook/pmc/section4/pmc421.htm
    For disjoint counts c[d,j], define X[d] = sum_j c[d,j]. The reference's
    equation is M[t] = (X[t] + ... + X[t-N+1]) / N. N is a required input;
    no smoothing period or physical acceptance limit is assumed.
    """
    # A window is a positive observation count, as defined in the reference.
    if isinstance(window, bool) or not isinstance(window, Integral) or window <= 0:
        raise ValueError("window must be a positive integer observation count")
    for column in ("date", "rig_count"):
        if column not in df.columns:
            raise ValueError(f"missing required column: {column}")

    counts = df["rig_count"]
    if (
        not is_any_real_numeric_dtype(counts.dtype)
        or is_bool_dtype(counts.dtype)
        or counts.isna().any()
        or not counts.map(math.isfinite).all()
        # Zero is the empty-set count; remainder modulo one tests integrality.
        # These are count-domain definitions, not empirical acceptance limits.
        or (counts < 0).any()
        or (counts % 1 != 0).any()
    ):
        raise ValueError("rig_count must contain finite nonnegative whole numbers")

    try:
        if is_numeric_dtype(df["date"].dtype) or any(
            isinstance(value, Number) for value in df["date"]
        ):
            raise ValueError("numeric epochs are not calendar dates")
        dates = df["date"].map(lambda value: pd.to_datetime(value, format="ISO8601"))
        if dates.isna().any() or dates.dt.tz is not None:
            raise ValueError("missing or timezone-aware date")
        dates = dates.dt.normalize()
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError(
            "date must contain valid timezone-naive calendar dates"
        ) from exc

    totals = (
        pd.DataFrame({"date": dates, "rig_count": counts})
        .groupby("date", as_index=False, sort=True)["rig_count"]
        .sum()
    )
    totals["rolling_mean"] = (
        totals["rig_count"].rolling(window=int(window), min_periods=int(window)).mean()
    )
    return totals
