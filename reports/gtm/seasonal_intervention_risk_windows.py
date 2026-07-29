#!/usr/bin/env python3
"""
Seasonal Intervention Risk Windows — hurricane season x WAR x operations
(issue #427, child of #423; sibling of #403; reuses #416 WAR/INCINV framing).

Deterministic, pure-stdlib analysis over LOCAL BSEE Well Activity Report (WAR) and
well-operations data. Emits a JSON sidecar (all figures), a markdown memo, and a
static HTML render with an inline SVG monthly chart overlaid on the Atlantic
hurricane-season window.

HARD SEPARATION OF DATA vs ASSUMPTIONS:
  - Every "data" figure traces to LOCAL BSEE WAR-derived CSVs (paths in SOURCES).
    These are the activity-period START dates of real GoM well-operation records.
  - The ONLY non-data inputs are the Atlantic hurricane-season calendar dates
    (Jun 1-Nov 30 season, Aug-Oct peak). These are PUBLIC KNOWLEDGE (NOAA/NHC
    climatology) carried in ASSUMPTIONS and surfaced verbatim. Nothing else is
    assumed; no rates, costs, or significance are invented.

SCOPE-DOWN HONESTY (per #426):
  - The assembled HSE incident DB (data/modules/hse/hse_incidents.db) is a 0-BYTE
    STUB and no raw BSEE INCINV file (mv_acc_investigations.txt) is present locally,
    so an HSE-incident-rate-by-season cut is NOT POSSIBLE here and is omitted.
  - The local WAR/operations extracts are SAMPLE CSVs with small N (~100-order
    records). This analysis is therefore DESCRIPTIVE ONLY. No statistical-
    significance claim (e.g. the #416 Bonferroni p<0.0125 target) is made; the
    sample is too small to support one and that limit is stated in the memo.

Run:  PYTHONPATH=src python3 reports/gtm/seasonal_intervention_risk_windows.py
"""
import csv
import datetime
import json
import os
from collections import Counter

DATE = "2026-07-05"
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_DIR = os.path.join(REPO_ROOT, "reports/gtm")
STEM = f"seasonal-intervention-risk-windows-{DATE}"

# ----------------------------------------------------------------------------
# LOCAL DATA SOURCES (all WAR-derived; activity-period START dates) — these are
# the ONLY measured inputs. Each is a relative repo path + the date column used.
# ----------------------------------------------------------------------------
SOURCES = [
    # (label, relpath, date_col, date_fmt)  fmt: "mdy" = M/D/Y[ time]; "iso" = YYYY-MM-DD[ time]
    (
        "well_activity_summary",
        "data/modules/bsee/current/operations/well_activity_summary.csv",
        "WAR_START_DT",
        "mdy",
    ),
    (
        "war_detail_608124003301",
        "docs/modules/bsee/analysis/rig_days/war_data_608124003301.csv",
        "WAR_START_DT",
        "iso",
    ),
    (
        "war_detail_608124009500",
        "docs/modules/bsee/analysis/rig_days/war_data_608124009500.csv",
        "WAR_START_DT",
        "iso",
    ),
]

# Activity-code grouping for intervention-type read (BSEE WELL_ACTIVITY_CD).
#
# NOT A DEFINITION SOURCE (#1065). This dict is a frozen copy kept only so this
# dated, pure-stdlib report reproduces byte-for-byte; it is known to be wrong in
# two ways and must not be copied forward:
#   * It attaches meanings to codes BSEE has never defined. WO, PND, CHZ, MPF,
#     REC and TBK have NO published meaning in any BSEE domain; "PND" in
#     particular is not "sidetrack-bypass" or anything else -- it is unknown.
#   * "RC" and "BP" are not real: neither token appears anywhere in
#     mv_war_main_prop. The actual twelve are DRL COM TA PA ST DSI WO CHZ PND
#     MPF REC TBK (plus 882 null rows, 1997-2001).
#
# The canonical, provenance-tiered source is
#   packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/data/war_activity_codes.yml
# loaded via worldenergydata.bsee.analysis.war_activity_codes.activity_labels().
# It is not imported here only because this script is deliberately stdlib-only.
ACTIVITY_MEANING = {
    "DRL": "Drilling",
    "COM": "Completion",
    "PA": "Plug & abandon (P&A)",
    "TA": "Temporary abandonment",
    "PND": "Pending / sidetrack-bypass",
    "WO": "Workover",
    "RC": "Recompletion",
    "ST": "Sidetrack",
    "BP": "Bypass",
}

