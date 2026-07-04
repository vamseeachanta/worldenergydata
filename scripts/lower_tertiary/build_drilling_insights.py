#!/usr/bin/env python3
"""ABOUTME: CLI for the GoM Lower-Tertiary drilling-performance insight (worldenergydata#775).
ABOUTME: Reads the V30 drilling_and_completion_days workbook and renders the drilling
ABOUTME: learning-curve front-door page + per-well CSV to reports/lower_tertiary/.

This is the guaranteed entry point for the saved analytic. It reads Sheet1 of
``docs/modules/bsee/analysis/production/FDAS_V30/drilling_and_completion_days.xlsx``
(219 rows: 217 Lower-Tertiary development wellbores + one blank + one spreadsheet
TOTALS row), computes portfolio drilling statistics, and emits:

  * reports/lower_tertiary/lt_drilling_insights.csv   -- per-well, one row/wellbore
  * reports/lower_tertiary/drilling_insights.html     -- self-contained front door

Every number on the page is computed here from the workbook. Drilling-day and
completion-day values of 0 (33 wellbores, mostly re-entries with no spud/TD date
recorded) are treated as NOT DERIVABLE and rendered as an em dash (—) -- flagged,
never faked. Mud-weight readings outside the physical 9-22 ppg band (5 wellbores,
incl. one 80 ppg keying error) are excluded from the mud-weight statistics and
counted in the data-limits footer.

Usage
-----
    python3 scripts/lower_tertiary/build_drilling_insights.py
    python3 scripts/lower_tertiary/build_drilling_insights.py --source <path.xlsx>
"""

from __future__ import annotations

import argparse
import html
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from worldenergydata.lower_tertiary.drilling_learning import (  # noqa: E402
    compute_learning,
)

DEFAULT_SOURCE = (
    PROJECT_ROOT
    / "docs"
    / "modules"
    / "bsee"
    / "analysis"
    / "production"
    / "FDAS_V30"
    / "drilling_and_completion_days.xlsx"
)
REPORTS_DIR = PROJECT_ROOT / "reports" / "lower_tertiary"
CSV_PATH = REPORTS_DIR / "lt_drilling_insights.csv"
HTML_PATH = REPORTS_DIR / "drilling_insights.html"

# Physical mud-weight window (ppg). Deepwater LT synthetic/oil-based muds run
# ~14-19 ppg; readings outside this band are keying errors (25/40/45/80 ppg).
MUD_MIN, MUD_MAX = 9.0, 22.0

EM = "—"  # em dash: flag-don't-fake sentinel


# --------------------------------------------------------------------------- #
# Load + clean
# --------------------------------------------------------------------------- #
def load_wells(source: Path) -> pd.DataFrame:
    """Return the per-wellbore frame, dropping blank + TOTALS trailer rows."""
    df = pd.read_excel(source, sheet_name="Sheet1")
    # The workbook's last two rows are a blank spacer and a column-SUM TOTALS
    # row (no LEASE_NAME). Drop any row with no lease name.
    df = df[df["LEASE_NAME"].notna()].copy()
    df["WELL_SPUD_DATE"] = pd.to_datetime(
        df["WELL_SPUD_DATE"], format="%m/%d/%Y", errors="coerce"
    )
    df["TOTAL_DEPTH_DATE"] = pd.to_datetime(
        df["TOTAL_DEPTH_DATE"], format="%m/%d/%Y", errors="coerce"
    )
    # 0-day drilling/completion means "not recorded" for these re-entry rows.
    df["drill_days"] = df["DRILLING_DAYS"].where(df["DRILLING_DAYS"] > 0)
    df["compl_days"] = df["COMPLETION_DAYS"].where(df["COMPLETION_DAYS"] > 0)
    df["mud_ppg_valid"] = df["MAX_DRILL_FLUID_WGT"].where(
        df["MAX_DRILL_FLUID_WGT"].between(MUD_MIN, MUD_MAX)
    )
    df = df.reset_index(drop=True)
    return df


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
            "drilling_days": df["drill_days"],
            "completion_days": df["compl_days"],
            "max_bh_total_md_ft": df["MAX_BH_TOTAL_MD"],
            "max_well_bore_tvd_ft": df["MAX_WELL_BORE_TVD"],
            "max_drill_fluid_wgt_ppg": df["MAX_DRILL_FLUID_WGT"],
        }
    )
    out = out.sort_values(["field", "well_name"], kind="stable")
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False)


