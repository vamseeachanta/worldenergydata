#!/usr/bin/env python3
"""Publish elapsed spud-to-TD calendar intervals from the saved workbook.

The historical URL remains available. Calendar dates cannot establish active
rig time or causal learning; legacy DRILLING_DAYS is intentionally not used.
"""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
import site_nav  # noqa: E402

DEFAULT_SOURCE = (
    PROJECT_ROOT
    / "docs/modules/bsee/analysis/production/FDAS_V30"
    / "drilling_and_completion_days.xlsx"
)
REPORTS_DIR = PROJECT_ROOT / "reports/lower_tertiary"
CSV_PATH = REPORTS_DIR / "lt_drilling_insights.csv"
HTML_PATH = REPORTS_DIR / "drilling_insights.html"
CALENDAR = "spud_to_td_calendar_days"
BASIS = "calendar_elapsed_spud_to_td"


def load_wells(source: Path) -> pd.DataFrame:
    """Keep named wellbores; derive nonnegative calendar spans from dates.

    Source: issue #1077 (2026), definition correction; Python 3.13 (2024),
    date subtraction: https://docs.python.org/3.13/library/datetime.html#date-objects
    Zero is valid for equal dates; missing or reversed dates remain null.
    """
    df = pd.read_excel(source, sheet_name="Sheet1")
    df = df[df["LEASE_NAME"].notna()].copy().reset_index(drop=True)
    for column in ("WELL_SPUD_DATE", "TOTAL_DEPTH_DATE"):
        df[column] = pd.to_datetime(df[column], format="%m/%d/%Y", errors="coerce")
    spans = (df["TOTAL_DEPTH_DATE"] - df["WELL_SPUD_DATE"]).dt.days
    df[CALENDAR] = spans.where(spans >= 0)
    return df


def write_csv(df: pd.DataFrame, path: Path) -> None:
    """Export explicit interval names and basis, retaining blank unknowns."""
    out = pd.DataFrame(
        {
            "field": df["LEASE_NAME"],
            "surf_lease_num": df.get("SURF_LEASE_NUM"),
            "water_depth_ft": df.get("WATER_DEPTH"),
            "api_well_number": df["API_WELL_NUMBER"],
            "well_name": df["WELL_NAME"],
            "spud_date": df["WELL_SPUD_DATE"].dt.strftime("%Y-%m-%d"),
            "total_depth_date": df["TOTAL_DEPTH_DATE"].dt.strftime("%Y-%m-%d"),
            CALENDAR: df[CALENDAR],
            "legacy_reported_completion_days": df.get("COMPLETION_DAYS"),
            "max_bh_total_md_ft": df.get("MAX_BH_TOTAL_MD"),
            "max_well_bore_tvd_ft": df.get("MAX_WELL_BORE_TVD"),
            "max_drill_fluid_wgt_ppg": df.get("MAX_DRILL_FLUID_WGT"),
            "basis": BASIS,
        }
    )
    out = out.sort_values(["field", "well_name"], kind="stable")
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False)


def compute_stats(df: pd.DataFrame) -> dict:
    """Describe the date-qualified population without a rig-time inference."""
    spans = df[CALENDAR].dropna()
    return {
        "n_wellbores": len(df),
        "n_calendar": len(spans),
        "n_missing": int(
            df[["WELL_SPUD_DATE", "TOTAL_DEPTH_DATE"]].isna().any(axis=1).sum()
        ),
        "n_reversed": int((df["TOTAL_DEPTH_DATE"] < df["WELL_SPUD_DATE"]).sum()),
        "total_calendar_days": float(spans.sum()) if len(spans) else float("nan"),
        "median_calendar_days": float(spans.median()) if len(spans) else float("nan"),
        "fields": df.groupby("LEASE_NAME")[CALENDAR].agg(["count", "median", "sum"]),
    }


def _number(value) -> str:
    return "—" if pd.isna(value) else f"{value:,.1f}"


def render_html(s: dict, source: Path) -> str:
    """Render definitions and population limits beside the reported intervals."""
    # The historical counts and totals are evidence quoted in issues #1077 and
    # #1062 (2026), not an independently validated membership reconciliation.
    # Hand calculation: 211 - 184 = 27; these are different cohorts and metrics.
    rows = "".join(
        f"<tr><td>{html.escape(str(field))}</td><td>{int(r['count'])}</td>"
        f"<td>{_number(r['median'])}</td><td>{_number(r['sum']) if r['count'] else '—'}</td></tr>"
        for field, r in s["fields"].iterrows()
    )
    return f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Well calendar cycle time</title>
