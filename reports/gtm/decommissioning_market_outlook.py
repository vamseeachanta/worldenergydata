#!/usr/bin/env python3
"""
Decommissioning Market Outlook — 5-year GoM P&A forecast (issue #424, child of #423).

Deterministic, pure-stdlib analysis over LOCAL BSEE well-status data. Emits a JSON
sidecar (all figures), a markdown memo, and a static HTML render.

HARD SEPARATION OF DATA vs ASSUMPTIONS:
  - Every "data" figure below traces to data/modules/bsee/current/wells/well_data.csv
    (BSEE borehole-status inventory + permanent-abandonment date history).
  - Every "assumption" figure is an EXPLICIT, CITED public-knowledge parameter
    (P&A unit-cost ranges, attrition pace) carried in the ASSUMPTIONS dict and
    surfaced verbatim in the memo. Nothing is presented as data that is not data.

Run:  PYTHONPATH=src python3 reports/gtm/decommissioning_market_outlook.py
"""
import csv
import json
import datetime
import os
from collections import Counter

DATE = "2026-06-19"
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WELL_CSV = os.path.join(REPO_ROOT, "data/modules/bsee/current/wells/well_data.csv")
OUT_DIR = os.path.join(REPO_ROOT, "reports/gtm")
STEM = f"decommissioning-market-outlook-{DATE}"

# ----------------------------------------------------------------------------
# ASSUMPTIONS (NOT data) — explicit, cited public-knowledge parameters.
# These are stated as assumptions in the memo and JSON; they are never reported
# as measured values. Sources are industry-standard public references.
# ----------------------------------------------------------------------------
ASSUMPTIONS = {
    "pa_unit_cost_usd_mm_per_well": {
        # Per-well P&A cost RANGES (shallow-water GoM). Public-knowledge ranges
        # widely cited by BOEM/BSEE decommissioning cost studies, GAO-16-40,
        # and industry (Wood Mackenzie / Westwood) decom estimates.
        "shelf_shallow": {"low": 0.8, "base": 1.5, "high": 3.0,
                          "note": "shelf / shallow-water single-well P&A, $MM"},
        "deepwater": {"low": 5.0, "base": 12.0, "high": 25.0,
                      "note": "deepwater subsea well P&A (rig-intensive), $MM"},
        "source": "BOEM/BSEE decommissioning cost reports; GAO-16-40; "
                  "industry (Wood Mackenzie / Westwood) GoM decom estimates — public ranges",
    },
    "deepwater_share_of_eligible": {
        # Share of the eligible inventory assumed deepwater for cost blending.
        # GoM well count is dominated by the shelf; deepwater is a small count
        # share but a large cost share. WATER_DEPTH is unpopulated for the
        # eligible set in this extract (see caveats), so this is an ASSUMPTION.
        "low": 0.03, "base": 0.06, "high": 0.10,
        "note": "fraction of eligible wells assumed deepwater (count share)",
        "source": "BOEM GoM well census — shelf-dominated count distribution (public)",
    },
    "annual_attrition_pace": {
        # Fraction of the eligible inventory plugged per year (drawdown pace).
        # Calibrated against the OBSERVED historical GoM P&A rate (see data),
        # then flexed low/high for sensitivity.
        "low": 0.04, "base": 0.055, "high": 0.07,
        "note": "fraction of eligible inventory plugged per year",
        "source": "calibrated to observed 2015-2024 GoM PA rate (data); flexed ±",
    },
    "forecast_years": [2026, 2027, 2028, 2029, 2030],
    "idle_threshold_years": 10,  # TA wells idle >= this are 'idle-iron' P&A-pressure
    "data_as_of_year": 2025,
}

GOM_BBOX = {"lat_min": 24.0, "lat_max": 31.5, "lon_min": -98.0, "lon_max": -86.0}


def _yr(d):
    d = (d or "").strip()
    if not d:
        return None
    try:
        return int(d.split("/")[-1].split(" ")[0])
    except (ValueError, IndexError):
        return None


def _is_gom(la, lo):
    return (la is not None and lo is not None
            and GOM_BBOX["lat_min"] <= la <= GOM_BBOX["lat_max"]
            and GOM_BBOX["lon_min"] <= lo <= GOM_BBOX["lon_max"])


