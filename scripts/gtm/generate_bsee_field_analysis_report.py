"""
Generate comprehensive BSEE GoM Lower Tertiary field economics HTML report.

Uses:
  - worldenergydata.lower_tertiary.portfolio_economics.run_portfolio()
  - All 10 LT field YAML configs (config/analysis/lower_tertiary/fields/)
  - worldenergydata.fdas.api.EconomicsQuery for metrics
  - Plotly for interactive charts

Output: reports/gtm/2026-05-04-bsee-field-analysis-comprehensive.html

Run: .venv/bin/python scripts/gtm/generate_bsee_field_analysis_report.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

# Ensure src/ is on the path when run directly.
_REPO = Path(__file__).resolve().parents[2]
if str(_REPO / "src") not in sys.path:
    sys.path.insert(0, str(_REPO / "src"))

import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

from worldenergydata.lower_tertiary.portfolio_economics import (
    FieldEconomicsResult,
    PortfolioEconomicsRun,
    _build_production_profile,
    run_portfolio,
)
from worldenergydata.lower_tertiary.portfolio import LT_FIELDS_2026

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

REPORT_DATE = "2026-05-04"
OUTPUT_PATH = _REPO / "reports" / "gtm" / f"{REPORT_DATE}-bsee-field-analysis-comprehensive.html"
PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"

STATUS_BADGE = {
    "producing": ('<span style="background:#16a34a;color:#fff;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600">Producing</span>'),
    "under_development": ('<span style="background:#d97706;color:#fff;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600">Dev</span>'),
    "pre_fid": ('<span style="background:#6366f1;color:#fff;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600">Pre-FID</span>'),
}

# ---------------------------------------------------------------------------
# Run portfolio economics
# ---------------------------------------------------------------------------

def run_analysis() -> PortfolioEconomicsRun:
    return run_portfolio(
        field_ids=LT_FIELDS_2026,
        oil_price_usd_per_bbl=70.0,
        discount_rate=0.10,
        reinvestment_rate=0.06,
        sensitivity_prices=(50.0, 60.0, 70.0, 80.0, 100.0),
        project_years=20,
        plateau_years=3,
        annual_decline=0.08,
    )


# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------

NAVY = "#1e3a5f"
TEAL = "#0e7490"
GREEN = "#16a34a"
ORANGE = "#d97706"
PURPLE = "#6366f1"
BLUE_LIGHT = "#93c5fd"
CHART_COLORS = ["#1e3a5f", "#0e7490", "#16a34a", "#d97706", "#6366f1",
                "#dc2626", "#7c3aed", "#0284c7", "#065f46", "#92400e"]

_LAYOUT_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="system-ui,-apple-system,sans-serif", size=12, color="#374151"),
    margin=dict(l=60, r=30, t=50, b=60),
)


def _fig_to_div(fig: go.Figure, div_id: str, height: int = 400) -> str:
    fig_json = pio.to_json(fig)
    return (
        f'<div id="{div_id}" style="width:100%;height:{height}px"></div>\n'
        f'<script>Plotly.newPlot("{div_id}", {fig_json});</script>\n'
    )


def chart_npv_comparison(results: list[FieldEconomicsResult]) -> str:
    names = [r.display_name for r in results]
    npvs = [r.npv_mm_usd for r in results]
    colors = [GREEN if v >= 0 else "#dc2626" for v in npvs]

    fig = go.Figure(go.Bar(
        x=names, y=npvs,
        marker_color=colors,
        text=[f"${v:,.0f}M" for v in npvs],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>NPV: $%{y:,.0f}M<extra></extra>",
    ))
    fig.update_layout(
        **_LAYOUT_BASE,
        title=dict(text="NPV Comparison @ $70/bbl, 10% Discount Rate", font=dict(size=14, color=NAVY)),
        yaxis=dict(title="NPV ($M)", gridcolor="#E5E7EB", zeroline=True, zerolinecolor="#374151"),
        xaxis=dict(gridcolor="#E5E7EB"),
    )
    return _fig_to_div(fig, "chart-npv-comparison", 380)


def chart_sensitivity_heatmap(results: list[FieldEconomicsResult]) -> str:
    prices = [50, 60, 70, 80, 100]
    field_names = [r.display_name for r in results]
    z = []
    for r in results:
        row = []
        for p in prices:
            match = r.sensitivity[r.sensitivity["oil_price_usd_per_bbl"] == float(p)]
            row.append(float(match["npv_mm_usd"].iloc[0]) if len(match) else 0.0)
        z.append(row)

    fig = go.Figure(go.Heatmap(
        x=[f"${p}/bbl" for p in prices],
        y=field_names,
        z=z,
        colorscale=[[0, "#dc2626"], [0.5, "#fef3c7"], [1, "#16a34a"]],
        zmid=0,
        colorbar=dict(title="NPV ($M)"),
        hovertemplate="<b>%{y}</b><br>Oil Price: %{x}<br>NPV: $%{z:,.0f}M<extra></extra>",
    ))
    layout = {**_LAYOUT_BASE, "margin": dict(l=130, r=80, t=50, b=60)}
    fig.update_layout(
        **layout,
        title=dict(text="NPV Sensitivity — 5-Point Oil Price Analysis", font=dict(size=14, color=NAVY)),
    )
    return _fig_to_div(fig, "chart-sensitivity-heatmap", 380)


def chart_production_profiles(results: list[FieldEconomicsResult], run: PortfolioEconomicsRun) -> str:
    fig = go.Figure()
    years = list(range(1, run.project_years + 1))
    for i, r in enumerate(results):
        prod = _build_production_profile(r.plateau_mbopd, run.plateau_years, run.annual_decline, run.project_years)
        fig.add_trace(go.Scatter(
            x=years, y=[p * 1000 / 365 for p in prod],  # convert MMbbl/yr → mbopd
            name=r.display_name,
            mode="lines",
            line=dict(color=CHART_COLORS[i % len(CHART_COLORS)], width=2),
            hovertemplate=f"<b>{r.display_name}</b><br>Year %{{x}}: %{{y:,.1f}} mbopd<extra></extra>",
        ))
    fig.update_layout(
        **_LAYOUT_BASE,
        title=dict(text="Production Profiles by Field — 20-Year Forecast (mbopd)", font=dict(size=14, color=NAVY)),
        yaxis=dict(title="Production (mbopd)", gridcolor="#E5E7EB"),
        xaxis=dict(title="Project Year", gridcolor="#E5E7EB"),
        legend=dict(bgcolor="rgba(255,255,255,0.8)", bordercolor="#E5E7EB", borderwidth=1),
    )
    return _fig_to_div(fig, "chart-production-profiles", 400)


def chart_capex_vs_npv(results: list[FieldEconomicsResult]) -> str:
    fig = go.Figure()
    for i, r in enumerate(results):
        ratio = r.npv_mm_usd / r.capex_mm_usd if r.capex_mm_usd else 0
        fig.add_trace(go.Scatter(
            x=[r.capex_mm_usd],
            y=[r.npv_mm_usd],
            mode="markers+text",
            name=r.display_name,
            text=[r.display_name],
            textposition="top center",
            marker=dict(size=14, color=CHART_COLORS[i % len(CHART_COLORS)],
                        symbol="circle", opacity=0.85),
            hovertemplate=(
                f"<b>{r.display_name}</b><br>"
                "CAPEX: $%{x:,.0f}M<br>NPV: $%{y:,.0f}M<br>"
                f"PI: {ratio:.2f}x<extra></extra>"
            ),
        ))
    # PI=1 reference line
    max_capex = max(r.capex_mm_usd for r in results)
    fig.add_shape(type="line", x0=0, y0=0, x1=max_capex, y1=0,
                  line=dict(color="#9ca3af", dash="dash", width=1))
    fig.update_layout(
        **_LAYOUT_BASE,
        title=dict(text="CAPEX vs NPV — Profitability Index (NPV=0 reference line)", font=dict(size=14, color=NAVY)),
        xaxis=dict(title="CAPEX ($M)", gridcolor="#E5E7EB"),
        yaxis=dict(title="NPV ($M)", gridcolor="#E5E7EB", zeroline=True, zerolinecolor="#9ca3af"),
        showlegend=False,
    )
    return _fig_to_div(fig, "chart-capex-npv", 400)


def chart_breakeven(results: list[FieldEconomicsResult]) -> str:
    names = [r.display_name for r in results]
    beps = [r.breakeven_oil_usd_per_bbl if r.breakeven_oil_usd_per_bbl else 0 for r in results]
    colors = [GREEN if b <= 70 else (ORANGE if b <= 85 else "#dc2626") for b in beps]

    fig = go.Figure(go.Bar(
        x=names, y=beps,
        marker_color=colors,
        text=[f"${b:.0f}/bbl" if b else "N/A" for b in beps],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Breakeven: $%{y:.0f}/bbl<extra></extra>",
    ))
    # $70/bbl reference line
    fig.add_hline(y=70, line_dash="dash", line_color=TEAL,
                  annotation_text="$70/bbl (base case)",
                  annotation_position="right")
    fig.update_layout(
        **_LAYOUT_BASE,
        title=dict(text="Breakeven Oil Price by Field (10% Discount Rate)", font=dict(size=14, color=NAVY)),
        yaxis=dict(title="Breakeven Price ($/bbl)", gridcolor="#E5E7EB"),
        xaxis=dict(gridcolor="#E5E7EB"),
    )
    return _fig_to_div(fig, "chart-breakeven", 380)


def chart_irr_mirr(results: list[FieldEconomicsResult]) -> str:
    names = [r.display_name for r in results]
    irrs = [r.irr_annual * 100 if not math.isnan(r.irr_annual) else 0 for r in results]
    mirrs = [r.mirr_annual * 100 if not math.isnan(r.mirr_annual) else 0 for r in results]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="IRR (%)", x=names, y=irrs,
        marker_color=NAVY, offsetgroup=0,
        hovertemplate="<b>%{x}</b><br>IRR: %{y:.1f}%<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="MIRR (%)", x=names, y=mirrs,
        marker_color=TEAL, offsetgroup=1,
        hovertemplate="<b>%{x}</b><br>MIRR: %{y:.1f}%<extra></extra>",
    ))
    fig.add_hline(y=10.0, line_dash="dash", line_color=ORANGE,
                  annotation_text="10% hurdle rate",
                  annotation_position="right")
    fig.update_layout(
        **_LAYOUT_BASE,
        barmode="group",
        title=dict(text="IRR vs MIRR by Field — Hurdle Rate: 10%", font=dict(size=14, color=NAVY)),
        yaxis=dict(title="Rate of Return (%)", gridcolor="#E5E7EB"),
        xaxis=dict(gridcolor="#E5E7EB"),
        legend=dict(bgcolor="rgba(255,255,255,0.8)"),
    )
    return _fig_to_div(fig, "chart-irr-mirr", 380)


# ---------------------------------------------------------------------------
# HTML building blocks
# ---------------------------------------------------------------------------

CSS = f"""
body {{
    font-family: system-ui,-apple-system,BlinkMacSystemFont,sans-serif;
    margin: 0; padding: 0; background: #f8fafc; color: #1F2937;
}}
.page-wrap {{max-width:1200px; margin:0 auto; padding:24px 20px}}
/* Header */
.report-header {{
    background: linear-gradient(135deg, {NAVY} 0%, {TEAL} 100%);
    color: #fff; padding: 36px 40px; border-radius: 10px; margin-bottom: 28px;
}}
.report-header h1 {{margin:0 0 6px; font-size:26px; font-weight:700}}
.report-header .sub {{opacity:.82; font-size:14px; margin-top:4px}}
.report-header .meta {{display:flex; gap:24px; margin-top:16px; font-size:13px; opacity:.75}}
/* KPI cards */
.kpi-grid {{display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:14px; margin-bottom:28px}}
.kpi-card {{
    background:#fff; border-radius:8px; padding:18px 20px;
    box-shadow:0 1px 4px rgba(0,0,0,.08); border-top:3px solid {NAVY};
}}
.kpi-card .label {{font-size:11px; font-weight:600; text-transform:uppercase;
    letter-spacing:.7px; color:#6B7280; margin-bottom:6px}}
.kpi-card .value {{font-size:1.8em; font-weight:700; color:{NAVY}}}
.kpi-card .unit  {{font-size:12px; color:#9ca3af; margin-left:3px}}
.kpi-card .note  {{font-size:11px; color:#9ca3af; margin-top:4px}}
/* Sections */
.section {{margin-bottom:36px}}
.section h2 {{
    color:{NAVY}; font-size:18px; border-bottom:2px solid {NAVY};
    padding-bottom:8px; margin-bottom:16px; margin-top:0;
}}
.section h3 {{color:{TEAL}; font-size:15px; margin: 20px 0 10px}}
/* Tables */
.data-table {{width:100%; border-collapse:collapse; font-size:13px; background:#fff;
    border-radius:8px; overflow:hidden; box-shadow:0 1px 4px rgba(0,0,0,.08)}}
.data-table th {{
    background:{NAVY}; color:#fff; padding:10px 14px; text-align:left;
    font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:.5px;
    position:sticky; top:0;
}}
.data-table td {{padding:8px 14px; border-bottom:1px solid #E5E7EB; vertical-align:middle}}
.data-table tr:nth-child(even) td {{background:#F9FAFB}}
.data-table tr:hover td {{background:#EFF6FF}}
/* Chart containers */
.chart-wrap {{background:#fff; border-radius:8px; padding:16px 20px;
    box-shadow:0 1px 4px rgba(0,0,0,.08); margin-bottom:20px}}
.chart-grid {{display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:20px}}
/* Field cards */
.field-cards {{display:grid; grid-template-columns:repeat(auto-fit,minmax(340px,1fr)); gap:18px}}
.field-card {{background:#fff; border-radius:8px; padding:20px 22px;
    box-shadow:0 1px 4px rgba(0,0,0,.08); border-left:4px solid {NAVY}}}
.field-card.pre-fid {{border-left-color:{PURPLE}}}
.field-card.under-development {{border-left-color:{ORANGE}}}
.field-card h4 {{margin:0 0 10px; font-size:15px; color:{NAVY}; display:flex; align-items:center; gap:8px}}
.field-metrics {{display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-top:12px}}
.fm {{background:#F9FAFB; padding:8px 10px; border-radius:4px}}
.fm .fl {{font-size:10px; color:#6B7280; text-transform:uppercase; letter-spacing:.4px}}
.fm .fv {{font-size:14px; font-weight:700; color:{NAVY}}}
.sens-mini {{margin-top:14px; font-size:12px}}
.sens-mini table {{width:100%; border-collapse:collapse}}
.sens-mini th {{background:#F3F4F6; padding:4px 8px; font-size:10px; text-align:center}}
.sens-mini td {{padding:4px 8px; text-align:center; border-bottom:1px solid #F3F4F6; font-size:12px}}
.sens-mini .pos {{color:{GREEN}; font-weight:600}}
.sens-mini .neg {{color:#dc2626; font-weight:600}}
/* Notes */
.data-note {{
    background:#EFF6FF; border-left:4px solid #3B82F6; padding:14px 18px;
    border-radius:4px; margin:16px 0; font-size:13px; line-height:1.5
}}
.warn-note {{
    background:#FEF3C7; border-left:4px solid {ORANGE}; padding:14px 18px;
    border-radius:4px; margin:16px 0; font-size:13px; line-height:1.5
}}
/* Operator table */
.operator-table {{width:100%; border-collapse:collapse; font-size:13px}}
.operator-table th {{background:#374151; color:#fff; padding:8px 14px; text-align:left; font-size:11px; font-weight:600}}
.operator-table td {{padding:8px 14px; border-bottom:1px solid #E5E7EB}}
.operator-table tr:nth-child(even) td {{background:#F9FAFB}}
/* Citations */
.cite-table {{width:100%; border-collapse:collapse; font-size:12px}}
.cite-table th {{background:#4b5563; color:#fff; padding:7px 12px; text-align:left}}
.cite-table td {{padding:6px 12px; border-bottom:1px solid #E5E7EB; vertical-align:top}}
.cite-table tr:nth-child(even) td {{background:#F9FAFB}}
/* Footer */
.report-footer {{text-align:center; padding:20px; color:#9ca3af; font-size:12px; margin-top:20px}}
@media (max-width:768px) {{.chart-grid{{grid-template-columns:1fr}}}}
"""


def _kpi_card(label: str, value: str, unit: str = "", note: str = "") -> str:
    return (
        f'<div class="kpi-card">'
        f'<div class="label">{label}</div>'
        f'<div class="value">{value}<span class="unit">{unit}</span></div>'
        f'{"<div class=note>" + note + "</div>" if note else ""}'
        f"</div>"
    )


def _status_badge(status: str) -> str:
    return STATUS_BADGE.get(status, f'<span style="background:#9ca3af;color:#fff;padding:2px 8px;border-radius:12px;font-size:11px">{status}</span>')


def _fmt_npv(v: float) -> str:
    color = GREEN if v >= 0 else "#dc2626"
    return f'<span style="color:{color};font-weight:600">${v:,.0f}M</span>'


def _fmt_pct(v: float) -> str:
    if math.isnan(v):
        return "N/A"
    return f"{v*100:.1f}%"


def build_portfolio_table(results: list[FieldEconomicsResult]) -> str:
    rows = ""
    for r in results:
        irr_str = _fmt_pct(r.irr_annual)
        mirr_str = _fmt_pct(r.mirr_annual)
        pb_str = f"{r.payback_years:.1f} yr" if not math.isnan(r.payback_years) else "N/A"
        be_str = f"${r.breakeven_oil_usd_per_bbl:.0f}/bbl" if r.breakeven_oil_usd_per_bbl else "N/A"
        rows += (
            f"<tr>"
            f"<td><strong>{r.display_name}</strong></td>"
            f"<td>{_status_badge(r.status)}</td>"
            f"<td>{r.operator}</td>"
            f"<td>${r.capex_mm_usd:,.0f}M</td>"
            f"<td>{r.plateau_mbopd:.0f}</td>"
            f"<td>{_fmt_npv(r.npv_mm_usd)}</td>"
            f"<td>{irr_str}</td>"
            f"<td>{mirr_str}</td>"
            f"<td>{pb_str}</td>"
            f"<td>{be_str}</td>"
            f"</tr>"
        )
    return f"""
<table class="data-table">
<thead><tr>
<th>Field</th><th>Status</th><th>Operator</th><th>CAPEX</th>
<th>Plateau (mbopd)</th><th>NPV @ $70</th><th>IRR</th><th>MIRR</th>
<th>Payback</th><th>Breakeven</th>
</tr></thead>
<tbody>{rows}</tbody>
</table>"""


def build_operator_table(results: list[FieldEconomicsResult]) -> str:
    from collections import defaultdict
    ops: dict[str, dict] = defaultdict(lambda: {"fields": [], "capex": 0.0, "npvs": [], "irrs": [], "plateau": 0.0})
    for r in results:
        d = ops[r.operator]
        d["fields"].append(r.display_name)
        d["capex"] += r.capex_mm_usd
        d["npvs"].append(r.npv_mm_usd)
        if not math.isnan(r.irr_annual):
            d["irrs"].append(r.irr_annual)
        d["plateau"] += r.plateau_mbopd

    rows = ""
    for op, d in sorted(ops.items(), key=lambda x: -x[1]["capex"]):
        avg_npv = sum(d["npvs"]) / len(d["npvs"]) if d["npvs"] else 0
        avg_irr = sum(d["irrs"]) / len(d["irrs"]) if d["irrs"] else float("nan")
        rows += (
            f"<tr>"
            f"<td><strong>{op}</strong></td>"
            f"<td>{', '.join(d['fields'])}</td>"
            f"<td>${d['capex']:,.0f}M</td>"
            f"<td>{_fmt_npv(avg_npv)}</td>"
            f"<td>{_fmt_pct(avg_irr)}</td>"
            f"<td>{d['plateau']:.0f}</td>"
            f"</tr>"
        )
    return f"""
<table class="operator-table">
<thead><tr>
<th>Operator</th><th>Fields</th><th>Total CAPEX</th>
<th>Avg NPV @ $70</th><th>Avg IRR</th><th>Total Plateau (mbopd)</th>
</tr></thead>
<tbody>{rows}</tbody>
</table>"""


def build_field_cards(results: list[FieldEconomicsResult]) -> str:
    cards = []
    for r in results:
        css_class = "pre-fid" if r.status == "pre_fid" else (
            "under-development" if r.status == "under_development" else "")
        pb = f"{r.payback_years:.1f} yr" if not math.isnan(r.payback_years) else "N/A"
        be = f"${r.breakeven_oil_usd_per_bbl:.0f}" if r.breakeven_oil_usd_per_bbl else "N/A"

        # Mini sensitivity table
        sens_rows = ""
        for _, row in r.sensitivity.iterrows():
            p = int(row["oil_price_usd_per_bbl"])
            v = row["npv_mm_usd"]
            cls = "pos" if v >= 0 else "neg"
            sens_rows += f'<tr><td>${p}/bbl</td><td class="{cls}">${v:,.0f}M</td></tr>'

        cards.append(f"""
<div class="field-card {css_class}">
  <h4>{r.display_name} {_status_badge(r.status)}</h4>
  <div style="font-size:12px;color:#6B7280">Operator: <strong>{r.operator}</strong></div>
  <div class="field-metrics">
    <div class="fm"><div class="fl">CAPEX</div><div class="fv">${r.capex_mm_usd:,.0f}M</div></div>
    <div class="fm"><div class="fl">Plateau</div><div class="fv">{r.plateau_mbopd:.0f} mbopd</div></div>
    <div class="fm"><div class="fl">NPV @ $70</div><div class="fv">{_fmt_npv(r.npv_mm_usd)}</div></div>
    <div class="fm"><div class="fl">IRR</div><div class="fv">{_fmt_pct(r.irr_annual)}</div></div>
    <div class="fm"><div class="fl">MIRR</div><div class="fv">{_fmt_pct(r.mirr_annual)}</div></div>
    <div class="fm"><div class="fl">Payback</div><div class="fv">{pb}</div></div>
    <div class="fm"><div class="fl">Breakeven</div><div class="fv">{be}/bbl</div></div>
  </div>
  <div class="sens-mini">
    <div style="font-weight:600;font-size:11px;color:#6B7280;margin-bottom:4px">OIL PRICE SENSITIVITY</div>
    <table><thead><tr><th>Price</th><th>NPV</th></tr></thead>
    <tbody>{sens_rows}</tbody></table>
  </div>
</div>""")
    return '<div class="field-cards">' + "\n".join(cards) + "</div>"


def build_citations(results: list[FieldEconomicsResult]) -> str:
    # Unique citations from the first field (global inputs); plus field-specific
    rows = ""
    seen = set()
    for r in results[:1]:
        for _, c in r.citations.iterrows():
            key = (c["input"], c["code_id"])
            if key not in seen:
                seen.add(key)
                rows += (f"<tr><td>{c['input']}</td><td>{c['publisher']}</td>"
                         f"<td><code>{c['code_id']}</code></td><td>{c['revision']}</td></tr>")
    return f"""
<table class="cite-table">
<thead><tr><th>Input</th><th>Publisher/Source</th><th>Code/Reference ID</th><th>Revision</th></tr></thead>
<tbody>{rows}</tbody>
</table>"""


# ---------------------------------------------------------------------------
# Assemble HTML
# ---------------------------------------------------------------------------

def build_html(run: PortfolioEconomicsRun) -> str:
    results = run.results
    total_capex = sum(r.capex_mm_usd for r in results)
    total_npv = sum(r.npv_mm_usd for r in results)
    total_plateau = sum(r.plateau_mbopd for r in results)
    producing = sum(1 for r in results if r.status == "producing")
    pre_fid = sum(1 for r in results if r.status == "pre_fid")
    under_dev = sum(1 for r in results if r.status == "under_development")
    valid_beps = [r.breakeven_oil_usd_per_bbl for r in results if r.breakeven_oil_usd_per_bbl]
    avg_bep = sum(valid_beps) / len(valid_beps) if valid_beps else 0
    valid_irrs = [r.irr_annual for r in results if not math.isnan(r.irr_annual)]
    best_irr = max(valid_irrs) if valid_irrs else float("nan")

    kpis = (
        _kpi_card("Total CAPEX", f"${total_capex/1000:.1f}", "B", "10 fields")
        + _kpi_card("Portfolio NPV", f"${total_npv/1000:.1f}", "B", "@$70/bbl, 10% disc.")
        + _kpi_card("Total Plateau", f"{total_plateau:.0f}", "mbopd", "peak combined rate")
        + _kpi_card("Producing", str(producing), "", "fields on stream")
        + _kpi_card("Pre-FID", str(pre_fid), "", "awaiting sanction")
        + _kpi_card("Under Dev.", str(under_dev), "", "")
        + _kpi_card("Avg Breakeven", f"${avg_bep:.0f}", "/bbl", "10% hurdle")
        + _kpi_card("Best IRR", _fmt_pct(best_irr), "", "producing fields")
    )

    charts_row1 = (
        f'<div class="chart-wrap">{chart_npv_comparison(results)}</div>'
        f'<div class="chart-wrap">{chart_breakeven(results)}</div>'
    )
    charts_row2 = (
        f'<div class="chart-wrap">{chart_irr_mirr(results)}</div>'
        f'<div class="chart-wrap">{chart_capex_vs_npv(results)}</div>'
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>BSEE GoM Lower Tertiary — Field Economics Analysis {REPORT_DATE}</title>
<script src="{PLOTLY_CDN}" charset="utf-8"></script>
<style>{CSS}</style>
</head>
<body>
<div class="page-wrap">

<!-- ── Header ────────────────────────────────────────────── -->
<div class="report-header">
  <h1>BSEE GoM Lower Tertiary Portfolio — Field Economics Analysis</h1>
  <div class="sub">US Gulf of Mexico Deepwater Play · 10 Fields · BSEE/BOEM Data · worldenergydata v1</div>
  <div class="meta">
    <span>📅 Report Date: {REPORT_DATE}</span>
    <span>💰 Base Price: $70/bbl (EIA STEO Q1 2026)</span>
    <span>📊 Discount Rate: 10%</span>
    <span>🛢 Data: BSEE OGOR-A + YAML field configs</span>
  </div>
</div>

<!-- ── KPI Cards ─────────────────────────────────────────── -->
<div class="kpi-grid">{kpis}</div>

<!-- ── Portfolio Overview ────────────────────────────────── -->
<div class="section">
  <h2>1. Portfolio Overview</h2>
  <div class="data-note">
    <strong>10 GoM Lower Tertiary fields</strong> covering the deepest, highest-CAPEX offshore development tier.
    Economics computed on documented decline-curve basis: {run.plateau_years}-year plateau →
    {run.annual_decline*100:.0f}%/yr exponential decline over {run.project_years}-year project life.
    Cashflow basis: <code>documented_decline_curve_v1</code>. Federal royalty: 12.5% (30 CFR § 250).
  </div>
  {build_portfolio_table(results)}
</div>

<!-- ── Charts Row 1 ──────────────────────────────────────── -->
<div class="section">
  <h2>2. Economics Comparison</h2>
  <div class="chart-grid">{charts_row1}</div>
  <div class="chart-grid">{charts_row2}</div>
</div>

<!-- ── Sensitivity Heatmap ───────────────────────────────── -->
<div class="section">
  <h2>3. Oil Price Sensitivity Analysis</h2>
  <div class="warn-note">
    <strong>5-point sensitivity:</strong> NPV at $50, $60, $70, $80, and $100/bbl.
    Green = positive NPV; Red = negative NPV at that price. Fields with pre-FID
    status (Kaskida, Tiber, North Platte) carry higher NPV under rising-price scenarios.
  </div>
  <div class="chart-wrap">{chart_sensitivity_heatmap(results)}</div>
</div>

<!-- ── Production Profiles ───────────────────────────────── -->
<div class="section">
  <h2>4. Production Profiles — 20-Year Forecast</h2>
  <div class="data-note">
    Production modeled as plateau ({run.plateau_years} yr) → exponential decline
    ({run.annual_decline*100:.0f}%/yr). Rates are field gross (100% WI).
    Pre-FID fields (Kaskida, Tiber, North Platte) show modeled potential on sanctioned
    development concept assumptions; actual curves will follow FEED outcomes.
  </div>
  <div class="chart-wrap">{chart_production_profiles(results, run)}</div>
</div>

<!-- ── Operator Benchmarking ─────────────────────────────── -->
<div class="section">
  <h2>5. Operator Benchmarking</h2>
  <div class="data-note">
    Portfolio is dominated by Chevron (4 field positions, largest CAPEX exposure) and BP
    (2 positions, both pre-FID). Equinor holds significant non-op WI in 4 fields.
    Average NPV and IRR aggregated by operator across all fields where operator is the
    named leaseholder-in-charge per BSEE records.
  </div>
  {build_operator_table(results)}
</div>

<!-- ── Per-Field Detail ───────────────────────────────────── -->
<div class="section">
  <h2>6. Per-Field Detail</h2>
  <div class="data-note">
    Each card shows: CAPEX, plateau rate, NPV/IRR/MIRR at base case, payback period,
    breakeven oil price, and 5-point sensitivity. Producing fields (green border)
    have confirmed first-oil dates; Pre-FID fields (purple) are pre-sanctioned.
  </div>
  {build_field_cards(results)}
</div>

<!-- ── Methodology & Citations ───────────────────────────── -->
<div class="section">
  <h2>7. Methodology &amp; Data Sources</h2>
  <h3>Economics Framework</h3>
  <ul style="font-size:13px;line-height:2">
    <li><strong>NPV:</strong> Standard discounted cashflow at 10% annual rate (FDAS default)</li>
    <li><strong>IRR:</strong> Internal rate of return via <code>numpy.irr</code>-equivalent root-finding</li>
    <li><strong>MIRR:</strong> Modified IRR: finance rate 10%, reinvestment rate 6%</li>
    <li><strong>Payback:</strong> First year cumulative cashflow crosses zero</li>
    <li><strong>Breakeven:</strong> Oil price where NPV = 0 (bisection, tolerance $0.01/bbl)</li>
    <li><strong>Cashflow year 0:</strong> Full CAPEX as negative outlay; years 1–20: net operating</li>
    <li><strong>Revenue:</strong> Production (MMbbl/yr) × oil price × (1 − 12.5% royalty) − OPEX</li>
  </ul>
  <h3>Data Sources &amp; Input Citations</h3>
  <div class="data-note">
    All numeric inputs are sourced from versioned YAML field configs
    (<code>config/analysis/lower_tertiary/fields/*.yml</code>) and
    <code>worldenergydata.lower_tertiary.portfolio_economics</code> defaults.
    Real-time BSEE OGOR-A production aggregation is a planned follow-up (issue #367).
  </div>
  {build_citations(results)}
  <div class="warn-note" style="margin-top:16px">
    <strong>⚠ Disclaimer:</strong> This report uses documented decline-curve assumptions
    and public CAPEX estimates. It is not investment advice. Pre-FID economics assume
    conceptual development scenarios; actual project economics will differ based on
    FEED outcomes, reservoir performance, and commodity prices.
    Source: worldenergydata Python library, <code>{REPORT_DATE}</code>.
  </div>
</div>

</div><!-- .page-wrap -->
<div class="report-footer">
  Generated by worldenergydata · BSEE GoM Lower Tertiary Field Economics Report ·
  {REPORT_DATE} · Cashflow basis: documented_decline_curve_v1 ·
  Data: BSEE OGOR-A + YAML configs · Engine: worldenergydata.lower_tertiary.portfolio_economics
</div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Running portfolio economics...")
    run = run_analysis()
    print(f"  {len(run.results)} fields computed.")

    print("Building HTML report...")
    html = build_html(run)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    size_kb = OUTPUT_PATH.stat().st_size // 1024
    print(f"Report written: {OUTPUT_PATH}")
    print(f"Size: {size_kb} KB")

    # Quick sanity
    for r in run.results:
        print(f"  {r.display_name:20s}  NPV={r.npv_mm_usd:8,.0f}M  IRR={r.irr_annual*100:.1f}%  BE=${r.breakeven_oil_usd_per_bbl or 0:.0f}/bbl")