<style>body{{font:1em system-ui;max-width:70em;margin:auto;padding:2em;line-height:1.6}}
table{{border-collapse:collapse}}td,th{{border:1px solid #aaa;padding:.5em;text-align:left}}</style>
<main><h1>Well calendar cycle time</h1>
<p>The former drilling learning-curve page now describes elapsed calendar time.
Among {s['n_wellbores']} named development wellbores in the saved workbook,
{s['n_calendar']} have both dates in chronological order. Their median spud-to-TD
interval is {_number(s['median_calendar_days'])} calendar days and their sum is
{_number(s['total_calendar_days'])} calendar days. The sum adds wellbore intervals;
it can count overlapping dates and is not a measure of rig occupancy.</p>
<h2>Revision history</h2>
<table><tr><th>Revision</th><th>Date</th><th>Change and reason</th></tr>
<tr><td>1</td><td>2026-10-19</td><td>Replace rig-time and learning claims with dated calendar intervals.</td></tr></table>
<h2>Definition and population</h2>
<p>Interval = total-depth date minus spud date, in elapsed calendar days, with no
inclusive-day addition. A same-day interval is zero. {s['n_missing']} rows have
missing or invalid dates; {s['n_reversed']} have TD before spud. Those rows remain
in the download with blank intervals and are excluded from interval statistics.
Rows without a lease name (blank and totals rows) are excluded. No cutoff year,
completion status, depth or duration threshold selects this date-qualified population.</p>
<p>The benchmark uses a different endpoint:
<code>spud_to_completion_calendar_days</code> = first completion marker minus spud;
<code>completion_days</code> = first oil minus first completion marker. Both are
calendar components including suspension and waiting, rather than active drilling time.</p>
<h2>Historical 184 versus 211 comparison</h2>
<p>Issues #1077 and #1062 (2026) record the former 184-wellbore / 11,124-day claim
and the article's 211-well / 21,944-day claim. The former selected positive legacy
workbook durations; the current count above instead requires valid spud/TD dates.
The article's population has 27 more entries, but different selection rules and
day definitions prevent interpreting this as 27 omitted drilling records.
Exact paired membership and the article's operational day basis are NOT_EVALUATED:
the saved workbook alone does not establish either. The producing-well benchmark
is another population, restricted to producing wells in its configured spud window.
Neither historical total is used to infer rig-time performance here.</p>
<h2>Calendar intervals by field</h2>
<table><tr><th>Field</th><th>Date-qualified wellbores</th><th>Median calendar days</th>
<th>Sum of calendar days</th></tr>{rows}</table>
<h2>Worked example</h2>
<p>Synthetic inputs: spud 2020-01-01, TD 2020-01-08, first completion 2020-03-01,
first oil 2020-06-09. Spud to TD = 7 calendar days. Spud to completion =
31 + 29 = 60 calendar days (leap year). Completion to first oil =
31 + 30 + 31 + 8 = 100 calendar days. The benchmark decomposition is
60 + 100 = 160 calendar days from spud to first oil. None establishes active rig time.</p>
<h2>Sources and limits</h2>
<p>Input: <code>{html.escape(source.name)}</code>, Sheet1. Method:
<a href="https://docs.python.org/3.13/library/datetime.html#date-objects">Python 3.13
(2024), date subtraction</a>; semantic correction: issue #1077 (2026).
Activity-coded rig time, causal learning and article membership are NOT_EVALUATED.
The legacy workbook day columns are not used in statistics; the download retains
reported completion values under an explicit legacy name without certifying their basis. No mud-weight acceptance band or
learning threshold is assumed. Date coverage can omit operations and does not
resolve rig moves, waiting, batch work or sidetrack scope.</p>
<p><a href="lt_drilling_insights.csv">Download the dated calendar intervals and basis</a>.</p>
</main></html>
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args(argv)
    df = load_wells(args.source)
    write_csv(df, CSV_PATH)
    HTML_PATH.write_text(
        site_nav.inject_for(
            render_html(compute_stats(df), args.source), "drilling_insights"
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
