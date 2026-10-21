#!/usr/bin/env python3
"""Build the Lower-Tertiary calendar cycle-time analysis from saved dates.

Spud-to-TD calendar days = (TD date - spud date).days, without an inclusive
endpoint adjustment. Source: Python 3 datetime, timedelta objects:
https://docs.python.org/3/library/datetime.html#timedelta-objects

The workbook's legacy DRILLING_DAYS mixes calendar and WAR-union bases and is
not used as a duration input. Missing/reversed dates remain null; same-day
milestones give a true zero. This page does not infer rig utilisation or learning.
"""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS = PROJECT_ROOT / "scripts"
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
EM = "—"

# Append one row per issued report change; preserve earlier revision text.
REVISION_HISTORY = (
    (
        1,
        "2026-10-19",
        "Replace mixed drilling-day claims with dated\ncalendar intervals; explain populations and remove unsupported learning conclusions.",
    ),
    (
        2,
        "2026-10-20",
        "Separate historical snapshot counts from the current workbook population and document the retained completion_days name.",
    ),
    (
        3,
        "2026-10-20",
        "Use the issued revision date in the footer to keep regeneration dates consistent.",
    ),
)


def load_wells(source: Path) -> pd.DataFrame:
    """Exclude blank/TOTALS rows; derive one consistent calendar interval."""
    df = pd.read_excel(source, sheet_name="Sheet1")
    df = df[df["LEASE_NAME"].notna()].copy()
    for col in ("WELL_SPUD_DATE", "TOTAL_DEPTH_DATE"):
        df[col] = pd.to_datetime(df[col], format="%m/%d/%Y", errors="coerce")
    span = (df["TOTAL_DEPTH_DATE"] - df["WELL_SPUD_DATE"]).dt.days
    df["calendar_days"] = span.where(span >= 0)
    return df.reset_index(drop=True)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    out = pd.DataFrame(
        {
            "field": df["LEASE_NAME"],
            "surf_lease_num": df["SURF_LEASE_NUM"],
            "water_depth_ft": df["WATER_DEPTH"],
            "api_well_number": df["API_WELL_NUMBER"],
            "well_name": df["WELL_NAME"],
            "spud_date": df["WELL_SPUD_DATE"].dt.strftime("%Y-%m-%d"),
            "total_depth_date": df["TOTAL_DEPTH_DATE"].dt.strftime("%Y-%m-%d"),
            "spud_to_td_calendar_days": df["calendar_days"],
            "max_bh_total_md_ft": (
                df["MAX_BH_TOTAL_MD"] if "MAX_BH_TOTAL_MD" in df else None
            ),
            "max_well_bore_tvd_ft": df["MAX_WELL_BORE_TVD"],
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    out.sort_values(["field", "well_name"], kind="stable").to_csv(path, index=False)


def compute_stats(df: pd.DataFrame) -> dict:
    valid = df.dropna(subset=["calendar_days"])
    days = valid["calendar_days"]
    lc = valid.dropna(subset=["MAX_WELL_BORE_TVD"])
    return {
        "n_wellbores": len(df),
        "n_calendar": len(valid),
        "n_missing": len(df) - len(valid),
        "total_calendar_days": float(days.sum()) if len(days) else None,
        "median_days": float(days.median()) if len(days) else None,
        "lc": lc,
        "per_field": valid.groupby("LEASE_NAME")["calendar_days"]
        .agg(["count", "median", "sum"])
        .reset_index(),
    }


def _n(v, dec=0):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return EM
    if dec == 0:
        return f"{v:,.0f}"
    return f"{v:,.{dec}f}"


def esc(s) -> str:
    return html.escape(str(s))


# --------------------------------------------------------------------------- #
# Inline-SVG chart builders (class-styled so the page CSS themes them)
# --------------------------------------------------------------------------- #
def svg_scatter(
    xs,
    ys,
    *,
    x_dom,
    y_dom,
    x_label,
    y_label,
    title,
    fit=None,
    highlight=None,
    width=760,
    height=430,
):
    ml, mr, mt, mb = 66, 22, 20, 52
    pw, ph = width - ml - mr, height - mt - mb
    x0, x1 = x_dom
    y0, y1 = y_dom

    def px(x):
        return ml + (x - x0) / (x1 - x0) * pw

    def py(y):
        return mt + (1 - (y - y0) / (y1 - y0)) * ph

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
        f'aria-label="{esc(title)}" class="chart" '
        f'preserveAspectRatio="xMidYMid meet">',
        f"<title>{esc(title)}</title>",
    ]
    # y grid + ticks
    yticks = np.linspace(y0, y1, 6)
    for t in yticks:
        yy = py(t)
        parts.append(
            f'<line x1="{ml:.1f}" y1="{yy:.1f}" x2="{ml+pw:.1f}" y2="{yy:.1f}" class="grid"/>'
        )
        parts.append(
            f'<text x="{ml-8:.1f}" y="{yy+3.5:.1f}" class="tick" text-anchor="end">{_n(t)}</text>'
        )
    # x ticks
    xticks = np.linspace(x0, x1, 7)
    for t in xticks:
        xx = px(t)
        parts.append(
            f'<line x1="{xx:.1f}" y1="{mt+ph:.1f}" x2="{xx:.1f}" y2="{mt+ph+5:.1f}" class="axis"/>'
        )
        parts.append(
            f'<text x="{xx:.1f}" y="{mt+ph+18:.1f}" class="tick" text-anchor="middle">'
            f"{_n(t/1000,1)}k</text>"
        )
    # axes
    parts.append(
        f'<line x1="{ml:.1f}" y1="{mt:.1f}" x2="{ml:.1f}" y2="{mt+ph:.1f}" class="axis"/>'
    )
    parts.append(
        f'<line x1="{ml:.1f}" y1="{mt+ph:.1f}" x2="{ml+pw:.1f}" y2="{mt+ph:.1f}" class="axis"/>'
    )
    # axis labels
    parts.append(
        f'<text x="{ml+pw/2:.1f}" y="{height-6:.1f}" class="axlab" text-anchor="middle">{esc(x_label)}</text>'
    )
    parts.append(
        f'<text x="16" y="{mt+ph/2:.1f}" class="axlab" text-anchor="middle" '
        f'transform="rotate(-90 16 {mt+ph/2:.1f})">{esc(y_label)}</text>'
    )
    # fit line
    if fit is not None:
        slope, intercept = fit
        fy0 = slope * x0 + intercept
        fy1 = slope * x1 + intercept
        parts.append(
            f'<line x1="{px(x0):.1f}" y1="{py(fy0):.1f}" x2="{px(x1):.1f}" y2="{py(fy1):.1f}" class="fit"/>'
        )
    # points
    hl = set(highlight or [])
    for i, (x, y) in enumerate(zip(xs, ys)):
        cls = "pt hi" if i in hl else "pt"
        parts.append(f'<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="4" class="{cls}"/>')
    parts.append("</svg>")
    return "".join(parts)


def render_html(s: dict, source: Path) -> str:
    lc = s["lc"]
    chart = "<p>No paired dates and TVD available.</p>"
    if not lc.empty:
        xs = lc["MAX_WELL_BORE_TVD"].to_numpy(float)
        ys = lc["calendar_days"].to_numpy(float)
        chart = svg_scatter(
            xs,
            ys,
            x_dom=(0, max(float(xs.max()), 1)),
            y_dom=(0, max(float(ys.max()), 1)),
            x_label="Max wellbore TVD (ft)",
            y_label="Calendar cycle time (days)",
            title="Spud-to-TD calendar cycle time vs TVD",
        )
    rows = "".join(
        f"<tr><td>{esc(r['LEASE_NAME'])}</td><td>{_n(r['count'])}</td>"
        f"<td>{_n(r['median'], 1)}</td><td>{_n(r['sum'])}</td></tr>"
        for _, r in s["per_field"].iterrows()
    )
    try:
        src = source.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        src = "supplied workbook"
    revisions = "".join(
        f"<tr><td>{rev}</td><td>{esc(issued)}</td><td>{esc(reason)}</td></tr>"
        for rev, issued, reason in REVISION_HISTORY
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lower-Tertiary Calendar Cycle-Time Analysis</title>
<style>
body {{ font:16px/1.6 system-ui,sans-serif; color:#172c3e; background:#f5f7fa;
max-width:960px; margin:auto; padding:24px; }}
section,header {{ background:white; padding:24px; margin-bottom:20px; }}
table {{ border-collapse:collapse; width:100%; }}
th,td {{ text-align:left; padding:8px; border-bottom:1px solid #ccd6df; }}
.chart .grid,.chart .axis {{ stroke:#ccd6df; }}
.chart .pt {{ fill:#1d5fa8; }} .chart text {{ fill:#172c3e; font-size:11px; }}
</style></head><body>
<header><h1>Calendar cycle time: spud to TD</h1>
<p>{s['n_calendar']} of {s['n_wellbores']} workbook wellbores have ordered milestone
 dates. Their summed calendar intervals are {_n(s['total_calendar_days'])} days;
 median {_n(s['median_days'], 1)} days. These are elapsed intervals, not rig-days,
 and include suspension and waiting between milestones.</p>
<h2>Revision history</h2><table><tr><th>Revision</th><th>Date</th><th>Change and reason</th></tr>
{revisions}</table>
</header>
<section><h2>Definition and population</h2>
<p>For each named lease row in workbook Sheet1, calendar days = TD date minus spud
 date, with no inclusive endpoint adjustment. Blank lease and TOTALS trailer rows
 are excluded. Missing or reversed dates are not evaluated; same-day dates give
 zero. {s['n_missing']} rows lack an ordered pair; {len(lc)} also have TVD and appear
 below. No positive-duration filter or producing-well filter is applied.</p>
<p>The historical <b>184</b> figure counted positive legacy DRILLING_DAYS entries
 in the historical 217-wellbore workbook snapshot; the remaining 33 were zero/missing entries.
 Current population: {s['n_wellbores']} workbook wellbores.
 The historical 11,124-day total mixed milestone spans and WAR-union values and is withdrawn
 as a rig-time claim. The article's <b>211</b> wellbores and 21,944 days cover a
 different development population (excluding Big Foot), and count drilling plus
 completion, rather than this page's spud-to-TD interval. Neither the difference
 in counts nor the difference in totals measures missing rig-time or performance.</p>
<p>Source for the historical counts and definitions:
<a href="https://github.com/vamseeachanta/worldenergydata/issues/1062">data-basis investigation</a>;
 source for the article comparison:
<a href="wo-april-2026-per-well-dc.html">per-well D&amp;C reconciliation, population table</a>.
 Exact row-level membership of the article population is not established by this
 workbook; a paired performance comparison is not evaluated.</p>
<p>The producing-well benchmark is a third population, restricted by its configured
 spud window and OGOR-A production. Its <code>spud_to_completion_calendar_days</code>
 ends at the first completion operation, not TD. Its <code>completion_days</code>
 ends at first oil. Neither benchmark interval is rig-time.</p>
<h3>Limits</h3><p>The name <code>completion_days</code> is retained for compatibility
 with existing CSV consumers. It means first oil minus first completion in calendar
 days, including waiting and suspension; a rename requires a coordinated consumer
 migration. Active completion time is not established.</p></section>
<section><h2>Calendar cycle time vs true vertical depth</h2><figure>{chart}
<figcaption>Spud-to-TD calendar days against maximum wellbore TVD (ft);
 {len(lc)} dated wellbores. Calendar intervals do not establish drilling efficiency,
 rig utilisation, learning, or the cause of a delay.</figcaption></figure></section>
<section><h2>Per-field calendar intervals</h2><table>
<tr><th>Field</th><th>Wellbores</th><th>Median (days)</th><th>Sum (days)</th></tr>
{rows}</table><p>Summed well intervals can overlap in calendar time; this sum is
 neither portfolio elapsed duration nor rig occupancy.</p></section>
<section><h2>Worked example: inputs, method and answer</h2>
<p>Synthetic input: spud 2020-01-01, TD 2020-01-08, first completion 2020-03-01,
 first oil 2020-06-09. TD minus spud = 7 calendar days. Completion minus spud =
 31 + 29 = 60 calendar days (leap-year February). First oil minus completion =
 31 + 30 + 31 + 8 = 100 calendar days. Thus 60 + 100 = 160 days from spud to
 first oil. None of these calculations establishes active drilling or completion
 rig-days. Missing milestones leave their intervals not evaluated.</p>
<p>Method source: <a href="https://docs.python.org/3/library/datetime.html#timedelta-objects">
 Python 3 datetime, timedelta objects</a> (date subtraction).</p></section>
<footer>Input: <code>{esc(src)}</code>, Sheet1. Report revision date {esc(REVISION_HISTORY[-1][1])}.
 Source dates are preserved in <a href="lt_drilling_insights.csv">the calendar CSV</a>.
 Regenerate with <code>python scripts/lower_tertiary/build_drilling_insights.py</code>.
 No activity-coded rig-time result is inferred; those require a separately qualified basis.</footer>
</body></html>"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args(argv)
    if not args.source.exists():
        print("ERROR: source workbook not found", file=sys.stderr)
        return 1
    df = load_wells(args.source)
    if df.empty:
        print("ERROR: no wellbore rows after cleaning", file=sys.stderr)
        return 1
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(df, CSV_PATH)
    stats = compute_stats(df)
    HTML_PATH.write_text(
        site_nav.inject_for(
            render_html(stats, args.source), "drilling_insights"
        ).rstrip()
        + "\n",
        encoding="utf-8",
    )
    print(f"{stats['n_calendar']} of {stats['n_wellbores']} calendar spans derived")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
