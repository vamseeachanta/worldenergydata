"""Annual lease cohorts and five-complete-calendar-year arithmetic means."""

import pandas as pd
from lease_analysis import (
    ALL,
    BANDS,
    COHORT_END,
    COHORT_START,
    DAYS_PER_YEAR,
    FOLLOWUP_YEARS,
    WINDOW_MONTHS,
    YEARS,
    groups,
    month_lag,
    pct,
)

TOTAL = "All water depths"


def observation(metric, band, year, leases, events, value, availability="verified"):
    band = TOTAL if band == ALL else band
    return {
        "group": f"{metric}|{band}",
        "metric": metric,
        "band": band,
        "year": int(year),
        "partial": int(int(year) == YEARS[-1]),
        "leases": leases,
        "events": events,
        "availability": availability,
        "value": value,
    }


def with_trends(rows):
    data = pd.DataFrame(rows).sort_values(["group", "year"], ignore_index=True)
    if data.duplicated(["group", "year"]).any():
        raise ValueError("Duplicate annual observation")
    if data.groupby("group").year.diff().dropna().ne(1).any():
        raise ValueError("Missing calendar year in series")
    complete = data.value.where(data.partial.eq(0) & data.availability.eq("verified"))
    data["moving_average"] = complete.groupby(data.group).transform(
        lambda values: values.rolling(5, min_periods=5).mean()
    )
    data["events"] = data.events.astype("Int64")
    return data


def annual_series(frame, older):
    """Use individual leases for both the depth totals and all conditional medians."""
    if not frame.depth_band.isin(BANDS[:4]).all():
        raise ValueError("Unallocated lease-block depth in annual series")
    rows = []
    statuses = sorted(frame.status_code.unique())
    for year, band, g in groups(frame, YEARS):
        if not year.isdecimal() or band == "Unknown":
            continue
        n = len(g)
        rows.append(observation("effective_leases", band, year, n, n, n))
        if band == ALL:
            for code in statuses:
                count = int(g.status_code.eq(code).sum())
                rows.append(
                    observation(f"status_{code}", band, year, n, count, pct(count, n))
                )

    spud_days = (older.exploration_spud - older.effective_date).dt.days
    if spud_days.lt(0).any():
        raise ValueError("First qualifying spud precedes lease effectiveness")
    by_anniversary = older.exploration_spud.le(
        older.effective_date + pd.DateOffset(years=FOLLOWUP_YEARS)
    )
    elapsed = month_lag(older.effective_date, older.first_oil_month)
    timed = older.assign(
        observed_days=spud_days,
        within_days=spud_days.where(by_anniversary),
        crude_months=elapsed.where(elapsed.between(0, WINDOW_MONTHS - 1)),
    )
    for year, band, g in groups(timed, range(COHORT_START, COHORT_END + 1)):
        if not year.isdecimal() or band == "Unknown":
            continue
        for share, timing, sample, units_per_year in (
            (
                "spud_share_observed",
                "spud_years_observed",
                g.observed_days,
                DAYS_PER_YEAR,
            ),
            ("spud_share_5y", "spud_years_5y", g.within_days, DAYS_PER_YEAR),
            ("crude_share_5y", "crude_years_5y", g.crude_months, 12),
        ):
            n, events = len(g), int(sample.count())
            rows.append(observation(share, band, year, n, events, pct(events, n)))
            median = sample.median() / units_per_year if events else None
            rows.append(observation(timing, band, year, n, events, median))
    return with_trends(rows)


def write_annual_trends(output, frame, older):
    annual_series(frame, older).to_csv(
        output / "annual_trends.csv", index=False, lineterminator="\n"
    )