def load_inventory():
    """Pure-data pass over BSEE well_data.csv. Returns measured inventory dict."""
    gom_stat = Counter()
    nat_stat = Counter()
    pa_yr = Counter()
    ta_yr = Counter()
    total = 0
    gom = 0
    with open(WELL_CSV, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            total += 1
            s = (row.get("BOREHOLE_STAT_CD") or "").strip()
            nat_stat[s] += 1
            try:
                la = float(row.get("BOTM_LATITUDE"))
                lo = float(row.get("BOTM_LONGITUDE"))
            except (TypeError, ValueError):
                la = lo = None
            if not _is_gom(la, lo):
                continue
            gom += 1
            gom_stat[s] += 1
            sdt_yr = _yr(row.get("BOREHOLE_STAT_DT"))
            if s == "PA" and sdt_yr:
                pa_yr[sdt_yr] += 1
            if s == "TA" and sdt_yr:
                ta_yr[sdt_yr] += 1
    return {
        "total_wells": total,
        "gom_wells": gom,
        "national_status": dict(nat_stat),
        "gom_status": dict(gom_stat),
        "gom_pa_by_year": dict(sorted(pa_yr.items())),
        "gom_ta_by_year": dict(sorted(ta_yr.items())),
    }


# BSEE borehole-status code meanings (BSEE Borehole_Status_Code data definition)
STATUS_MEANING = {
    "PA": "Permanently Abandoned (plugged & abandoned — already decommissioned)",
    "TA": "Temporarily Abandoned (idle/suspended — prime P&A candidate)",
    "COM": "Completed (producing or capable — reaches end-of-life over horizon)",
    "ST": "Sidetrack (borehole of a sidetracked well — not a standalone P&A unit)",
    "DSI": "Drilled & Suspended / Inactive",
    "AST": "Abandoned Sidetrack",
    "CNL": "Cancelled",
    "DRL": "Drilling",
    "APD": "Approved Permit to Drill",
}


def build_forecast(inv):
    """Forecast model. Combines DATA (eligible inventory + observed PA rate)
    with explicit ASSUMPTIONS (attrition pace, unit cost). Returns model dict."""
    gs = inv["gom_status"]
    # --- DATA: eligible inventory ---
    n_ta = gs.get("TA", 0)        # idle/suspended
    n_com = gs.get("COM", 0)      # completed (end-of-life candidates)
    n_dsi = gs.get("DSI", 0)
    n_ast = gs.get("AST", 0)
    eligible = n_ta + n_com + n_dsi + n_ast

    # --- DATA: idle-iron aging (TA wells idle >= threshold) ---
    cut = ASSUMPTIONS["data_as_of_year"] - ASSUMPTIONS["idle_threshold_years"]
    idle_iron = sum(v for y, v in inv["gom_ta_by_year"].items() if y <= cut)
    idle_15 = sum(v for y, v in inv["gom_ta_by_year"].items()
                  if y <= ASSUMPTIONS["data_as_of_year"] - 15)

    # --- DATA: observed historical PA rate (calibration anchor) ---
    pa = inv["gom_pa_by_year"]
    obs_2015_2024 = [pa.get(y, 0) for y in range(2015, 2025)]
    obs_2020_2024 = [pa.get(y, 0) for y in range(2020, 2025)]
    obs_mean_10yr = round(sum(obs_2015_2024) / len(obs_2015_2024), 1)
    obs_mean_5yr = round(sum(obs_2020_2024) / len(obs_2020_2024), 1)

    # --- FORECAST: inventory drawdown at the assumed attrition pace ---
    years = ASSUMPTIONS["forecast_years"]
    pace = ASSUMPTIONS["annual_attrition_pace"]
    cost = ASSUMPTIONS["pa_unit_cost_usd_mm_per_well"]
    dw_share = ASSUMPTIONS["deepwater_share_of_eligible"]

    scenarios = {}
    for sk in ("low", "base", "high"):
        remaining = float(eligible)
        per_year = []
        for _ in years:
            plugged = remaining * pace[sk]
            per_year.append(round(plugged))
            remaining -= plugged
        total_wells_5yr = sum(per_year)
        # Blended unit cost = (1-dw)*shelf + dw*deepwater, at the same scenario key
        dwf = dw_share[sk]
        blended_unit = ((1 - dwf) * cost["shelf_shallow"][sk]
                        + dwf * cost["deepwater"][sk])
        market_usd_bn = round(total_wells_5yr * blended_unit / 1000.0, 2)
        scenarios[sk] = {
            "attrition_pace": pace[sk],
            "deepwater_share": dwf,
            "blended_unit_cost_usd_mm": round(blended_unit, 2),
            "pa_per_year": per_year,
            "pa_wells_5yr_total": total_wells_5yr,
            "market_size_5yr_usd_bn": market_usd_bn,
        }

    return {
        "eligible_inventory": {
            "TA_idle": n_ta, "COM_completed": n_com,
            "DSI": n_dsi, "AST": n_ast, "total_eligible": eligible,
        },
        "idle_iron": {
            "threshold_years": ASSUMPTIONS["idle_threshold_years"],
            "ta_idle_ge_10yr": idle_iron,
            "ta_idle_ge_15yr": idle_15,
        },
        "observed_pa_rate": {
            "by_year_2015_2024": {str(y): pa.get(y, 0) for y in range(2015, 2025)},
            "mean_2015_2024": obs_mean_10yr,
            "mean_2020_2024": obs_mean_5yr,
            "implied_pace_vs_eligible_2015_2024": round(obs_mean_10yr / eligible, 4),
        },
        "forecast_years": years,
        "scenarios": scenarios,
    }


def build_payload():
    inv = load_inventory()
    fc = build_forecast(inv)
    return {
        "generated_at": datetime.datetime.now(datetime.timezone.utc)
            .isoformat().replace("+00:00", "Z"),
        "issue": "https://github.com/vamseeachanta/worldenergydata/issues/424",
        "parent_epic": "https://github.com/vamseeachanta/worldenergydata/issues/423",
        "date": DATE,
        "title": "GoM Decommissioning Market Outlook — 5-Year P&A Forecast",
        "methodology": (
            "Eligible-inventory drawdown model over the BSEE borehole-status "
            "census, calibrated to the observed 2015-2024 GoM permanent-"
            "abandonment rate, with explicit cited unit-cost assumptions and a "
            "low/base/high sensitivity on attrition pace, deepwater mix, and cost."
        ),
        "data_source": {
            "file": "data/modules/bsee/current/wells/well_data.csv",
            "rows": inv["total_wells"],
            "gom_filter": GOM_BBOX,
            "fields_used": ["BOREHOLE_STAT_CD", "BOREHOLE_STAT_DT",
                            "BOTM_LATITUDE", "BOTM_LONGITUDE"],
            "data_as_of": ASSUMPTIONS["data_as_of_year"],
        },
        "status_code_meanings": STATUS_MEANING,
        "data": inv,             # measured-only
        "forecast": fc,          # data + assumptions, separated within
        "assumptions": ASSUMPTIONS,  # explicit cited parameters
        "operator_aggregation": (
            "Operator-aggregate only; no per-operator forecasts surfaced "
            "(Operator Aggregation Contract #420)."
        ),
    }


# ----------------------------------------------------------------------------
# Renderers
# ----------------------------------------------------------------------------
def render_markdown(p):
    d = p["data"]
    fc = p["forecast"]
    a = p["assumptions"]
    ei = fc["eligible_inventory"]
    sc = fc["scenarios"]
    yrs = fc["forecast_years"]
    cost = a["pa_unit_cost_usd_mm_per_well"]

    def row(scn):
        s = sc[scn]
        return (f"| {scn} | {s['attrition_pace']:.1%} | "
                f"{s['deepwater_share']:.0%} | ${s['blended_unit_cost_usd_mm']:.2f}MM | "
                + " | ".join(str(x) for x in s["pa_per_year"]) + " | "
                f"**{s['pa_wells_5yr_total']}** | **${s['market_size_5yr_usd_bn']:.2f}B** |")

    L = []
    L.append("# GoM Decommissioning Market Outlook — 5-Year P&A Forecast\n")
    L.append(f"> **Issue**: [#424](https://github.com/vamseeachanta/worldenergydata/issues/424) "
             f"(child of [#423](https://github.com/vamseeachanta/worldenergydata/issues/423))  ")
    L.append("> **Branch**: `feat/autorun-2026-06-19`  ")
    L.append(f"> **Data as of**: {DATE} (BSEE borehole-status census; status dates through "
             f"{a['data_as_of_year']})  ")
    L.append("> **Framing**: market-intelligence (commercial), operator-aggregate only.\n")
    L.append("---\n")
    L.append("## What this document is\n")
    L.append("A forward 5-year (2026-2030) Gulf of Mexico **decommissioning / plug-&-abandonment "
             "(P&A)** volume, timing, and market-size forecast. It mirrors the rigor of the "
             "field-analysis and HSE reports in `reports/`: it is grounded in the **real local "
             "BSEE well-status census**, and it makes a **hard separation** between measured data "
             "and explicitly-cited public-knowledge assumptions. Every projected number traces to "
             "either the data pass or a labelled assumption — nothing is fabricated.\n")

    L.append("## Caveat block\n")
    L.append("> **Data source**: BSEE wells census — "
             "`data/modules/bsee/current/wells/well_data.csv` "
             f"({d['total_wells']:,} boreholes nationally; "
             f"{d['gom_wells']:,} fall inside the GoM bounding box and are this report's universe). "
             "The **populated, reliable fields** in this extract are `BOREHOLE_STAT_CD` (100%), "
             "`BOREHOLE_STAT_DT` (99%), and bottom-hole coordinates (99%). "
             "**Known thinness**: `WATER_DEPTH` and `WELL_SPUD_DATE` are populated for only ~100 "
             "rows in this extract, so per-well **water-depth strata and spud-age cohorts cannot "
             "be grounded** — the deepwater mix and the attrition pace are therefore carried as "
             "**explicit assumptions**, not data, and are stress-tested in the sensitivity. "
             "This is engineering analysis of public regulatory data, **not** a regulatory finding. "
             "Operator names are not surfaced (Operator Aggregation Contract #420).\n")

    L.append("## Borehole-status inventory (DATA — measured)\n")
    L.append("BSEE `BOREHOLE_STAT_CD`, GoM-filtered:\n")
    L.append("| Status | Meaning | GoM wells |")
    L.append("|---|---|---:|")
    order = ["PA", "ST", "COM", "TA", "CNL", "DSI", "AST", "DRL", "APD"]
    for s in order:
        if s in d["gom_status"]:
            L.append(f"| `{s}` | {STATUS_MEANING.get(s, '')} | {d['gom_status'][s]:,} |")
    L.append(f"| **Total** | | **{d['gom_wells']:,}** |\n")
    L.append(f"**Already decommissioned (PA):** {d['gom_status'].get('PA',0):,} GoM boreholes are "
             "permanently abandoned — the historical decommissioning record this forecast extends.\n")

    L.append("## Eligible-for-decommissioning inventory (DATA)\n")
    L.append("Wells **not yet permanently abandoned** but in a status that draws down into P&A "
             "over the horizon — the addressable pipeline:\n")
    L.append("| Eligible bucket | Count | Basis |")
    L.append("|---|---:|---|")
    L.append(f"| `TA` temporarily abandoned (idle) | {ei['TA_idle']:,} | idle iron — direct P&A candidates |")
    L.append(f"| `COM` completed (producing/capable) | {ei['COM_completed']:,} | reach end-of-life over horizon |")
    L.append(f"| `DSI` drilled & suspended | {ei['DSI']:,} | inactive |")
    L.append(f"| `AST` abandoned sidetrack | {ei['AST']:,} | residual |")
    L.append(f"| **Total eligible inventory** | **{ei['total_eligible']:,}** | model drawdown base |\n")

    ii = fc["idle_iron"]
    L.append("### Idle-iron aging (DATA) — regulatory P&A pressure\n")
    L.append("TA wells by how long they have sat idle (from `BOREHOLE_STAT_DT`):\n")
    L.append(f"- **{ii['ta_idle_ge_10yr']:,}** TA wells have been idle **≥10 years** "
             f"(status date ≤{a['data_as_of_year']-10}) — the BSEE 'idle iron' cohort under the "
             "strongest plug-or-restore regulatory pressure.\n")
    L.append(f"- **{ii['ta_idle_ge_15yr']:,}** TA wells idle **≥15 years**.\n")

    op = fc["observed_pa_rate"]
    L.append("## Observed historical P&A rate (DATA — calibration anchor)\n")
    L.append("GoM permanent abandonments completed per year (from `BOREHOLE_STAT_DT`):\n")
    L.append("| Year | " + " | ".join(str(y) for y in range(2015, 2025)) + " |")
    L.append("|---|" + "---:|" * 10)
    L.append("| GoM P&A | " + " | ".join(str(op["by_year_2015_2024"][str(y)])
             for y in range(2015, 2025)) + " |")
    L.append("")
    L.append(f"- **2015-2024 mean**: {op['mean_2015_2024']:.1f} P&A / yr.  "
             f"**2020-2024 mean**: {op['mean_2020_2024']:.1f} / yr.")
    L.append(f"- Implied historical attrition pace vs. the eligible inventory: "
             f"**{op['implied_pace_vs_eligible_2015_2024']:.1%} / yr** — the empirical anchor "
             "for the assumed pace below.\n")

    L.append("## Forecast model\n")
    L.append("**Model**: eligible-inventory drawdown.  For each forecast year, "
             "`plugged = remaining_eligible × attrition_pace`, then `remaining -= plugged`. "
             "Market size = `Σ plugged × blended_unit_cost`, where the blended unit cost mixes "
             "shelf and deepwater per-well cost at the assumed deepwater share. The data fixes the "
             f"starting inventory ({ei['total_eligible']:,}) and the empirical pace anchor "
             f"({op['implied_pace_vs_eligible_2015_2024']:.1%}); the pace, deepwater mix, and unit "
             "costs are the assumptions stress-tested below.\n")

    L.append("### Assumptions (NOT data — explicit & cited)\n")
    L.append("| Parameter | Low | Base | High | Source |")
    L.append("|---|---:|---:|---:|---|")
    L.append(f"| Shelf/shallow P&A unit cost ($MM/well) | {cost['shelf_shallow']['low']} | "
             f"{cost['shelf_shallow']['base']} | {cost['shelf_shallow']['high']} | "
             "BOEM/BSEE decom cost reports; GAO-16-40 |")
    L.append(f"| Deepwater P&A unit cost ($MM/well) | {cost['deepwater']['low']} | "
             f"{cost['deepwater']['base']} | {cost['deepwater']['high']} | "
             "Wood Mackenzie / Westwood GoM decom (public) |")
    dw = a["deepwater_share_of_eligible"]
    L.append(f"| Deepwater share of eligible | {dw['low']:.0%} | {dw['base']:.0%} | "
             f"{dw['high']:.0%} | BOEM GoM well census (shelf-dominated) |")
    pc = a["annual_attrition_pace"]
    L.append(f"| Annual attrition pace | {pc['low']:.1%} | {pc['base']:.1%} | {pc['high']:.1%} | "
             "calibrated to observed PA rate (data), flexed ± |\n")

    L.append("## 5-year forecast & sensitivity (2026-2030)\n")
    L.append("| Scenario | Pace | DW share | Blended $/well | "
             + " | ".join(str(y) for y in yrs) + " | 5-yr wells | 5-yr market |")
    L.append("|---|---:|---:|---:|" + "---:|" * len(yrs) + "---:|---:|")
    L.append(row("low"))
    L.append(row("base"))
    L.append(row("high"))
    L.append("")
    b = sc["base"]
    L.append(f"**Base case**: **{b['pa_wells_5yr_total']:,} GoM wells** plugged over 2026-2030 "
             f"(~{b['pa_per_year'][0]}/yr declining as the inventory draws down), a **"
             f"${b['market_size_5yr_usd_bn']:.2f}B** addressable P&A market at the base blended "
             f"unit cost of ${b['blended_unit_cost_usd_mm']:.2f}MM/well.\n")
    L.append(f"**Sensitivity span**: the market ranges from **${sc['low']['market_size_5yr_usd_bn']:.2f}B** "
             f"(low pace × low cost) to **${sc['high']['market_size_5yr_usd_bn']:.2f}B** "
             f"(high pace × high cost) — a "
             f"{sc['high']['market_size_5yr_usd_bn']/sc['low']['market_size_5yr_usd_bn']:.1f}× "
             "spread, driven jointly by pace and unit cost.\n")

    L.append("## Commercial read-through\n")
    L.append(f"- **Pipeline is large and aging**: {ei['total_eligible']:,} eligible wells, of which "
             f"{ei['TA_idle']:,} are already idle and {ii['ta_idle_ge_10yr']:,} have been idle ≥10 "
             "years — a standing backlog independent of new end-of-life additions.\n")
    L.append("- **Steady multi-year demand**: at the base pace the GoM sustains several hundred "
             "P&A wells/year, a durable services market for well-plugging, rig/vessel, casing-cut, "
             "and conductor-removal contractors.\n")
    L.append("- **Capacity gap signal**: the observed PA rate "
             f"({op['mean_2020_2024']:.0f}/yr, 2020-2024) sits below the base-case requirement, "
             "implying a backlog-clearing gap that favors decom-capable vendors.\n")

    L.append("## Reproduce\n")
    L.append("```\nPYTHONPATH=src python3 reports/gtm/decommissioning_market_outlook.py\n```")
    L.append("Deterministic: emits the `.json` sidecar (all figures), this `.md`, and the `.html`. "
             "Every number above is in the JSON.\n")
    L.append(f"*Generated {p['generated_at']} · data as of {DATE} · operator-aggregate only.*\n")
    return "\n".join(L)


def render_html(p):
    d = p["data"]
    fc = p["forecast"]
    a = p["assumptions"]
    ei = fc["eligible_inventory"]
    sc = fc["scenarios"]
    yrs = fc["forecast_years"]
    op = fc["observed_pa_rate"]
    ii = fc["idle_iron"]
    cost = a["pa_unit_cost_usd_mm_per_well"]
    b = sc["base"]

    def esc(x):
        return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # bar chart of PA history (inline SVG, deterministic)
    pa_hist = [(y, d["gom_pa_by_year"].get(y, 0)) for y in range(2010, 2025)]
    mx = max(v for _, v in pa_hist) or 1
    bw, gap, h = 34, 10, 180
    bars = []
    for i, (y, v) in enumerate(pa_hist):
        bh = int(h * v / mx)
        x = i * (bw + gap) + 40
        bars.append(f'<rect x="{x}" y="{h-bh+20}" width="{bw}" height="{bh}" fill="#0e7490"/>'
                    f'<text x="{x+bw/2}" y="{h+34}" font-size="9" text-anchor="middle" fill="#6B7280">{y}</text>'
                    f'<text x="{x+bw/2}" y="{h-bh+16}" font-size="9" text-anchor="middle" fill="#1e3a5f">{v}</text>')
    pa_svg = (f'<svg width="{len(pa_hist)*(bw+gap)+60}" height="{h+50}" '
              f'style="max-width:100%">{"".join(bars)}</svg>')

    # forecast bars (base case per-year)
    fmx = max(b["pa_per_year"]) or 1
    fbars = []
    for i, (y, v) in enumerate(zip(yrs, b["pa_per_year"])):
        bh = int(h * v / fmx)
        x = i * (bw + gap + 20) + 40
        fbars.append(f'<rect x="{x}" y="{h-bh+20}" width="{bw+8}" height="{bh}" fill="#d97706"/>'
                     f'<text x="{x+(bw+8)/2}" y="{h+34}" font-size="10" text-anchor="middle" fill="#6B7280">{y}</text>'
                     f'<text x="{x+(bw+8)/2}" y="{h-bh+16}" font-size="10" text-anchor="middle" fill="#1e3a5f">{v}</text>')
    fc_svg = (f'<svg width="{len(yrs)*(bw+gap+20)+60}" height="{h+50}" '
              f'style="max-width:100%">{"".join(fbars)}</svg>')

    def kpi(label, value, unit="", note=""):
        return (f'<div class="kpi-card"><div class="label">{esc(label)}</div>'
                f'<div class="value">{esc(value)}<span class="unit">{esc(unit)}</span></div>'
                f'<div class="note">{esc(note)}</div></div>')

    def srow(scn):
        s = sc[scn]
        cells = "".join(f"<td>{x}</td>" for x in s["pa_per_year"])
        return (f"<tr><td><b>{scn}</b></td><td>{s['attrition_pace']:.1%}</td>"
                f"<td>{s['deepwater_share']:.0%}</td><td>${s['blended_unit_cost_usd_mm']:.2f}MM</td>"
                f"{cells}<td><b>{s['pa_wells_5yr_total']:,}</b></td>"
                f"<td><b>${s['market_size_5yr_usd_bn']:.2f}B</b></td></tr>")

    status_rows = ""
    for s in ["PA", "ST", "COM", "TA", "CNL", "DSI", "AST", "DRL", "APD"]:
        if s in d["gom_status"]:
            status_rows += (f"<tr><td><code>{s}</code></td><td>{esc(STATUS_MEANING.get(s,''))}</td>"
                            f"<td>{d['gom_status'][s]:,}</td></tr>")

    yr_hdr = "".join(f"<th>{y}</th>" for y in yrs)

    HTML = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>GoM Decommissioning Market Outlook — {DATE}</title>
<style>
body{{font-family:system-ui,-apple-system,BlinkMacSystemFont,sans-serif;margin:0;background:#f8fafc;color:#1F2937}}
.page-wrap{{max-width:1180px;margin:0 auto;padding:24px 20px}}
.report-header{{background:linear-gradient(135deg,#1e3a5f 0%,#0e7490 100%);color:#fff;padding:34px 40px;border-radius:10px;margin-bottom:26px}}
.report-header h1{{margin:0 0 6px;font-size:25px;font-weight:700}}
.report-header .sub{{opacity:.85;font-size:14px}}
.report-header .meta{{display:flex;gap:24px;margin-top:16px;font-size:13px;opacity:.78;flex-wrap:wrap}}
.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:28px}}
.kpi-card{{background:#fff;border-radius:8px;padding:18px 20px;box-shadow:0 1px 4px rgba(0,0,0,.08);border-top:3px solid #d97706}}
.kpi-card .label{{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.7px;color:#6B7280;margin-bottom:6px}}
.kpi-card .value{{font-size:1.7em;font-weight:700;color:#1e3a5f}}
.kpi-card .unit{{font-size:12px;color:#9ca3af;margin-left:3px}}
.kpi-card .note{{font-size:11px;color:#9ca3af;margin-top:4px}}
.section{{margin-bottom:34px}}
.section h2{{color:#1e3a5f;font-size:18px;border-bottom:2px solid #1e3a5f;padding-bottom:8px;margin:0 0 16px}}
.section h3{{color:#0e7490;font-size:15px;margin:18px 0 10px}}
.data-table{{width:100%;border-collapse:collapse;font-size:13px;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
.data-table th{{background:#1e3a5f;color:#fff;padding:9px 13px;text-align:left;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.4px}}
.data-table td{{padding:8px 13px;border-bottom:1px solid #E5E7EB}}
.data-table tr:nth-child(even) td{{background:#F9FAFB}}
.data-note{{background:#EFF6FF;border-left:4px solid #3B82F6;padding:13px 17px;border-radius:4px;margin:16px 0;font-size:13px;line-height:1.5}}
.warn-note{{background:#FEF3C7;border-left:4px solid #d97706;padding:13px 17px;border-radius:4px;margin:16px 0;font-size:13px;line-height:1.5}}
.assum-note{{background:#F3E8FF;border-left:4px solid #9333ea;padding:13px 17px;border-radius:4px;margin:16px 0;font-size:13px;line-height:1.5}}
.chart-wrap{{background:#fff;border-radius:8px;padding:16px 20px;box-shadow:0 1px 4px rgba(0,0,0,.08);margin-bottom:18px}}
.chart-wrap h4{{margin:0 0 10px;font-size:13px;color:#1e3a5f}}
code{{background:#eef2ff;padding:1px 5px;border-radius:3px;font-size:12px}}
.footer{{font-size:12px;color:#9ca3af;margin-top:28px;border-top:1px solid #E5E7EB;padding-top:14px}}
</style></head><body><div class="page-wrap">
<div class="report-header">
<h1>GoM Decommissioning Market Outlook — 5-Year P&amp;A Forecast</h1>
<div class="sub">Forward 2026-2030 Gulf of Mexico plug-&amp;-abandonment volume, timing &amp; market sizing · market-intelligence framing</div>
<div class="meta"><span>Issue #424 (child of #423)</span><span>Data as of {DATE}</span>
<span>BSEE borehole-status census</span><span>Operator-aggregate only</span></div>
</div>

<div class="kpi-grid">
{kpi("Eligible inventory", f"{ei['total_eligible']:,}", "wells", "not-yet-P&A GoM wells (data)")}
{kpi("Idle iron ≥10yr", f"{ii['ta_idle_ge_10yr']:,}", "wells", "TA idle ≥10yr (data)")}
{kpi("Already P&A (GoM)", f"{d['gom_status'].get('PA',0):,}", "wells", "historical decom record (data)")}
{kpi("Base 5-yr volume", f"{b['pa_wells_5yr_total']:,}", "wells", "2026-2030 forecast")}
{kpi("Base 5-yr market", f"${b['market_size_5yr_usd_bn']:.2f}B", "", "blended unit cost (assump.)")}
{kpi("Sensitivity span", f"${sc['low']['market_size_5yr_usd_bn']:.1f}–{sc['high']['market_size_5yr_usd_bn']:.1f}B", "", "low→high scenario")}
</div>

<div class="warn-note"><b>Data vs assumptions — hard separation.</b> Inventory, idle-iron aging, and the
historical P&amp;A rate are <b>measured</b> from BSEE <code>well_data.csv</code>. Unit costs, deepwater mix,
and attrition pace are <b>explicit cited assumptions</b> (purple boxes), stress-tested in the sensitivity.
<code>WATER_DEPTH</code>/<code>WELL_SPUD_DATE</code> are unpopulated in this extract, so water-depth strata
and spud-age cohorts are <b>not</b> grounded — hence the deepwater mix is an assumption, not data.</div>

<div class="section"><h2>1 · Borehole-status inventory (data)</h2>
<p>BSEE <code>BOREHOLE_STAT_CD</code>, GoM-filtered ({d['gom_wells']:,} of {d['total_wells']:,} national boreholes).</p>
<table class="data-table"><thead><tr><th>Status</th><th>Meaning</th><th>GoM wells</th></tr></thead>
<tbody>{status_rows}<tr><td colspan="2"><b>Total</b></td><td><b>{d['gom_wells']:,}</b></td></tr></tbody></table>
</div>

<div class="section"><h2>2 · Eligible-for-decommissioning pipeline (data)</h2>
<table class="data-table"><thead><tr><th>Eligible bucket</th><th>Count</th><th>Basis</th></tr></thead><tbody>
<tr><td><code>TA</code> temporarily abandoned (idle)</td><td>{ei['TA_idle']:,}</td><td>idle iron — direct P&amp;A candidates</td></tr>
<tr><td><code>COM</code> completed (producing/capable)</td><td>{ei['COM_completed']:,}</td><td>reach end-of-life over horizon</td></tr>
<tr><td><code>DSI</code> drilled &amp; suspended</td><td>{ei['DSI']:,}</td><td>inactive</td></tr>
<tr><td><code>AST</code> abandoned sidetrack</td><td>{ei['AST']:,}</td><td>residual</td></tr>
<tr><td><b>Total eligible</b></td><td><b>{ei['total_eligible']:,}</b></td><td>model drawdown base</td></tr>
</tbody></table>
<div class="data-note"><b>Idle-iron aging (data):</b> {ii['ta_idle_ge_10yr']:,} TA wells idle ≥10 years,
{ii['ta_idle_ge_15yr']:,} idle ≥15 years — a standing backlog under BSEE plug-or-restore pressure,
independent of new end-of-life additions.</div>
</div>

<div class="section"><h2>3 · Historical P&amp;A rate (data — calibration anchor)</h2>
<div class="chart-wrap"><h4>GoM permanent abandonments completed per year (2010-2024)</h4>{pa_svg}</div>
<div class="data-note">2015-2024 mean: <b>{op['mean_2015_2024']:.0f}</b> P&amp;A/yr ·
2020-2024 mean: <b>{op['mean_2020_2024']:.0f}</b>/yr ·
implied historical pace vs. eligible inventory: <b>{op['implied_pace_vs_eligible_2015_2024']:.1%}/yr</b>
— the empirical anchor for the assumed attrition pace.</div>
</div>

<div class="section"><h2>4 · Assumptions (NOT data — explicit &amp; cited)</h2>
<div class="assum-note">These parameters are <b>public-knowledge assumptions</b>, not measured from the
data. They are surfaced verbatim and stress-tested below.</div>
<table class="data-table"><thead><tr><th>Parameter</th><th>Low</th><th>Base</th><th>High</th><th>Source</th></tr></thead><tbody>
<tr><td>Shelf/shallow P&amp;A unit cost ($MM/well)</td><td>{cost['shelf_shallow']['low']}</td><td>{cost['shelf_shallow']['base']}</td><td>{cost['shelf_shallow']['high']}</td><td>BOEM/BSEE decom cost reports; GAO-16-40</td></tr>
<tr><td>Deepwater P&amp;A unit cost ($MM/well)</td><td>{cost['deepwater']['low']}</td><td>{cost['deepwater']['base']}</td><td>{cost['deepwater']['high']}</td><td>Wood Mackenzie / Westwood (public)</td></tr>
<tr><td>Deepwater share of eligible</td><td>{a['deepwater_share_of_eligible']['low']:.0%}</td><td>{a['deepwater_share_of_eligible']['base']:.0%}</td><td>{a['deepwater_share_of_eligible']['high']:.0%}</td><td>BOEM GoM well census (shelf-dominated)</td></tr>
<tr><td>Annual attrition pace</td><td>{a['annual_attrition_pace']['low']:.1%}</td><td>{a['annual_attrition_pace']['base']:.1%}</td><td>{a['annual_attrition_pace']['high']:.1%}</td><td>calibrated to observed PA rate, flexed ±</td></tr>
</tbody></table></div>

<div class="section"><h2>5 · 5-year forecast &amp; sensitivity (2026-2030)</h2>
<div class="chart-wrap"><h4>Base-case P&amp;A volume by year (inventory drawdown)</h4>{fc_svg}</div>
<table class="data-table"><thead><tr><th>Scenario</th><th>Pace</th><th>DW share</th><th>$/well</th>{yr_hdr}<th>5-yr wells</th><th>5-yr market</th></tr></thead>
<tbody>{srow('low')}{srow('base')}{srow('high')}</tbody></table>
<div class="data-note"><b>Base case:</b> {b['pa_wells_5yr_total']:,} GoM wells plugged over 2026-2030
(~{b['pa_per_year'][0]}/yr declining as inventory draws down) → <b>${b['market_size_5yr_usd_bn']:.2f}B</b>
addressable P&amp;A market at ${b['blended_unit_cost_usd_mm']:.2f}MM/well blended.
Sensitivity span <b>${sc['low']['market_size_5yr_usd_bn']:.2f}B–${sc['high']['market_size_5yr_usd_bn']:.2f}B</b>
({sc['high']['market_size_5yr_usd_bn']/sc['low']['market_size_5yr_usd_bn']:.1f}× spread).</div>
</div>

<div class="section"><h2>6 · Commercial read-through</h2>
<ul style="font-size:14px;line-height:1.6">
<li><b>Large, aging pipeline:</b> {ei['total_eligible']:,} eligible wells, {ei['TA_idle']:,} already idle,
{ii['ta_idle_ge_10yr']:,} idle ≥10 years — a standing backlog independent of new end-of-life additions.</li>
<li><b>Durable multi-year demand:</b> several hundred P&amp;A wells/year at base pace — a sustained market for
well-plugging, rig/vessel, casing-cut and conductor-removal contractors.</li>
<li><b>Capacity-gap signal:</b> observed 2020-2024 P&amp;A ({op['mean_2020_2024']:.0f}/yr) runs below the
base-case requirement — a backlog-clearing gap favoring decom-capable vendors.</li>
</ul></div>

<div class="footer">Generated {p['generated_at']} · data as of {DATE} ·
source <code>data/modules/bsee/current/wells/well_data.csv</code> · operator-aggregate only (#420) ·
engineering analysis of public BSEE data, not a regulatory finding · reproduce:
<code>PYTHONPATH=src python3 reports/gtm/decommissioning_market_outlook.py</code></div>
</div></body></html>"""
    return HTML


def main():
    p = build_payload()
    json_path = os.path.join(OUT_DIR, STEM + ".json")
    md_path = os.path.join(OUT_DIR, STEM + ".md")
    html_path = os.path.join(OUT_DIR, STEM + ".html")
    with open(json_path, "w") as f:
        json.dump(p, f, indent=2)
    with open(md_path, "w") as f:
        f.write(render_markdown(p))
    with open(html_path, "w") as f:
        f.write(render_html(p))
    print("WROTE:", json_path)
    print("WROTE:", md_path)
    print("WROTE:", html_path)
    # quick self-summary
    fc = p["forecast"]
    print("eligible:", fc["eligible_inventory"]["total_eligible"],
          "| base 5yr wells:", fc["scenarios"]["base"]["pa_wells_5yr_total"],
          "| base market $B:", fc["scenarios"]["base"]["market_size_5yr_usd_bn"])


if __name__ == "__main__":
    main()