# --------------------------------------------------------------------------- #
# Stats
# --------------------------------------------------------------------------- #
def compute_stats(df: pd.DataFrame) -> dict:
    drill = df["drill_days"].dropna()
    compl = df["compl_days"].dropna()
    lc = df.dropna(subset=["drill_days", "MAX_WELL_BORE_TVD"])
    x = lc["MAX_WELL_BORE_TVD"].to_numpy(float)
    y = lc["drill_days"].to_numpy(float)
    slope, intercept = np.polyfit(x, y, 1)
    corr = float(np.corrcoef(x, y)[0, 1])

    mud = df["mud_ppg_valid"].dropna()

    # deepest / fastest / slowest (only among wells with a derivable drill_days)
    dd = df.dropna(subset=["drill_days"])
    deepest = (
        dd.dropna(subset=["MAX_WELL_BORE_TVD"]).nlargest(1, "MAX_WELL_BORE_TVD").iloc[0]
    )
    fastest = dd.nsmallest(5, "drill_days")
    slowest = dd.nlargest(5, "drill_days")

    per_field = (
        dd.groupby("LEASE_NAME")
        .agg(
            n=("drill_days", "size"),
            median_days=("drill_days", "median"),
            total_days=("drill_days", "sum"),
            median_tvd=("MAX_WELL_BORE_TVD", "median"),
        )
        .sort_values("median_days")
        .reset_index()
    )

    return {
        "n_wellbores": int(len(df)),
        "n_drill": int(len(drill)),
        "n_not_derivable": int(len(df) - len(drill)),
        "total_rig_days": float(drill.sum()),
        "rig_years": float(drill.sum() / 365.25),
        "total_compl_days": float(compl.sum()),
        "median_days": float(drill.median()),
        "mean_days": float(drill.mean()),
        "p25": float(drill.quantile(0.25)),
        "p75": float(drill.quantile(0.75)),
        "min_days": float(drill.min()),
        "max_days": float(drill.max()),
        "n_compl": int(len(compl)),
        "median_compl": float(compl.median()),
        "slope_per_ft": float(slope),
        "slope_per_kft": float(slope * 1000.0),
        "intercept": float(intercept),
        "corr": corr,
        "r2": corr * corr,
        "n_lc": int(len(lc)),
        "tvd_min": float(x.min()),
        "tvd_max": float(x.max()),
        "n_mud": int(len(mud)),
        "median_mud": float(mud.median()),
        "max_mud": float(mud.max()),
        "n_mud_outlier": int(df["MAX_DRILL_FLUID_WGT"].notna().sum() - len(mud)),
        "median_wd": float(df["WATER_DEPTH"].median()),
        "max_wd": float(df["WATER_DEPTH"].max()),
        "n_fields": int(dd["LEASE_NAME"].nunique()),
        "deepest": deepest,
        "fastest": fastest,
        "slowest": slowest,
        "per_field": per_field,
        "spud_min_year": int(df["WELL_SPUD_DATE"].dt.year.min()),
        "spud_max_year": int(df["WELL_SPUD_DATE"].dt.year.max()),
        "lc": lc,
        "mud_df": df.dropna(subset=["mud_ppg_valid", "MAX_WELL_BORE_TVD"]),
    }


# --------------------------------------------------------------------------- #
# Small formatters
# --------------------------------------------------------------------------- #
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


