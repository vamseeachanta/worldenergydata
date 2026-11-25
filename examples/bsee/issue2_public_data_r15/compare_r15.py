"""Compare r12 aggregate tables and the readings displayed in the Part 2 article."""

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

# Most cells are counts. These columns carry a different unit for the difference.
DIFFERENCE_UNITS = {
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
            unit = "wells/year" if column.endswith("(3-year mean)") else DIFFERENCE_UNITS.get(column, "count")
            for group, value in zip(groups, pd.to_numeric(frame[column], errors="raise")):
                rows.append((name, group, column, unit, value))
    rows.extend(("article", *row) for row in article_cells(tables, no_date))
    index = ["table", "group", "metric", "difference_unit"]
    return pd.DataFrame(rows, columns=[*index, "value"]).set_index(index, verify_integrity=True)["value"]


def compare_tables(old_dir, new_dir):
    """Compare every numeric aggregate. Missing cells stay blank on either side."""
    # r12 counting-rules.md, §1: 10 first permits without a requested spud date.
    # Its published exclusions.csv only covers APM and Borehole.
    old = aggregate_cells(old_dir, 10).rename("r12")
    records = pd.read_csv(new_dir / "record-counts.csv").set_index(
        ["source", "disposition", "reason"], verify_integrity=True
    )
    no_date = records.loc[("APD", "excluded", "no_spud_date"), "records"]
    new = aggregate_cells(new_dir, no_date).rename("r15")
    comparison = pd.concat([old, new], axis=1)
    comparison["difference"] = (comparison.r15 - comparison.r12).round(12)
    return comparison.reset_index()