# ----------------------------------------------------------------------------
# ASSUMPTIONS (NOT data) — public-knowledge hurricane-season calendar only.
# ----------------------------------------------------------------------------
ASSUMPTIONS = {
    "atlantic_hurricane_season": {
        "season_months": [6, 7, 8, 9, 10, 11],  # Jun 1 - Nov 30
        "peak_months": [8, 9, 10],  # Aug - Oct climatological peak
        "season_label": "Jun 1 - Nov 30",
        "peak_label": "Aug - Oct",
        "source": "NOAA National Hurricane Center — official Atlantic hurricane "
        "season (Jun 1-Nov 30) and climatological peak (mid-Aug to "
        "mid-Oct). Public knowledge.",
        "note": "GoM operations face elevated storm-evacuation, deferral, and "
        "weather-window risk in these months; this is the ONLY non-data "
        "input and is used purely to overlay the measured monthly cut.",
    },
    "data_as_of": DATE,
}

MONTH_ABBR = [
    "",
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]
SEASON_OF_MONTH = {
    12: "Winter",
    1: "Winter",
    2: "Winter",
    3: "Spring",
    4: "Spring",
    5: "Spring",
    6: "Summer",
    7: "Summer",
    8: "Summer",
    9: "Fall",
    10: "Fall",
    11: "Fall",
}


def _month_year(raw, fmt):
    s = (raw or "").strip()
    if not s:
        return None
    part = s.split(" ")[0]
    try:
        if fmt == "mdy":
            m, _d, y = part.split("/")
            return int(m), int(y)
        else:  # iso
            y, m, _d = part.split("-")
            return int(m), int(y)
    except (ValueError, IndexError):
        return None


def load_records():
    """Return list of (month, year, activity_cd, source_label) for every
    parseable WAR-period start date across local sources. DATA ONLY."""
    recs = []
    per_source = {}
    for label, rel, col, fmt in SOURCES:
        path = os.path.join(REPO_ROOT, rel)
        rows = 0
        ok = 0
        if os.path.exists(path):
            with open(path, encoding="utf-8", errors="replace") as f:
                r = csv.DictReader(f)
                for row in r:
                    rows += 1
                    my = _month_year(row.get(col), fmt)
                    if my:
                        ok += 1
                        act = (row.get("WELL_ACTIVITY_CD") or "").strip().upper()
                        recs.append((my[0], my[1], act, label))
        per_source[label] = {"path": rel, "rows": rows, "parseable_dates": ok}
    return recs, per_source