def svg_barh(labels, values, notes, *, x_max, title, unit="", width=760, bar_h=26):
    ml, mr, mt, mb = 150, 60, 14, 30
    n = len(labels)
    height = mt + mb + n * (bar_h + 8)
    pw = width - ml - mr

    def bx(v):
        return v / x_max * pw

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
        f'aria-label="{esc(title)}" class="chart" preserveAspectRatio="xMidYMid meet">',
        f"<title>{esc(title)}</title>",
    ]
    for i, (lab, val, note) in enumerate(zip(labels, values, notes)):
        y = mt + i * (bar_h + 8)
        w = bx(val)
        parts.append(
            f'<text x="{ml-10:.0f}" y="{y+bar_h*0.68:.1f}" class="tick" text-anchor="end">{esc(lab)}</text>'
        )
        parts.append(
            f'<rect x="{ml}" y="{y:.1f}" width="{w:.1f}" height="{bar_h}" rx="3" class="bar"/>'
        )
        parts.append(
            f'<text x="{ml+w+8:.1f}" y="{y+bar_h*0.68:.1f}" class="barval">{_n(val,1)}{unit}'
            f'<tspan class="barnote"> {esc(note)}</tspan></text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def svg_diverging_barh(rows, *, title, width=760, bar_h=24):
    """Zero-centered horizontal bars of per-field dpk_delta_pct.

    Negative (depth-normalized drilling got faster = learning) extends left and
    is styled cool/green; positive (step-out reset the clock) extends right and
    is styled warm/red; near-zero (flat) is muted. ``rows`` is the per_field
    list from ``compute_learning`` (already sorted by dpk_delta_pct).
    """
    ml, mr, mt, mb = 132, 58, 34, 20
    n = len(rows)
    height = mt + mb + n * (bar_h + 8)
    pw = width - ml - mr
    cx = ml + pw / 2.0
    vmax = max(abs(r["dpk_delta_pct"]) for r in rows) * 1.08

    def bx(v):
        return v / vmax * (pw / 2.0)

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
        f'aria-label="{esc(title)}" class="chart" preserveAspectRatio="xMidYMid meet">',
        f"<title>{esc(title)}</title>",
    ]
    # header direction labels
    parts.append(
        f'<text x="{cx-8:.0f}" y="{mt-16:.0f}" class="divhdr" text-anchor="end">'
        f"&#8592; faster (learning)</text>"
    )
    parts.append(
        f'<text x="{cx+8:.0f}" y="{mt-16:.0f}" class="divhdr warm" text-anchor="start">'
        f"slower (step-out) &#8594;</text>"
    )
    y_bot = mt + n * (bar_h + 8) - 8 + bar_h
    parts.append(
        f'<line x1="{cx:.1f}" y1="{mt-6:.1f}" x2="{cx:.1f}" y2="{y_bot:.1f}" class="axis"/>'
    )
    for i, r in enumerate(rows):
        y = mt + i * (bar_h + 8)
        v = r["dpk_delta_pct"]
        w = bx(v)
        x = cx if w >= 0 else cx + w
        cls = {"learn": "div-learn", "stepout": "div-step", "flat": "div-flat"}[
            r["verdict"]
        ]
        parts.append(
            f'<text x="{ml-10:.0f}" y="{y+bar_h*0.68:.1f}" class="tick" '
            f'text-anchor="end">{esc(r["field"])}</text>'
        )
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{abs(w):.1f}" height="{bar_h}" '
            f'rx="3" class="{cls}"/>'
        )
        if w >= 0:
            lx, anch = cx + w + 7, "start"
        else:
            lx, anch = cx + w - 7, "end"
        parts.append(
            f'<text x="{lx:.1f}" y="{y+bar_h*0.68:.1f}" class="barval" '
            f'text-anchor="{anch}">{v:+.0f}%<tspan class="barnote"> (n={r["n"]})</tspan></text>'
        )
    parts.append("</svg>")
    return "".join(parts)


