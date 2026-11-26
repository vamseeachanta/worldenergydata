"""Compare r12 aggregate tables and the readings displayed in the Part 2 article."""

import re

import pandas as pd

# The remaining r12 files describe input schemas, source files, or individual wells.
GROUP_COLUMNS = {
    "table1": ["Rig type"],
    "fig-p1-new-well-permits-by-rig-type": ["year"],
    "new-well-permits-by-water-depth": ["year"],
    "pies-rig": ["year", "category"],
    "pies-depth": ["year", "category"],
    "map-summary": ["period"],
    "map-selection": ["period"],
    "map-windows": ["start", "end"],
    "new-wells-by-year": ["year"],
    "new-wells-trend": ["year"],
    "wti-annual": ["year"],
    "days-summary": ["activity", "band"],
    "exclusions": ["source", "rule"],
    "repeat-key-sensitivity": ["activity", "band"],
    "subtype-activity": ["activity", "primary", "subtype"],
}

DEPTH_BANDS = ("Under 100 m", "100 to 500 m", "500 to 1,500 m", "1,500 m and deeper")
COUNT_COLUMNS = {
    "New-well permits, 2005 to 2026 (-)", *DEPTH_BANDS, *(f"{band} (-)" for band in DEPTH_BANDS),
    "under_100_m", "100_to_500_m", "500_to_1500_m", "1500_m_and_deeper",
    "Jack-up", "Drillship", "Semisubmersible", "DP semisubmersible", "Platform rig", "Submersible", "Other",
    "permits", "total", "selected", "mapped", "missing_or_outside_coordinates",
    "records", "n", "missing_invalid_days", "nonpositive_days", "excluded_days", "latest_key_n", "submissions",
}
DIFFERENCE_UNITS = {
    **dict.fromkeys(COUNT_COLUMNS, "count"),
    **{f"{name} (3-year mean)": "wells/year" for name in (*DEPTH_BANDS, "total")},
    "share_percent": "percentage points",
    "Median water depth (m)": "m",
    "median_m": "m",
    "WTI (USD/bbl)": "USD/bbl",
    "wti_usd_per_bbl": "USD/bbl",
    "median_days": "days",
    "latest_key_median_days": "days",
    "q1_days": "days",
    "q3_days": "days",
}


def majority_start(counts, totals):
    """First year of a >50% share in every subsequent full year (Figure 2 or 4)."""
    majority = (counts * 2 > totals).sort_index().loc[:2025]
    since = majority.iloc[::-1].cummin()
    years = since.index[since]
    return years.min() if len(years) else None


def article_cells(tables, no_date):
    """Additional readings from r12 sections 1 to 2 and Appendix B, at printed precision."""
    years = "2005 to 2025"
    rows = [
        ("All years", "First permits without readable requested spud date", "count", no_date),
        (years, "New wells started", "count", tables["new-wells-by-year"].total.sum()),
    ]
    for period, row in tables["map-summary"].set_index("period").iterrows():
        deep = row["500 to 1,500 m"] + row["1,500 m and deeper"]
        for label, n in [("under 100 m", row["Under 100 m"]), ("in 500 m or more", deep)]:
            rows.append((period, f"New wells {label} (%)", "percentage points", round(100 * n / row.total, 1)))

    # build_r12.trend_note adds the two rounded deep-band means before formatting.
    trend = tables["new-wells-trend"].set_index("year")
    for year in (2014, 2017):
        row = trend.loc[year]
        group = f"{year - 2} to {year}"
        shallow = row["Under 100 m (3-year mean)"]
        deep = row["500 to 1,500 m (3-year mean)"] + row["1,500 m and deeper (3-year mean)"]
        for label, value in [("under 100 m", shallow), ("in 500 m or more", deep)]:
            rows.append((group, f"New wells/year {label} (figure note)", "wells/year", round(value, 1)))
            rows.append((group, f"New wells/year {label} (rounded in text)", "wells/year", round(value)))

    rigs = tables["fig-p1-new-well-permits-by-rig-type"].set_index("year")
    depth = tables["new-well-permits-by-water-depth"].set_index("year")
    deep = depth["500_to_1500_m"] + depth["1500_m_and_deeper"]
    rows.extend([
        (years, "First full year of sustained drillship majority", "years", majority_start(rigs.Drillship, rigs.total)),
        (years, "First full year of sustained 500 m or deeper majority", "years", majority_start(deep, depth.permits)),
    ])
    repeat = tables["repeat-key-sensitivity"]
    changes = (repeat.latest_key_median_days - repeat.median_days).abs().dropna()
    rows.extend([
        (years, "Comparable repeat-key cell medians", "count", len(changes)),
        (years, "Changed repeat-key cell medians", "count", changes.ne(0).sum()),
        (years, "Largest absolute repeat-key median change (d)", "days", changes.max()),
    ])
    return rows


def aggregate_cells(directory, no_date):
    tables = {}
    rows = []
    for name, keys in GROUP_COLUMNS.items():
        frame = pd.read_csv(directory / f"{name}.csv", thousands=",")
        tables[name] = frame
        # Explicit row labels keep differences stable across sorting or a new subgroup.
        groups = frame[keys].astype(str).agg(" | ".join, axis=1)
        for column in frame.drop(columns=keys):
            if column not in DIFFERENCE_UNITS:
                raise ValueError(f"{name}: unknown difference unit for {column!r}")
            unit = DIFFERENCE_UNITS[column]
            for group, value in zip(groups, pd.to_numeric(frame[column], errors="raise")):
                rows.append((name, group, column, unit, value))
    rows.extend(("article", *row) for row in article_cells(tables, no_date))
    index = ["table", "group", "metric", "difference_unit"]
    return pd.DataFrame(rows, columns=[*index, "value"]).set_index(index, verify_integrity=True)["value"]


def no_spud_count(directory, *, historical=False):
    path = directory / "record-counts.csv"
    if historical and not path.exists():
        # The original r12 release recorded this APD count only in section 1.
        rules = directory.parent / "counting-rules.md"
        text = " ".join(rules.read_text(encoding="utf-8").split())
        counts = re.findall(
            r"(?<!\S)(\d+|\d{1,3}(?:,\d{3})+) wells whose first New Well permit gives no requested spud date\b",
            text,
        )
        if len(counts) != 1:
            raise ValueError(f"{rules}: expected one count of first permits without a requested spud date")
        return int(counts[0].replace(",", ""))
    records = pd.read_csv(path).set_index(
        ["source", "disposition", "reason"], verify_integrity=True
    )
    return records.loc[("APD", "excluded", "no_spud_date"), "records"]


def compare_tables(old_dir, new_dir):
    """Compare every numeric aggregate. Missing cells stay blank on either side."""
    old = aggregate_cells(old_dir, no_spud_count(old_dir, historical=True)).rename("r12")
    new = aggregate_cells(new_dir, no_spud_count(new_dir)).rename("r15")
    comparison = pd.concat([old, new], axis=1)
    comparison["difference"] = (comparison.r15 - comparison.r12).round(12)
    return comparison.reset_index()