def compute():
    recs, per_source = load_records()
    hs = ASSUMPTIONS["atlantic_hurricane_season"]
    season_months = set(hs["season_months"])
    peak_months = set(hs["peak_months"])

    by_month = Counter(r[0] for r in recs)
    by_season = Counter(SEASON_OF_MONTH[r[0]] for r in recs)
    by_year = Counter(r[1] for r in recs)
    by_activity = Counter(r[2] or "(blank)" for r in recs)
    total = len(recs)

    in_season = sum(c for m, c in by_month.items() if m in season_months)
    in_peak = sum(c for m, c in by_month.items() if m in peak_months)
    off_season = total - in_season

    # Per-month detail with hurricane flags
    months = []
    for m in range(1, 13):
        c = by_month.get(m, 0)
        months.append(
            {
                "month": m,
                "label": MONTH_ABBR[m],
                "count": c,
                "share": (c / total) if total else 0.0,
                "in_hurricane_season": m in season_months,
                "is_peak": m in peak_months,
            }
        )

    # Lower-risk operating windows = non-hurricane-season months ranked by
    # observed activity (descending), purely descriptive.
    off_season_months = [mm for mm in months if not mm["in_hurricane_season"]]
    off_season_ranked = sorted(
        off_season_months, key=lambda x: (-x["count"], x["month"])
    )

    # Activity-type split inside vs outside hurricane season (DATA).
    act_split = {}
    for m, y, act, lbl in recs:
        key = act or "(blank)"
        d = act_split.setdefault(key, {"in_season": 0, "off_season": 0, "total": 0})
        d["total"] += 1
        if m in season_months:
            d["in_season"] += 1
        else:
            d["off_season"] += 1

    payload = {
        "meta": {
            "issue": 427,
            "parent": 423,
            "siblings": [403, 416],
            "title": "Seasonal intervention risk windows — hurricane season x WAR x operations",
            "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "date": DATE,
            "descriptive_only": True,
            "statistical_significance_claimed": False,
        },
        "data_sources": per_source,
        "data_scope_note": (
            "WAR-derived activity-period START dates from local BSEE sample CSVs. "
            "HSE-incident-by-season omitted: hse_incidents.db is a 0-byte stub and "
            "no raw BSEE INCINV (mv_acc_investigations.txt) is present locally. "
            "Small N => descriptive only, no significance test."
        ),
        "assumptions": ASSUMPTIONS,
        "data": {
            "total_records": total,
            "years_present": sorted(by_year),
            "by_year": {str(k): v for k, v in sorted(by_year.items())},
            "by_month": {str(m): by_month.get(m, 0) for m in range(1, 13)},
            "months": months,
            "by_season": {
                s: by_season.get(s, 0) for s in ["Winter", "Spring", "Summer", "Fall"]
            },
            "by_activity": dict(sorted(by_activity.items(), key=lambda x: -x[1])),
            "activity_meaning": ACTIVITY_MEANING,
            "activity_season_split": act_split,
        },
        "overlay": {
            "hurricane_season_months": hs["season_months"],
            "hurricane_peak_months": hs["peak_months"],
            "records_in_hurricane_season": in_season,
            "records_in_peak": in_peak,
            "records_off_season": off_season,
            "share_in_hurricane_season": (in_season / total) if total else 0.0,
            "share_in_peak": (in_peak / total) if total else 0.0,
            "share_off_season": (off_season / total) if total else 0.0,
            "lower_risk_windows_ranked": [
                {"month": mm["label"], "count": mm["count"]} for mm in off_season_ranked
            ],
        },
    }
    return payload