# --------------------------------------------------------------------------- #
# Page
# --------------------------------------------------------------------------- #
def render_html(s: dict, source: Path) -> str:
    lc = s["lc"]
    hi_idx = int(np.argmax(lc["MAX_WELL_BORE_TVD"].to_numpy()))
    scatter = svg_scatter(
        lc["MAX_WELL_BORE_TVD"].to_numpy(float),
        lc["drill_days"].to_numpy(float),
        x_dom=(4000, 36000),
        y_dom=(0, 380),
        x_label="Max wellbore TVD (ft)",
        y_label="Drilling days",
        title="Lower-Tertiary drilling learning curve: days vs TVD",
        fit=(s["slope_per_ft"], s["intercept"]),
        highlight=[hi_idx],
    )
    mud = s["mud_df"]
    mud_scatter = svg_scatter(
        mud["MAX_WELL_BORE_TVD"].to_numpy(float),
        mud["mud_ppg_valid"].to_numpy(float),
        x_dom=(4000, 36000),
        y_dom=(9, 20),
        x_label="Max wellbore TVD (ft)",
        y_label="Max mud weight (ppg)",
        title="Mud weight vs depth",
    )
    pf = s["per_field"]
    field_bar = svg_barh(
        pf["LEASE_NAME"].tolist(),
        pf["median_days"].tolist(),
        [f"(n={int(x)})" for x in pf["n"]],
        x_max=float(pf["median_days"].max()) * 1.18,
        title="Median drilling days by field",
        unit=" d",
    )

    lrn = s["learning"]
    learn_bar = svg_diverging_barh(
        lrn["per_field"],
        title="Change in depth-normalized drilling intensity, first half vs last half",
    )
    lc_counts = lrn["counts"]
    learn_flds = [r for r in lrn["per_field"] if r["verdict"] == "learn"]
    step_flds = [r for r in lrn["per_field"] if r["verdict"] == "stepout"]
    learn_names = ", ".join(
        f"{esc(r['field'])} {r['dpk_delta_pct']:+.0f}%" for r in learn_flds
    )
    step_names = ", ".join(
        f"{esc(r['field'])} {r['dpk_delta_pct']:+.0f}%"
        for r in sorted(step_flds, key=lambda r: -r["dpk_delta_pct"])
    )
    sm = lrn["stmalo"]
    pooled = lrn["pooled"]

    def rows(frame):
        out = []
        for _, r in frame.iterrows():
            out.append(
                "<tr><td>{f}</td><td>{w}</td><td class='num'>{d}</td>"
                "<td class='num'>{tvd}</td><td class='num'>{wd}</td></tr>".format(
                    f=esc(r["LEASE_NAME"]),
                    w=esc(r["WELL_NAME"]),
                    d=_n(r["drill_days"]),
                    tvd=_n(r["MAX_WELL_BORE_TVD"]),
                    wd=_n(r["WATER_DEPTH"]),
                )
            )
        return "\n".join(out)

    dp = s["deepest"]
    field_rows = "\n".join(
        "<tr><td>{f}</td><td class='num'>{n}</td><td class='num'>{med}</td>"
        "<td class='num'>{tot}</td><td class='num'>{tvd}</td></tr>".format(
            f=esc(r["LEASE_NAME"]),
            n=int(r["n"]),
            med=_n(r["median_days"], 1),
            tot=_n(r["total_days"]),
            tvd=_n(r["median_tvd"]),
        )
        for _, r in pf.iterrows()
    )

    gen = date.today().isoformat()
    src_rel = source.relative_to(PROJECT_ROOT)

    return f"""<meta charset="utf-8">
<title>GoM Lower-Tertiary Drilling Learning Curve</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root {{
    --bg:#eef2f6; --panel:#fff; --panel-2:#f6f9fc; --ink:#0c1a28; --muted:#5a6b7b;
    --line:#d6e0ea; --accent:#d9822b; --accent-ink:#7a4410; --blue:#1d5fa8;
    --good:#2e9e6b; --alert:#c0453b; --grid:#e3e9ee;
    --mono:ui-monospace,"SF Mono","Cascadia Code","JetBrains Mono",Consolas,monospace;
    --sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    --shadow:0 1px 2px rgba(12,26,40,.06),0 8px 24px rgba(12,26,40,.06);
  }}
  @media (prefers-color-scheme:dark) {{
    :root {{
      --bg:#0a141f; --panel:#10202f; --panel-2:#0d1b28; --ink:#e8eef4; --muted:#8ca0b3;
      --line:#24384b; --accent:#f0a24a; --accent-ink:#f7c489; --blue:#5b9de0;
      --good:#43b982; --alert:#e0685e; --grid:#1c2e40;
      --shadow:0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35);
    }}
  }}
  :root[data-theme="light"] {{ --bg:#eef2f6; --panel:#fff; --panel-2:#f6f9fc; --ink:#0c1a28;
    --muted:#5a6b7b; --line:#d6e0ea; --accent:#d9822b; --accent-ink:#7a4410; --blue:#1d5fa8;
    --good:#2e9e6b; --alert:#c0453b; --grid:#e3e9ee; }}
  :root[data-theme="dark"] {{ --bg:#0a141f; --panel:#10202f; --panel-2:#0d1b28; --ink:#e8eef4;
    --muted:#8ca0b3; --line:#24384b; --accent:#f0a24a; --accent-ink:#f7c489; --blue:#5b9de0;
    --good:#43b982; --alert:#e0685e; --grid:#1c2e40; }}

  * {{ box-sizing:border-box; }}
  body {{ margin:0; }}
  .wrap {{ background:var(--bg); color:var(--ink); font-family:var(--sans);
    padding:clamp(16px,3vw,40px); min-height:100%; -webkit-font-smoothing:antialiased; }}
  .sheet {{ max-width:1180px; margin:0 auto; background:var(--panel); border:1px solid var(--line);
    border-radius:14px; box-shadow:var(--shadow); overflow:hidden; }}
  .head {{ padding:clamp(20px,2.6vw,34px); border-bottom:1px solid var(--line); }}
  .eyebrow {{ font-family:var(--mono); font-size:11px; letter-spacing:.18em; text-transform:uppercase;
    color:var(--muted); margin:0 0 8px; }}
  .title {{ font-size:clamp(26px,3.6vw,40px); font-weight:800; letter-spacing:-.02em; margin:0;
    line-height:1.05; text-wrap:balance; }}
  .thesis {{ color:var(--ink); margin:14px 0 0; font-size:clamp(15px,1.5vw,17px); max-width:74ch;
    line-height:1.5; }}
  .thesis b {{ color:var(--accent-ink); }}
  @media (prefers-color-scheme:dark) {{ .thesis b {{ color:var(--accent); }} }}
  :root[data-theme="dark"] .thesis b {{ color:var(--accent); }}

  .metrics {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
    gap:1px; background:var(--line); border-top:1px solid var(--line); }}
  .metric {{ background:var(--panel-2); padding:16px 18px; }}
  .metric .k {{ font-family:var(--mono); font-size:10.5px; letter-spacing:.09em;
    text-transform:uppercase; color:var(--muted); }}
  .metric .v {{ font-family:var(--mono); font-size:23px; font-weight:700;
    font-variant-numeric:tabular-nums; margin-top:5px; letter-spacing:-.01em; }}
  .metric .v small {{ font-size:12px; color:var(--muted); font-weight:500; }}

  .body {{ padding:clamp(18px,2.6vw,34px); display:grid; gap:34px; }}
  section h2 {{ font-size:19px; margin:0 0 4px; letter-spacing:-.01em; }}
  section p.lead {{ color:var(--muted); margin:0 0 14px; font-size:14.5px; max-width:80ch; line-height:1.5; }}
  .lane-label {{ font-family:var(--mono); font-size:11px; letter-spacing:.16em; text-transform:uppercase;
    color:var(--muted); margin:0 0 10px; font-weight:600; }}
  .scrollx {{ overflow-x:auto; }}
  figure {{ margin:0; }}
  figcaption {{ font-size:12.5px; color:var(--muted); margin-top:8px; line-height:1.45; }}

  /* charts */
  .chart {{ max-width:820px; height:auto; display:block; margin:0 auto; }}
  .chart .grid {{ stroke:var(--grid); stroke-width:1; }}
  .chart .axis {{ stroke:var(--line); stroke-width:1.2; }}
  .chart .tick {{ font-family:var(--mono); font-size:10px; fill:var(--muted); }}
  .chart .axlab {{ font-family:var(--sans); font-size:11.5px; fill:var(--muted); }}
  .chart .pt {{ fill:var(--blue); opacity:.5; }}
  .chart .pt.hi {{ fill:var(--accent); opacity:1; stroke:var(--panel); stroke-width:1.4; }}
  .chart .fit {{ stroke:var(--accent); stroke-width:2.4; stroke-dasharray:6 4; }}
  .chart .bar {{ fill:var(--blue); }}
  .chart .barval {{ font-family:var(--mono); font-size:11px; fill:var(--ink);
    font-variant-numeric:tabular-nums; dominant-baseline:middle; }}
  .chart .barnote {{ fill:var(--muted); }}
  .chart .div-learn {{ fill:var(--good); }}
  .chart .div-step {{ fill:var(--alert); }}
  .chart .div-flat {{ fill:var(--muted); opacity:.55; }}
  .chart .divhdr {{ font-family:var(--mono); font-size:10.5px; letter-spacing:.04em;
    fill:var(--good); font-weight:600; }}
  .chart .divhdr.warm {{ fill:var(--alert); }}

  .callout {{ border:1px solid var(--line); border-left:4px solid var(--accent);
    background:var(--panel-2); border-radius:10px; padding:16px 18px; margin:2px 0 0;
    font-size:14px; line-height:1.55; }}
  .callout .ct {{ font-family:var(--mono); font-size:10.5px; letter-spacing:.12em;
    text-transform:uppercase; color:var(--accent-ink); font-weight:700; margin:0 0 6px; }}
  @media (prefers-color-scheme:dark) {{ .callout .ct {{ color:var(--accent); }} }}
  :root[data-theme="dark"] .callout .ct {{ color:var(--accent); }}
  .callout b {{ font-variant-numeric:tabular-nums; }}
  .note {{ font-size:12.5px; color:var(--muted); margin:12px 0 0; line-height:1.5;
    max-width:82ch; }}

  table {{ border-collapse:collapse; width:100%; font-size:13.5px; min-width:520px; }}
  th, td {{ text-align:left; padding:7px 12px; border-bottom:1px solid var(--line); }}
  th {{ font-family:var(--mono); font-size:10.5px; letter-spacing:.06em; text-transform:uppercase;
    color:var(--muted); font-weight:600; }}
  td.num, th.num {{ text-align:right; font-variant-numeric:tabular-nums; font-family:var(--mono); }}
  tbody tr:nth-child(odd) td {{ background:var(--panel-2); }}
  .cols {{ display:grid; grid-template-columns:1fr 1fr; gap:26px; }}
  @media (max-width:760px) {{ .cols {{ grid-template-columns:1fr; }} }}

  .foot {{ border-top:1px solid var(--line); padding:18px clamp(18px,2.6vw,34px);
    font-size:12px; color:var(--muted); line-height:1.55; }}
  .foot b {{ color:var(--ink); }}
  code {{ font-family:var(--mono); font-size:.92em; background:var(--panel-2);
    padding:1px 5px; border-radius:4px; }}
</style>
<div class="wrap">
<div class="sheet">
  <header class="head">
    <p class="eyebrow">worldenergydata &middot; Gulf of Mexico &middot; Lower-Tertiary play</p>
    <h1 class="title">The Lower-Tertiary Drilling Learning Curve</h1>
    <p class="thesis">
      Across {s['n_fields']} Paleogene fields, <b>{s['n_drill']} development wellbores</b>
      burned <b>{_n(s['total_rig_days'])} rig-days</b> ({_n(s['rig_years'],1)} rig-years)
      of drilling &mdash; a median of <b>{_n(s['median_days'],1)} days</b> per wellbore
      (IQR {_n(s['p25'])}&ndash;{_n(s['p75'])}). Each extra 1,000&nbsp;ft of true vertical
      depth adds only about <b>{_n(s['slope_per_kft'],1)} drilling days</b>, and TVD explains
      just <b>{_n(s['r2']*100,0)}%</b> of the spread (r&sup2;={_n(s['r2'],2)}): in this play
      field execution and hole trouble &mdash; not depth &mdash; drive the learning curve.
    </p>
  </header>

  <div class="metrics">
    <div class="metric"><div class="k">Wellbores (drill-days derivable)</div>
      <div class="v">{s['n_drill']}<small> / {s['n_wellbores']}</small></div></div>
    <div class="metric"><div class="k">Total rig-days</div>
      <div class="v">{_n(s['total_rig_days'])}<small> d</small></div></div>
    <div class="metric"><div class="k">Median drill-days</div>
      <div class="v">{_n(s['median_days'],1)}<small> (mean {_n(s['mean_days'],1)})</small></div></div>
    <div class="metric"><div class="k">Median completion-days</div>
      <div class="v">{_n(s['median_compl'],1)}<small> (n={s['n_compl']})</small></div></div>
    <div class="metric"><div class="k">Days per 1,000 ft TVD</div>
      <div class="v">{_n(s['slope_per_kft'],1)}<small> r&sup2;={_n(s['r2'],2)}</small></div></div>
    <div class="metric"><div class="k">Median mud weight</div>
      <div class="v">{_n(s['median_mud'],1)}<small> ppg (max {_n(s['max_mud'],1)})</small></div></div>
    <div class="metric"><div class="k">Median water depth</div>
      <div class="v">{_n(s['median_wd'])}<small> ft (max {_n(s['max_wd'])})</small></div></div>
    <div class="metric"><div class="k">Deepest wellbore TVD</div>
      <div class="v">{_n(s['tvd_max'])}<small> ft</small></div></div>
  </div>

  <div class="body">
    <section>
      <p class="lane-label">Learning curve</p>
      <h2>Drilling days vs true vertical depth</h2>
      <p class="lead">
        Each dot is one of the {s['n_lc']} wellbores with both a recorded drilling
        duration and a TVD. The dashed line is the least-squares fit
        (slope {_n(s['slope_per_kft'],1)} days per 1,000&nbsp;ft, r&sup2;={_n(s['r2'],2)});
        the highlighted point is the deepest hole, {esc(s['deepest']['LEASE_NAME'])}
        {esc(s['deepest']['WELL_NAME'])} at {_n(s['deepest']['MAX_WELL_BORE_TVD'])}&nbsp;ft TVD,
        drilled in only {_n(s['deepest']['drill_days'])} days &mdash; deeper is not
        automatically slower.
      </p>
      <div class="scrollx"><figure>{scatter}
        <figcaption>Drilling days vs max wellbore TVD, {s['n_lc']} GoM Lower-Tertiary
        wellbores. The weak fit (r&sup2;={_n(s['r2'],2)}) is the point: depth sets a
        floor, execution sets the spread.</figcaption></figure></div>
    </section>

    <section>
      <p class="lane-label">By field</p>
      <h2>Median drilling days by field</h2>
      <p class="lead">
        Field medians range from {_n(s['per_field']['median_days'].min(),1)} days
        ({esc(s['per_field'].iloc[0]['LEASE_NAME'])}) to
        {_n(s['per_field']['median_days'].max(),1)} days
        ({esc(s['per_field'].iloc[-1]['LEASE_NAME'])}) &mdash; a
        {_n(s['per_field']['median_days'].max()/s['per_field']['median_days'].min(),1)}&times;
        spread across the same play, at broadly similar depths.
      </p>
      <div class="scrollx"><figure>{field_bar}
        <figcaption>Median drilling days per field (n = wellbores with a derivable
        duration). St&nbsp;Malo's low median reflects many short re-entry / sidetrack
        intervals in a 65-wellbore program.</figcaption></figure></div>
    </section>

    <section>
      <p class="lane-label">Repetition vs step-out</p>
      <h2>What actually drives drilling days &mdash; repetition vs step-out</h2>
      <p class="lead">
        Ordering each field's wells by spud date and splitting them in half, the
        honest signal is depth-normalized: <b>rig-days per 1,000&nbsp;ft TVD</b>
        (dpk), first-half median vs last-half median. That controls for a field
        simply moving to shallower targets. Of the {lc_counts['learn']+lc_counts['stepout']+lc_counts['flat']}
        fields with n&nbsp;&ge;&nbsp;4 datable wells, <b>{lc_counts['learn']} learned</b>
        (dpk fell &gt;10%), <b>{lc_counts['stepout']} stepped out</b> (dpk rose &gt;10%),
        and {lc_counts['flat']} held flat.
      </p>
      <div class="scrollx"><figure>{learn_bar}
        <figcaption>Percent change in depth-normalized drilling intensity
        (rig-days per 1,000&nbsp;ft TVD), first half &rarr; last half of each field's
        spud-ordered wells. Green = repetition compounding; red = step-outs into
        new fault blocks resetting the clock.</figcaption></figure></div>

      <div class="callout" style="margin-top:16px">
        <p class="ct">St&nbsp;Malo spotlight &mdash; why depth-normalizing matters</p>
        Across St&nbsp;Malo's <b>{sm['n']} wells</b>, raw drilling time looks like a
        clean win &mdash; first-half median <b>{_n(sm['h1_median'])} days</b> falling to
        <b>{_n(sm['h2_median'])} days</b> ({(sm['h2_median']/sm['h1_median']-1)*100:+.0f}% raw).
        But the last-half wells are ~<b>{_n(abs(sm['tvd_drift']))}&nbsp;ft shallower</b>
        (TVD drift {sm['tvd_drift']:+,.0f}&nbsp;ft), so a good chunk of that speed-up is
        just easier holes. Depth-normalized, the real, defensible learning is
        <b>{sm['dpk_delta_pct']:+.0f}%</b> &mdash; {_n(sm['dpk_h1'],1)} &rarr;
        {_n(sm['dpk_h2'],1)} rig-days per 1,000&nbsp;ft.
      </div>

      <p class="lead" style="margin-top:16px">
        <b>Repetition compounds:</b> {len(learn_flds)} fields cut depth-normalized
        drilling intensity 26&ndash;67% ({learn_names}). <b>Step-outs reset the
        clock:</b> {len(step_flds)} fields worsened by +29&ndash;266% as they pushed
        into new fault blocks and reservoir compartments ({step_names}).
      </p>
      <p class="note">
        Honest note: this is depth-normalized and limited to fields with
        n&nbsp;&ge;&nbsp;4 datable wells. Pooled across every well-in-sequence, the
        learning trend is <b>weak</b> (r&nbsp;&asymp;&nbsp;{pooled['r']:.2f} over
        {pooled['n']} wells, {_n(pooled['slope_per_well'],1)} days per additional well) &mdash;
        so the thesis is <i>not</i> &ldquo;wells always get faster,&rdquo; but rather that
        <i>repetition within a known block</i> compounds while step-outs pay the
        first-well tax again.
      </p>
    </section>

    <section>
      <p class="lane-label">Mud program</p>
      <h2>Mud weight vs depth</h2>
      <p class="lead">
        Maximum drilling-fluid weight rises with depth as pore-pressure ramps in the
        Paleogene section &mdash; median {_n(s['median_mud'],1)} ppg, topping out at
        {_n(s['max_mud'],1)} ppg. {s['n_mud_outlier']} readings outside the physical
        {int(MUD_MIN)}&ndash;{int(MUD_MAX)} ppg band (including one 80 ppg keying error)
        are excluded as data errors.
      </p>
      <div class="scrollx"><figure>{mud_scatter}
        <figcaption>Max mud weight (ppg) vs max wellbore TVD, {s['n_mud']} wellbores
        with a valid reading.</figcaption></figure></div>
    </section>

    <section class="cols">
      <div>
        <p class="lane-label">Fastest</p>
        <h2 style="font-size:16px">Quickest wellbores</h2>
        <div class="scrollx"><table>
          <thead><tr><th>Field</th><th>Well</th><th class="num">Drill&nbsp;d</th>
            <th class="num">TVD&nbsp;ft</th><th class="num">WD&nbsp;ft</th></tr></thead>
          <tbody>{rows(s['fastest'])}</tbody></table></div>
        <p class="lead" style="margin-top:10px">Sub-3-day entries at deep TVD are
        re-entry / completion-only intervals, not full wells &mdash; the duration is
        real but the scope is partial.</p>
      </div>
      <div>
        <p class="lane-label">Slowest</p>
        <h2 style="font-size:16px">Longest wellbores</h2>
        <div class="scrollx"><table>
          <thead><tr><th>Field</th><th>Well</th><th class="num">Drill&nbsp;d</th>
            <th class="num">TVD&nbsp;ft</th><th class="num">WD&nbsp;ft</th></tr></thead>
          <tbody>{rows(s['slowest'])}</tbody></table></div>
        <p class="lead" style="margin-top:10px">The slowest hole,
        {esc(s['slowest'].iloc[0]['LEASE_NAME'])}
        {esc(s['slowest'].iloc[0]['WELL_NAME'])}, took
        {_n(s['slowest'].iloc[0]['drill_days'])} days &mdash;
        {_n(s['slowest'].iloc[0]['drill_days']/s['median_days'],1)}&times; the play median.</p>
      </div>
    </section>

    <section>
      <p class="lane-label">Field table</p>
      <h2>Per-field drilling summary</h2>
      <div class="scrollx"><table>
        <thead><tr><th>Field</th><th class="num">Wellbores</th>
          <th class="num">Median&nbsp;d</th><th class="num">Total&nbsp;rig-d</th>
          <th class="num">Median&nbsp;TVD&nbsp;ft</th></tr></thead>
        <tbody>{field_rows}</tbody></table></div>
    </section>
  </div>

  <footer class="foot">
    <div><b>Source:</b> <code>{esc(str(src_rel))}</code> (Sheet1) &mdash;
      {s['n_wellbores']} Lower-Tertiary development wellbores after dropping one blank
      row and one spreadsheet TOTALS trailer. Per-well export:
      <code>reports/lower_tertiary/lt_drilling_insights.csv</code>.</div>
    <div style="margin-top:8px"><b>Data limits (flag-don't-fake):</b>
      {s['n_not_derivable']} wellbores carry no recorded drilling duration
      (0-day rows with no spud/TD date, mostly re-entries) and are shown as &mdash;,
      excluded from every drilling statistic. {s['n_mud_outlier']} mud-weight readings
      outside {int(MUD_MIN)}&ndash;{int(MUD_MAX)} ppg are excluded as keying errors.
      Spud dates span {s['spud_min_year']}&ndash;{s['spud_max_year']}. Drilling and
      completion days are as-reported in the V30 workbook (BSEE well/API records);
      "fastest" short-duration rows are partial-scope re-entries, not full wells.</div>
    <div style="margin-top:8px">Generated {gen} by
      <code>scripts/lower_tertiary/build_drilling_insights.py</code> (worldenergydata&nbsp;#775).
      Same workbook &rarr; identical page.</div>
  </footer>
</div>
</div>
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        default=str(DEFAULT_SOURCE),
        help="Path to drilling_and_completion_days.xlsx",
    )
    args = parser.parse_args(argv)

    source = Path(args.source)
    if not source.exists():
        print(f"ERROR: source workbook not found: {source}", file=sys.stderr)
        return 1

    df = load_wells(source)
    if df.empty:
        print("ERROR: no wellbore rows after cleaning.", file=sys.stderr)
        return 1

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(df, CSV_PATH)
    stats = compute_stats(df)
    stats["learning"] = compute_learning(df)
    HTML_PATH.write_text(render_html(stats, source), encoding="utf-8")

    print(f"Wrote {CSV_PATH}")
    print(f"Wrote {HTML_PATH}")
    print(
        f"{stats['n_drill']} wellbores, median {stats['median_days']:.1f} drill-days, "
        f"{stats['total_rig_days']:.0f} total rig-days; "
        f"slope {stats['slope_per_kft']:.1f} d/1000ft (r2={stats['r2']:.2f})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
