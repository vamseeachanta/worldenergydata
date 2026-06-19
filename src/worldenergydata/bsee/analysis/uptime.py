"""ABOUTME: Per-well production uptime from BSEE OGOR-A ``DAYS_ON_PROD``.
ABOUTME: Uptime = producing days delivered / calendar days in the online window.

The one absent first-class metric in the existing per-well primitives is
**uptime** — the fraction of calendar time a well actually produced once it came
online. BSEE OGOR-A reports a ``DAYS_ON_PROD`` integer per well-month (the number
of calendar days the completion produced that month). Summing it over a well's
online window and dividing by the calendar days spanned gives a deterministic,
data-grounded availability fraction.

Flag-don't-fake: a well-month with a null/blank ``DAYS_ON_PROD`` is *counted as
missing* (added to ``missing_months``) and excluded from the numerator rather
than silently treated as zero or as a full month. When too many months are
missing the row is flagged ``low_confidence`` so callers can surface the gap
instead of presenting a fabricated uptime.
"""

from __future__ import annotations

import calendar

import pandas as pd

# A well whose online window has more than this fraction of months missing a
# DAYS_ON_PROD value is flagged: the uptime is computed on the months we have,
# but the gap is reported rather than hidden.
_LOW_CONFIDENCE_MISSING_FRACTION = 0.10


def _calendar_days(period_start: pd.Timestamp, period_end: pd.Timestamp) -> int:
    """Inclusive calendar-day span between two month-start timestamps.

    Both endpoints are month-starts; the window runs from the first day of
    ``period_start``'s month to the last day of ``period_end``'s month.
    """
    last_day = calendar.monthrange(period_end.year, period_end.month)[1]
    window_end = period_end.replace(day=last_day)
    return (window_end - period_start).days + 1


def compute_uptime(
    prod_df: pd.DataFrame,
    api_col: str = "API_WELL_NUMBER",
    days_col: str = "DAYS_ON_PROD",
    date_col: str = "date",
    oil_col: str = "MON_O_PROD_VOL",
) -> pd.DataFrame:
    """Per-well uptime from OGOR-A ``DAYS_ON_PROD`` over the online window.

    Parameters
    ----------
    prod_df : pd.DataFrame
        OGOR-A monthly production rows (one row per well-month). Must carry the
        ``api_col``, ``days_col``, ``date_col`` columns; ``oil_col`` is used to
        bound the online window to producing months only.
    api_col, days_col, date_col, oil_col : str
        Column names (defaults match the OGOR-A schema in
        :data:`worldenergydata.lower_tertiary.ops_timeline.OGOR_COLUMNS`).

    Returns
    -------
    pd.DataFrame
        One row per well, columns:
          - ``API_WELL_NUMBER``
          - ``producing_days`` : Σ DAYS_ON_PROD over producing months (int)
          - ``calendar_days`` : inclusive calendar span first→last producing
            month (int)
          - ``online_months`` : count of producing well-months
          - ``missing_days_months`` : producing months with a null/blank
            DAYS_ON_PROD (excluded from the numerator)
          - ``uptime`` : producing_days / calendar_days in [0, 1], or NaN when
            calendar_days is 0
          - ``uptime_pct`` : uptime * 100
          - ``low_confidence`` : True when DAYS_ON_PROD is missing for more than
            10% of the online months (flag-don't-fake)

    Notes
    -----
    The denominator is the *online window* (first producing month → last
    producing month), not field life: a well that came online late is not
    penalised for the years before first oil. Months with zero oil inside the
    window still count toward the calendar denominator (they are real downtime).
    """
    cols = ["API_WELL_NUMBER", "producing_days", "calendar_days", "online_months",
            "missing_days_months", "uptime", "uptime_pct", "low_confidence"]
    if prod_df is None or prod_df.empty:
        return pd.DataFrame(columns=cols)

    df = prod_df.copy()
    df[api_col] = df[api_col].astype(str).str.strip()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col])

    # Bound the window to producing months (oil > 0). A well that has never
    # produced oil has no online window and is omitted.
    oil = pd.to_numeric(df[oil_col], errors="coerce").fillna(0.0)
    df = df[oil > 0]
    if df.empty:
        return pd.DataFrame(columns=cols)

    # DAYS_ON_PROD: coerce; track which producing months are missing it.
    raw_days = pd.to_numeric(df[days_col], errors="coerce")
    df = df.assign(_days=raw_days, _days_missing=raw_days.isna())

    rows: list[dict] = []
    for api, grp in df.groupby(api_col):
        # Collapse to one record per month (a well can have multiple completion
        # rows per month; sum producing days and OR the missing flag).
        grp = grp.assign(_month=grp[date_col].dt.to_period("M").dt.to_timestamp())
        by_month = grp.groupby("_month").agg(
            days=("_days", "sum"),
            missing=("_days_missing", "any"),
        )
        first_month = by_month.index.min()
        last_month = by_month.index.max()
        cal_days = _calendar_days(first_month, last_month)
        producing_days = float(by_month["days"].fillna(0.0).sum())
        online_months = int(len(by_month))
        missing_months = int(by_month["missing"].sum())
        uptime = producing_days / cal_days if cal_days > 0 else float("nan")
        low_conf = (
            online_months > 0
            and (missing_months / online_months) > _LOW_CONFIDENCE_MISSING_FRACTION
        )
        rows.append(
            {
                "API_WELL_NUMBER": api,
                "producing_days": int(producing_days),
                "calendar_days": int(cal_days),
                "online_months": online_months,
                "missing_days_months": missing_months,
                "uptime": uptime,
                "uptime_pct": uptime * 100.0 if uptime == uptime else float("nan"),
                "low_confidence": bool(low_conf),
            }
        )

    out = pd.DataFrame(rows, columns=cols)
    return out.sort_values("API_WELL_NUMBER").reset_index(drop=True)