# ----------------------------------------------------------------------------
# Markdown memo
# ----------------------------------------------------------------------------
def render_md(p):
    d = p["data"]
    ov = p["overlay"]
    hs = p["assumptions"]["atlantic_hurricane_season"]
    L = []
    L.append(
        "# Seasonal Intervention Risk Windows — Hurricane Season × WAR × Operations\n"
    )
    L.append(
        f"*Issue #427 · child of #423 · sibling of #403 / #416 · data as of {DATE} · "
        "aggregate-only · **descriptive only (small N, no significance test)***\n"
    )

    L.append("## TL;DR\n")
    L.append(
        f"- **{d['total_records']} WAR-derived operation records** carry a parseable "
        f"activity start date across the local BSEE sample CSVs.\n"
    )
    L.append(
        f"- **{ov['records_in_hurricane_season']} ({ov['share_in_hurricane_season']:.0%})** "
        f"fall inside the Atlantic hurricane season ({hs['season_label']}); "
        f"**{ov['records_in_peak']} ({ov['share_in_peak']:.0%})** fall in the "
        f"climatological peak ({hs['peak_label']}).\n"
    )
    L.append(
        f"- **{ov['records_off_season']} ({ov['share_off_season']:.0%})** fall in the "
        "lower-storm-risk off-season (Dec–May) — the window where weather-driven "
        "deferral and evacuation risk is lowest.\n"
    )
    if ov["lower_risk_windows_ranked"]:
        top = ov["lower_risk_windows_ranked"][:3]
        L.append(
            "- **Lowest-storm-risk months with observed activity (data):** "
            + ", ".join(f"{m['month']} ({m['count']})" for m in top)
            + ".\n"
        )

    L.append("## Data vs assumptions — hard separation\n")
    L.append("| Element | Type | Source |")
    L.append("|---|---|---|")
    L.append(
        "| Monthly/seasonal activity counts | **DATA** | local BSEE WAR CSVs (below) |"
    )
    L.append("| Activity-type split | **DATA** | `WELL_ACTIVITY_CD` in the same CSVs |")
    L.append(
        "| Hurricane-season window (Jun–Nov) & peak (Aug–Oct) | **ASSUMPTION (public)** | "
        "NOAA/NHC climatology |"
    )
    L.append("")
    L.append(
        "> **No HSE-incident-by-season cut** is included: the assembled "
        "`data/modules/hse/hse_incidents.db` is a **0-byte stub** and no raw BSEE "
        "INCINV file (`mv_acc_investigations.txt`) is present locally. The acceptance "
        "criterion asking for a statistically-sane (#416 Bonferroni p<0.0125) HSE-rate "
        "recommendation **cannot be met from local data**; this memo therefore reports "
        "the WAR operations-timing cut only, descriptively. (See #426 scope-down note.)\n"
    )

    L.append("## Local data sources (DATA)\n")
    L.append("| Source | Path | Rows | Parseable dates |")
    L.append("|---|---|---:|---:|")
    for lbl, info in p["data_sources"].items():
        L.append(
            f"| `{lbl}` | `{info['path']}` | {info['rows']} | {info['parseable_dates']} |"
        )
    L.append("")

    L.append("## Monthly distribution overlaid on hurricane season (DATA + overlay)\n")
    L.append("| Month | Records | Share | Hurricane season | Peak |")
    L.append("|---|---:|---:|:--:|:--:|")
    for mm in d["months"]:
        hsf = "🌀 yes" if mm["in_hurricane_season"] else "—"
        pk = "● peak" if mm["is_peak"] else ""
        L.append(
            f"| {mm['label']} | {mm['count']} | {mm['share']:.0%} | {hsf} | {pk} |"
        )
    L.append(f"| **Total** | **{d['total_records']}** | | | |\n")

    L.append("## Seasonal roll-up (DATA)\n")
    L.append("| Meteorological season | Records | Share |")
    L.append("|---|---:|---:|")
    for s in ["Winter", "Spring", "Summer", "Fall"]:
        c = d["by_season"][s]
        sh = (c / d["total_records"]) if d["total_records"] else 0
        L.append(f"| {s} | {c} | {sh:.0%} |")
    L.append("")

    L.append("## Activity-type mix inside vs outside hurricane season (DATA)\n")
    L.append("| Activity | Meaning | In season | Off season | Total |")
    L.append("|---|---|---:|---:|---:|")
    for act, sp in sorted(
        d["activity_season_split"].items(), key=lambda x: -x[1]["total"]
    ):
        mean = d["activity_meaning"].get(act, "")
        L.append(
            f"| `{act}` | {mean} | {sp['in_season']} | {sp['off_season']} | {sp['total']} |"
        )
    L.append("")

    L.append("## Lower-risk operating windows (read-through)\n")
    L.append(
        f"- The Atlantic hurricane season ({hs['season_label']}; source: {hs['source']}) "
        "concentrates storm-evacuation, weather-deferral, and crew-fatigue overlap risk "
        f"in Jun–Nov, peaking {hs['peak_label']}.\n"
    )
    L.append(
        f"- **Off-season (Dec–May)** carried **{ov['records_off_season']} of "
        f"{d['total_records']} ({ov['share_off_season']:.0%})** observed operation starts "
        "in this sample — the descriptively lower-storm-risk scheduling window.\n"
    )
    L.append(
        "- **Operational decision support:** where intervention scope is schedulable, "
        "front-loading discretionary work into the Dec–May off-season (and avoiding the "
        "Aug–Oct peak) reduces exposure to storm-driven deferral. This is a "
        "**directional, descriptive** recommendation — the local sample is too small "
        "(N≈"
        + f"{d['total_records']}"
        + ") to attach a quantified HSE-rate delta or a "
        "significance test.\n"
    )

    L.append("## Caveats\n")
    L.append(
        "- **Small N / sample extracts.** The local BSEE operations CSVs are truncated "
        "samples, not the full census; counts are illustrative of method, not a "
        "population estimate.\n"
    )
    L.append(
        "- **WAR_START_DT = reporting-period start**, a close proxy for when the "
        "operation was active that week; it is not a precise incident timestamp.\n"
    )
    L.append(
        "- **No HSE incident data** locally (0-byte db stub; no raw INCINV) — the "
        "incident-rate-by-season half of #427's scope is deferred to when INCINV lands.\n"
    )
    L.append(
        "- **No metocean current/wave overlay** included; that requires the #403 "
        "metocean datasets, out of scope for this local-only pass.\n"
    )

    L.append("## Cross-links\n")
    L.append(
        "- #403 — hurricane-mooring infrastructure (metocean/storm window source).\n"
    )
    L.append(
        "- #416 — Phase-1A WAR loaders + INCINV classification (loader reuse target).\n"
    )
    L.append("- #423 — marketing-pipeline umbrella (parent).\n")

    L.append("## Reproduce\n")
    L.append(
        "```\nPYTHONPATH=src python3 reports/gtm/seasonal_intervention_risk_windows.py\n```"
    )
    L.append(
        "Deterministic: emits the `.json` sidecar (all figures), this `.md`, and the "
        "`.html`. Every number above is in the JSON.\n"
    )
    L.append(
        f"*Generated {p['meta']['generated_at']} · data as of {DATE} · aggregate-only.*\n"
    )
    return "\n".join(L)


# ----------------------------------------------------------------------------
# Static HTML render (inline SVG, deterministic)
# ----------------------------------------------------------------------------
def render_html(p):
    d = p["data"]
    ov = p["overlay"]
    hs = p["assumptions"]["atlantic_hurricane_season"]

    def esc(x):
        return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Monthly bar chart with hurricane-season band shaded behind.
    counts = [d["by_month"][str(m)] for m in range(1, 13)]
    mx = max(counts) or 1
    bw, gap, h, top = 38, 12, 190, 24
    season_months = set(hs["season_months"])
    peak_months = set(hs["peak_months"])
    left = 44
    # season shading band (Jun..Nov)
    sm = sorted(season_months)
    band_x = left + (sm[0] - 1) * (bw + gap) - gap / 2
    band_w = len(sm) * (bw + gap)
    bars = [
        f'<rect x="{band_x:.0f}" y="{top}" width="{band_w:.0f}" height="{h}" '
        f'fill="#fde68a" opacity="0.5"/>',
        f'<text x="{band_x + band_w/2:.0f}" y="{top+13}" font-size="10" '
        f'text-anchor="middle" fill="#92400e">Hurricane season (Jun–Nov)</text>',
    ]
    for i, v in enumerate(counts):
        m = i + 1
        bh = int(h * v / mx)
        x = left + i * (bw + gap)
        color = (
            "#dc2626"
            if m in peak_months
            else ("#d97706" if m in season_months else "#0e7490")
        )
        bars.append(
            f'<rect x="{x}" y="{top+h-bh}" width="{bw}" height="{bh}" fill="{color}"/>'
            f'<text x="{x+bw/2}" y="{top+h+15}" font-size="10" text-anchor="middle" '
            f'fill="#6B7280">{MONTH_ABBR[m]}</text>'
            f'<text x="{x+bw/2}" y="{top+h-bh-4}" font-size="10" text-anchor="middle" '
            f'fill="#1e3a5f">{v}</text>'
        )
    chart_w = left + 12 * (bw + gap) + 10
    month_svg = (
        f'<svg width="{chart_w}" height="{top+h+30}" style="max-width:100%">'
        f'{"".join(bars)}</svg>'
    )

    def kpi(label, value, unit="", note=""):
        return (
            f'<div class="kpi-card"><div class="label">{esc(label)}</div>'
            f'<div class="value">{esc(value)}<span class="unit">{esc(unit)}</span></div>'
            f'<div class="note">{esc(note)}</div></div>'
        )

    month_rows = ""
    for mm in d["months"]:
        flag = "🌀" if mm["in_hurricane_season"] else ""
        pk = "●" if mm["is_peak"] else ""
        bg = ' style="background:#FEF3C7"' if mm["in_hurricane_season"] else ""
        month_rows += (
            f"<tr{bg}><td>{mm['label']}</td><td>{mm['count']}</td>"
            f"<td>{mm['share']:.0%}</td><td>{flag}</td><td>{pk}</td></tr>"
        )

    season_rows = ""
    for s in ["Winter", "Spring", "Summer", "Fall"]:
        c = d["by_season"][s]
        sh = (c / d["total_records"]) if d["total_records"] else 0
        season_rows += f"<tr><td>{s}</td><td>{c}</td><td>{sh:.0%}</td></tr>"

    act_rows = ""
    for act, sp in sorted(
        d["activity_season_split"].items(), key=lambda x: -x[1]["total"]
    ):
        mean = d["activity_meaning"].get(act, "")
        act_rows += (
            f"<tr><td><code>{esc(act)}</code></td><td>{esc(mean)}</td>"
            f"<td>{sp['in_season']}</td><td>{sp['off_season']}</td>"
            f"<td>{sp['total']}</td></tr>"
        )

    src_rows = ""
    for lbl, info in p["data_sources"].items():
        src_rows += (
            f"<tr><td><code>{esc(lbl)}</code></td><td><code>{esc(info['path'])}</code></td>"
            f"<td>{info['rows']}</td><td>{info['parseable_dates']}</td></tr>"
        )

    lrw = ", ".join(
        f"{m['month']} ({m['count']})" for m in ov["lower_risk_windows_ranked"][:3]
    )

    HTML = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Seasonal Intervention Risk Windows — {DATE}</title>
<style>
body{{font-family:system-ui,-apple-system,BlinkMacSystemFont,sans-serif;margin:0;background:#f8fafc;color:#1F2937}}
.page-wrap{{max-width:1100px;margin:0 auto;padding:24px 20px}}
.report-header{{background:linear-gradient(135deg,#1e3a5f 0%,#b45309 100%);color:#fff;padding:34px 40px;border-radius:10px;margin-bottom:26px}}
.report-header h1{{margin:0 0 6px;font-size:24px;font-weight:700}}
.report-header .sub{{opacity:.85;font-size:14px}}
.report-header .meta{{display:flex;gap:24px;margin-top:16px;font-size:13px;opacity:.8;flex-wrap:wrap}}
.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin-bottom:26px}}
.kpi-card{{background:#fff;border-radius:8px;padding:18px 20px;box-shadow:0 1px 4px rgba(0,0,0,.08);border-top:3px solid #d97706}}
.kpi-card .label{{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.7px;color:#6B7280;margin-bottom:6px}}
.kpi-card .value{{font-size:1.6em;font-weight:700;color:#1e3a5f}}
.kpi-card .unit{{font-size:12px;color:#9ca3af;margin-left:3px}}
.kpi-card .note{{font-size:11px;color:#9ca3af;margin-top:4px}}
.section{{margin-bottom:32px}}
.section h2{{color:#1e3a5f;font-size:18px;border-bottom:2px solid #1e3a5f;padding-bottom:8px;margin:0 0 14px}}
.data-table{{width:100%;border-collapse:collapse;font-size:13px;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
.data-table th{{background:#1e3a5f;color:#fff;padding:9px 13px;text-align:left;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.4px}}
.data-table td{{padding:8px 13px;border-bottom:1px solid #E5E7EB}}
.data-note{{background:#EFF6FF;border-left:4px solid #3B82F6;padding:13px 17px;border-radius:4px;margin:16px 0;font-size:13px;line-height:1.5}}
.warn-note{{background:#FEF3C7;border-left:4px solid #d97706;padding:13px 17px;border-radius:4px;margin:16px 0;font-size:13px;line-height:1.5}}
.assum-note{{background:#F3E8FF;border-left:4px solid #9333ea;padding:13px 17px;border-radius:4px;margin:16px 0;font-size:13px;line-height:1.5}}
.chart-wrap{{background:#fff;border-radius:8px;padding:16px 20px;box-shadow:0 1px 4px rgba(0,0,0,.08);margin-bottom:18px}}
.chart-wrap h4{{margin:0 0 10px;font-size:13px;color:#1e3a5f}}
code{{background:#eef2ff;padding:1px 5px;border-radius:3px;font-size:12px}}
.footer{{font-size:12px;color:#9ca3af;margin-top:28px;border-top:1px solid #E5E7EB;padding-top:14px}}
</style></head><body><div class="page-wrap">
<div class="report-header">
<h1>Seasonal Intervention Risk Windows — Hurricane Season × WAR × Operations</h1>
<div class="sub">When GoM well-operation activity occurs, overlaid on the Atlantic hurricane season · operational scheduling decision-support</div>
<div class="meta"><span>Issue #427 (child of #423)</span><span>Data as of {DATE}</span>
<span>BSEE WAR-derived operations</span><span>Aggregate-only · descriptive</span></div>
</div>

<div class="kpi-grid">
{kpi("WAR records (dated)", f"{d['total_records']}", "", "parseable activity starts (data)")}
{kpi("In hurricane season", f"{ov['share_in_hurricane_season']:.0%}", "", f"{ov['records_in_hurricane_season']} of {d['total_records']} (Jun–Nov)")}
{kpi("In peak Aug–Oct", f"{ov['share_in_peak']:.0%}", "", f"{ov['records_in_peak']} records")}
{kpi("Off-season Dec–May", f"{ov['share_off_season']:.0%}", "", f"{ov['records_off_season']} — lower-storm-risk window")}
</div>

<div class="warn-note"><b>Data vs assumptions — hard separation.</b> All monthly/seasonal/activity
counts are <b>measured</b> from local BSEE WAR-derived CSVs. The <b>only</b> non-data input is the
Atlantic hurricane-season calendar (Jun 1–Nov 30 season, Aug–Oct peak), which is <b>public NOAA/NHC
climatology</b>, used purely to overlay the measured counts.
<b>This is a descriptive analysis</b> — the local extracts are small sample CSVs (N={d['total_records']}),
so no statistical-significance claim is made.</div>

<div class="warn-note"><b>Scope-down (per #426).</b> The assembled
<code>data/modules/hse/hse_incidents.db</code> is a <b>0-byte stub</b> and no raw BSEE INCINV file
(<code>mv_acc_investigations.txt</code>) is present locally, so the HSE-incident-rate-by-season cut and
the #416 Bonferroni-significance recommendation <b>cannot be produced from local data</b> and are
deferred. This report delivers the WAR operations-timing × hurricane-season overlay only.</div>

<div class="section"><h2>1 · Monthly activity vs hurricane season</h2>
<div class="chart-wrap"><h4>WAR-derived operation starts by month (shaded = hurricane season; red = Aug–Oct peak)</h4>
{month_svg}</div>
<table class="data-table"><thead><tr><th>Month</th><th>Records</th><th>Share</th><th>Hurricane</th><th>Peak</th></tr></thead>
<tbody>{month_rows}<tr><td><b>Total</b></td><td><b>{d['total_records']}</b></td><td></td><td></td><td></td></tr></tbody></table>
</div>

<div class="section"><h2>2 · Seasonal roll-up</h2>
<table class="data-table"><thead><tr><th>Meteorological season</th><th>Records</th><th>Share</th></tr></thead>
<tbody>{season_rows}</tbody></table>
<div class="data-note"><b>Lower-storm-risk off-season (Dec–May):</b> {ov['records_off_season']} of
{d['total_records']} observed operation starts ({ov['share_off_season']:.0%}). Months with most observed
off-season activity: {esc(lrw)}.</div>
</div>

<div class="section"><h2>3 · Activity-type mix in vs out of season</h2>
<table class="data-table"><thead><tr><th>Activity</th><th>Meaning</th><th>In season</th><th>Off season</th><th>Total</th></tr></thead>
<tbody>{act_rows}</tbody></table>
</div>

<div class="section"><h2>4 · Operational decision-support read-through</h2>
<div class="assum-note"><b>Hurricane-season window (assumption — public):</b> {esc(hs['source'])}</div>
<p>Where intervention scope is schedulable, front-loading discretionary work into the
<b>Dec–May off-season</b> (and avoiding the <b>Aug–Oct peak</b>) reduces exposure to storm-driven
deferral, evacuation, and weather-window loss. This is a <b>directional, descriptive</b> recommendation;
the local sample (N={d['total_records']}) is too small to attach a quantified HSE-rate delta or a
significance test — that awaits the INCINV/HSE data and the #403 metocean overlay.</p>
</div>

<div class="section"><h2>5 · Local data sources (data)</h2>
<table class="data-table"><thead><tr><th>Source</th><th>Path</th><th>Rows</th><th>Parseable dates</th></tr></thead>
<tbody>{src_rows}</tbody></table>
</div>

<div class="footer">
Cross-links: #403 (hurricane-mooring / metocean) · #416 (WAR loaders + INCINV classification) · #423 (parent).<br>
Reproduce: <code>PYTHONPATH=src python3 reports/gtm/seasonal_intervention_risk_windows.py</code> ·
Generated {esc(p['meta']['generated_at'])} · data as of {DATE} · aggregate-only.
</div>
</div></body></html>"""
    return HTML


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    payload = compute()
    base = os.path.join(OUT_DIR, STEM)
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    with open(base + ".md", "w", encoding="utf-8") as f:
        f.write(render_md(payload))
    with open(base + ".html", "w", encoding="utf-8") as f:
        f.write(render_html(payload))
    print(f"wrote {base}.json / .md / .html")
    print(
        f"total_records={payload['data']['total_records']} "
        f"in_season={payload['overlay']['records_in_hurricane_season']} "
        f"in_peak={payload['overlay']['records_in_peak']} "
        f"off_season={payload['overlay']['records_off_season']}"
    )


if __name__ == "__main__":
    main()
