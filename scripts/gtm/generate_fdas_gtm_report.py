#!/usr/bin/env python3
"""
ABOUTME: GTM demo report generator for FDAS field development economics.
ABOUTME: Produces a self-contained interactive Plotly HTML report for client delivery.

Run from worldenergydata root:
    /mnt/local-analysis/workspace-hub/worldenergydata/.venv/bin/python \
        scripts/gtm/generate_fdas_gtm_report.py
"""

from __future__ import annotations

import sys
import os
from pathlib import Path

# Ensure src is on path when running directly
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

OUTPUT_PATH = (
    REPO_ROOT / "reports" / "gtm" / "2026-05-04-fdas-field-development-economics.html"
)

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from worldenergydata.fdas.api import EconomicsQuery
from worldenergydata.production.forecast.decline import ArpsDeclineCurve


# ---------------------------------------------------------------------------
# 1. Scenario definitions
# ---------------------------------------------------------------------------

SCENARIOS = [
    {
        "name": "Shallow Water Gas",
        "short": "SW Gas",
        "capex_mm": 150,
        "revenue_mm_yr": 25,
        "life_years": 15,
        "color": "#2196F3",
        "water_depth": "Shelf (<300 m)",
        "development_type": "Fixed Platform",
    },
    {
        "name": "Deepwater Oil",
        "short": "DW Oil",
        "capex_mm": 500,
        "revenue_mm_yr": 60,
        "life_years": 20,
        "color": "#4CAF50",
        "water_depth": "Deepwater (300-1500 m)",
        "development_type": "Semi-submersible TLP",
    },
    {
        "name": "Ultra-Deepwater FPSO",
        "short": "UDW FPSO",
        "capex_mm": 2000,
        "revenue_mm_yr": 220,
        "life_years": 25,
        "color": "#FF9800",
        "water_depth": "Ultra-deepwater (>1500 m)",
        "development_type": "FPSO",
    },
    {
        "name": "Subsea Tieback",
        "short": "Tieback",
        "capex_mm": 80,
        "revenue_mm_yr": 18,
        "life_years": 12,
        "color": "#9C27B0",
        "water_depth": "Deepwater (tie to host)",
        "development_type": "Subsea Tie-back",
    },
]

DISCOUNT_RATES = [0.08, 0.10, 0.12]
FINANCE_RATE = 0.10
REINVEST_RATE = 0.06


def build_annual_cashflows(capex_mm: float, revenue_mm_yr: float, life_years: int) -> list[float]:
    """Build simple annual cashflow list: year 0 is capex, years 1..N are revenue."""
    return [-capex_mm] + [revenue_mm_yr] * life_years


def run_scenario(scenario: dict) -> dict:
    """Calculate all financial metrics for one scenario at each discount rate."""
    econ = EconomicsQuery()
    cfs = build_annual_cashflows(
        scenario["capex_mm"], scenario["revenue_mm_yr"], scenario["life_years"]
    )

    results = {"scenario": scenario["name"], "short": scenario["short"]}
    results["cashflows"] = cfs
    results["color"] = scenario["color"]
    results["capex_mm"] = scenario["capex_mm"]
    results["revenue_mm_yr"] = scenario["revenue_mm_yr"]
    results["life_years"] = scenario["life_years"]
    results["water_depth"] = scenario["water_depth"]
    results["development_type"] = scenario["development_type"]

    # NPV at each discount rate
    for dr in DISCOUNT_RATES:
        npv_val = econ.npv(cfs, dr, period="annual")
        results[f"npv_{int(dr*100)}pct"] = npv_val

    # IRR
    try:
        _, irr_annual = econ.irr(cfs, period="annual")
        results["irr_annual"] = irr_annual
    except Exception:
        results["irr_annual"] = float("nan")

    # MIRR (finance=10%, reinvest=6%)
    try:
        _, mirr_annual = econ.mirr(cfs, FINANCE_RATE, reinvestment_rate=REINVEST_RATE)
        results["mirr_annual"] = mirr_annual
    except Exception:
        results["mirr_annual"] = float("nan")

    # Payback period
    try:
        _, payback_years = econ.payback_period(cfs, period="annual")
        results["payback_years"] = payback_years
    except Exception:
        results["payback_years"] = float("nan")

    return results


def run_decline_curve_demo() -> tuple:
    """Fit Arps hyperbolic decline to a synthetic GoM well and return result + historical df."""
    # Synthetic historical production: qi=5000 bbl/mo, Di=0.08/mo, b=0.6 for 60 months
    np.random.seed(42)
    t_hist = np.arange(1, 61, dtype=float)
    # True hyperbolic: q(t) = qi / (1 + b*Di*t)^(1/b)
    qi_true, Di_true, b_true = 5000.0, 0.08, 0.6
    q_true = qi_true * (1.0 + b_true * Di_true * t_hist) ** (-1.0 / b_true)
    # Add 5% noise
    noise = np.random.normal(0, 0.05 * q_true, size=len(q_true))
    q_obs = np.maximum(q_true + noise, 10.0)

    historical_df = pd.DataFrame({"month": t_hist.astype(int), "rate_bbl": q_obs})

    adc = ArpsDeclineCurve()
    result = adc.fit(historical_df, model="hyperbolic", economic_limit=10.0, months=240)

    return result, historical_df


# ---------------------------------------------------------------------------
# 2. Chart builders
# ---------------------------------------------------------------------------

def make_npv_sensitivity_chart(scenario_results: list[dict]) -> go.Figure:
    """Bar chart: NPV at 8%/10%/12% for all scenarios."""
    fig = go.Figure()
    dr_labels = ["NPV @ 8%", "NPV @ 10%", "NPV @ 12%"]
    dr_keys = ["npv_8pct", "npv_10pct", "npv_12pct"]
    bar_colors = ["#1565C0", "#1976D2", "#42A5F5"]

    x_positions = list(range(len(scenario_results)))
    scenario_labels = [r["short"] for r in scenario_results]
    bar_width = 0.25

    for i, (label, key, bcolor) in enumerate(zip(dr_labels, dr_keys, bar_colors)):
        offsets = [x + (i - 1) * bar_width for x in x_positions]
        values = [r[key] for r in scenario_results]
        fig.add_trace(
            go.Bar(
                x=offsets,
                y=values,
                name=label,
                marker_color=bcolor,
                width=bar_width,
                text=[f"${v:,.0f}M" for v in values],
                textposition="outside",
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "Scenario: " + "%{customdata}<br>"
                    "NPV: $%{y:,.1f}M<extra></extra>"
                ),
                customdata=scenario_labels,
            )
        )

    fig.update_layout(
        title={
            "text": "NPV Sensitivity by Discount Rate — All Scenarios",
            "font": {"size": 16, "color": "#1A237E"},
        },
        xaxis=dict(
            tickmode="array",
            tickvals=x_positions,
            ticktext=scenario_labels,
            title="Development Scenario",
        ),
        yaxis=dict(title="Net Present Value (US$ Millions)", zeroline=True),
        barmode="group",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=420,
        margin=dict(t=80, b=60, l=70, r=30),
    )
    return fig


def make_scenario_comparison_chart(scenario_results: list[dict]) -> go.Figure:
    """Multi-metric bar chart for IRR, MIRR, Payback across scenarios."""
    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=["IRR (Annual %)", "MIRR (Annual %)", "Payback Period (Years)"],
        shared_yaxes=False,
    )

    names = [r["short"] for r in scenario_results]
    colors = [r["color"] for r in scenario_results]

    irr_vals = [r["irr_annual"] * 100 if not np.isnan(r["irr_annual"]) else 0 for r in scenario_results]
    mirr_vals = [r["mirr_annual"] * 100 if not np.isnan(r["mirr_annual"]) else 0 for r in scenario_results]
    pb_vals = [r["payback_years"] if not np.isnan(r["payback_years"]) else 0 for r in scenario_results]

    fig.add_trace(
        go.Bar(x=names, y=irr_vals, marker_color=colors,
               text=[f"{v:.1f}%" for v in irr_vals], textposition="outside",
               name="IRR", showlegend=False,
               hovertemplate="<b>%{x}</b><br>IRR: %{y:.1f}%<extra></extra>"),
        row=1, col=1
    )
    fig.add_trace(
        go.Bar(x=names, y=mirr_vals, marker_color=colors,
               text=[f"{v:.1f}%" for v in mirr_vals], textposition="outside",
               name="MIRR", showlegend=False,
               hovertemplate="<b>%{x}</b><br>MIRR: %{y:.1f}%<extra></extra>"),
        row=1, col=2
    )
    fig.add_trace(
        go.Bar(x=names, y=pb_vals, marker_color=colors,
               text=[f"{v:.1f} yr" for v in pb_vals], textposition="outside",
               name="Payback", showlegend=False,
               hovertemplate="<b>%{x}</b><br>Payback: %{y:.1f} years<extra></extra>"),
        row=1, col=3
    )

    fig.update_yaxes(title_text="IRR (%)", row=1, col=1)
    fig.update_yaxes(title_text="MIRR (%)", row=1, col=2)
    fig.update_yaxes(title_text="Years", row=1, col=3)

    fig.update_layout(
        title={
            "text": "Scenario Financial Metrics Comparison",
            "font": {"size": 16, "color": "#1A237E"},
        },
        template="plotly_white",
        height=400,
        margin=dict(t=80, b=60, l=70, r=30),
    )
    return fig


def make_cumulative_cashflow_chart(scenario_results: list[dict]) -> go.Figure:
    """Line chart showing cumulative cashflow over project life for all scenarios."""
    fig = go.Figure()

    for r in scenario_results:
        cfs = r["cashflows"]
        cum_cfs = np.cumsum(cfs)
        years = list(range(len(cfs)))

        fig.add_trace(
            go.Scatter(
                x=years,
                y=cum_cfs,
                name=r["short"],
                mode="lines+markers",
                line=dict(color=r["color"], width=2),
                marker=dict(size=5),
                hovertemplate=(
                    "<b>" + r["scenario"] + "</b><br>"
                    "Year: %{x}<br>"
                    "Cumulative CF: $%{y:,.1f}M<extra></extra>"
                ),
            )
        )

    fig.add_hline(y=0, line_dash="dot", line_color="gray", annotation_text="Breakeven")

    fig.update_layout(
        title={
            "text": "Cumulative Cashflow Profiles",
            "font": {"size": 16, "color": "#1A237E"},
        },
        xaxis_title="Project Year",
        yaxis_title="Cumulative Cashflow (US$ Millions)",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=400,
        margin=dict(t=80, b=60, l=70, r=30),
    )
    return fig


def make_decline_curve_chart(result, historical_df: pd.DataFrame) -> go.Figure:
    """Plot historical production, fitted decline curve, and 240-month forecast."""
    fig = go.Figure()

    # Historical data (observed)
    fig.add_trace(
        go.Scatter(
            x=historical_df["month"],
            y=historical_df["rate_bbl"],
            mode="markers",
            name="Historical (60 months)",
            marker=dict(color="#1565C0", size=6, symbol="circle-open"),
            hovertemplate="Month %{x}<br>Rate: %{y:,.0f} bbl/mo<extra></extra>",
        )
    )

    # Full forecast (240 months)
    fc = result.forecast_df
    fig.add_trace(
        go.Scatter(
            x=fc["month"],
            y=fc["rate_bbl"],
            mode="lines",
            name=f"Forecast (Hyperbolic, {result.model.capitalize()})",
            line=dict(color="#E53935", width=2),
            hovertemplate="Month %{x}<br>Forecast: %{y:,.0f} bbl/mo<extra></extra>",
        )
    )

    # Add vertical line at end of history
    fig.add_vline(
        x=60, line_dash="dash", line_color="#555",
        annotation_text="History / Forecast boundary",
        annotation_position="top right",
    )

    # Shaded forecast zone
    fig.add_vrect(
        x0=60, x1=240,
        fillcolor="rgba(255, 152, 0, 0.06)",
        layer="below", line_width=0,
    )

    eur_mbbl = result.eur_bbl / 1000.0
    fig.update_layout(
        title={
            "text": (
                f"GoM Well — Arps Hyperbolic Decline Curve  |  "
                f"qi = {result.qi:,.0f} bbl/mo  |  "
                f"Di = {result.Di:.4f}/mo  |  "
                f"b = {result.b:.2f}  |  "
                f"R² = {result.r_squared:.4f}  |  "
                f"EUR = {eur_mbbl:,.0f} Mbbl"
            ),
            "font": {"size": 13, "color": "#1A237E"},
        },
        xaxis_title="Month",
        yaxis_title="Production Rate (bbl/month)",
        template="plotly_white",
        legend=dict(x=0.65, y=0.95),
        height=440,
        margin=dict(t=90, b=60, l=80, r=30),
    )
    return fig


# ---------------------------------------------------------------------------
# 3. HTML assembly
# ---------------------------------------------------------------------------

def _fig_to_div(fig: go.Figure, div_id: str) -> str:
    """Convert Plotly figure to an HTML div string."""
    return fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        div_id=div_id,
        config={"responsive": True, "displayModeBar": True},
    )


def fmt_mm(val: float) -> str:
    if abs(val) >= 1000:
        return f"${val/1000:,.2f}B"
    return f"${val:,.1f}M"


def fmt_pct(val: float) -> str:
    if np.isnan(val):
        return "N/A"
    return f"{val*100:.1f}%"


def fmt_yr(val: float) -> str:
    if np.isnan(val):
        return "N/A"
    return f"{val:.1f} yrs"


def npv_badge(val: float) -> str:
    color = "#1B5E20" if val >= 0 else "#B71C1C"
    bg = "#E8F5E9" if val >= 0 else "#FFEBEE"
    return f'<span style="color:{color};background:{bg};padding:2px 6px;border-radius:4px;font-weight:600;">{fmt_mm(val)}</span>'


def build_summary_table_html(scenario_results: list[dict]) -> str:
    rows = ""
    for r in scenario_results:
        color = r["color"]
        rows += f"""
        <tr>
          <td style="padding:10px 14px;font-weight:600;">
            <span style="display:inline-block;width:12px;height:12px;background:{color};border-radius:2px;margin-right:8px;vertical-align:middle;"></span>
            {r['scenario']}
          </td>
          <td style="padding:10px 14px;color:#555;">{r['development_type']}</td>
          <td style="padding:10px 14px;color:#555;">{r['water_depth']}</td>
          <td style="padding:10px 14px;text-align:right;color:#B71C1C;font-weight:600;">-{fmt_mm(r['capex_mm'])}</td>
          <td style="padding:10px 14px;text-align:right;color:#555;">{fmt_mm(r['revenue_mm_yr'])}/yr</td>
          <td style="padding:10px 14px;text-align:right;color:#555;">{r['life_years']} yrs</td>
          <td style="padding:10px 14px;text-align:right;">{npv_badge(r['npv_8pct'])}</td>
          <td style="padding:10px 14px;text-align:right;">{npv_badge(r['npv_10pct'])}</td>
          <td style="padding:10px 14px;text-align:right;">{npv_badge(r['npv_12pct'])}</td>
          <td style="padding:10px 14px;text-align:right;color:#1565C0;font-weight:600;">{fmt_pct(r['irr_annual'])}</td>
          <td style="padding:10px 14px;text-align:right;color:#4527A0;font-weight:600;">{fmt_pct(r['mirr_annual'])}</td>
          <td style="padding:10px 14px;text-align:right;color:#E65100;">{fmt_yr(r['payback_years'])}</td>
        </tr>"""

    return f"""
    <div style="overflow-x:auto;margin:24px 0;">
      <table style="width:100%;border-collapse:collapse;font-size:13.5px;font-family:system-ui,sans-serif;box-shadow:0 1px 4px rgba(0,0,0,0.08);border-radius:8px;overflow:hidden;">
        <thead>
          <tr style="background:linear-gradient(135deg,#1A237E,#283593);color:white;">
            <th style="padding:12px 14px;text-align:left;">Scenario</th>
            <th style="padding:12px 14px;text-align:left;">Type</th>
            <th style="padding:12px 14px;text-align:left;">Water Depth</th>
            <th style="padding:12px 14px;text-align:right;">CAPEX</th>
            <th style="padding:12px 14px;text-align:right;">Revenue</th>
            <th style="padding:12px 14px;text-align:right;">Life</th>
            <th style="padding:12px 14px;text-align:right;">NPV @8%</th>
            <th style="padding:12px 14px;text-align:right;">NPV @10%</th>
            <th style="padding:12px 14px;text-align:right;">NPV @12%</th>
            <th style="padding:12px 14px;text-align:right;">IRR</th>
            <th style="padding:12px 14px;text-align:right;">MIRR</th>
            <th style="padding:12px 14px;text-align:right;">Payback</th>
          </tr>
        </thead>
        <tbody style="background:white;">
          {rows}
        </tbody>
      </table>
    </div>
    <p style="font-size:11px;color:#888;margin-top:4px;">
      MIRR: finance rate 10%, reinvestment rate 6%. All values in US$ millions unless noted.
    </p>
    """


def build_decline_stats_card(result) -> str:
    eur_mbbl = result.eur_bbl / 1000.0
    stats = [
        ("Model", result.model.capitalize()),
        ("Initial Rate (qᵢ)", f"{result.qi:,.0f} bbl/mo"),
        ("Nominal Decline (Dᵢ)", f"{result.Di:.4f} /mo"),
        ("Hyperbolic b", f"{result.b:.3f}"),
        ("R² Fit Quality", f"{result.r_squared:.4f}"),
        ("EUR (economic limit 10 bbl/mo)", f"{eur_mbbl:,.0f} Mbbls"),
        ("Forecast Horizon", "240 months (20 years)"),
    ]
    items = "".join(
        f'<div style="display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid #EEE;">'
        f'<span style="color:#555;">{k}</span><span style="font-weight:600;color:#1A237E;">{v}</span></div>'
        for k, v in stats
    )
    return f"""
    <div style="background:#F8F9FF;border:1px solid #C5CAE9;border-radius:8px;padding:18px;margin:20px 0;max-width:480px;">
      <h4 style="margin:0 0 12px;color:#1A237E;font-size:14px;text-transform:uppercase;letter-spacing:0.5px;">
        Fitted Decline Parameters — GoM Well
      </h4>
      {items}
    </div>"""


def generate_html(
    scenario_results: list[dict],
    decline_result,
    historical_df: pd.DataFrame,
    output_path: Path,
) -> None:
    npv_fig = make_npv_sensitivity_chart(scenario_results)
    cmp_fig = make_scenario_comparison_chart(scenario_results)
    cum_fig = make_cumulative_cashflow_chart(scenario_results)
    dec_fig = make_decline_curve_chart(decline_result, historical_df)

    npv_div = _fig_to_div(npv_fig, "chart-npv")
    cmp_div = _fig_to_div(cmp_fig, "chart-cmp")
    cum_div = _fig_to_div(cum_fig, "chart-cum")
    dec_div = _fig_to_div(dec_fig, "chart-dec")

    table_html = build_summary_table_html(scenario_results)
    stats_card = build_decline_stats_card(decline_result)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>ACE Engineer — Field Development Economics Analysis</title>
  <script src="https://cdn.plot.ly/plotly-2.27.0.min.js" charset="utf-8"></script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
           background: #F5F7FA; color: #212121; }}

    /* ---- Header ---- */
    .report-header {{
      background: linear-gradient(135deg, #0D47A1 0%, #1565C0 50%, #1976D2 100%);
      color: white; padding: 36px 48px 32px;
      display: flex; justify-content: space-between; align-items: flex-start;
    }}
    .header-left h1 {{ font-size: 26px; font-weight: 700; letter-spacing: -0.3px; }}
    .header-left .subtitle {{ margin-top: 6px; opacity: 0.85; font-size: 14px; }}
    .header-left .badges {{ display: flex; gap: 10px; margin-top: 14px; flex-wrap: wrap; }}
    .badge {{ background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3);
              border-radius: 20px; padding: 4px 14px; font-size: 12px; }}
    .header-right {{ text-align: right; font-size: 12px; opacity: 0.8; }}
    .header-right .date {{ font-size: 18px; font-weight: 600; opacity: 1; }}

    /* ---- KPI Cards ---- */
    .kpi-row {{ display: flex; gap: 16px; padding: 24px 32px; flex-wrap: wrap;
                background: #ECEFF1; border-bottom: 1px solid #CFD8DC; }}
    .kpi-card {{ background: white; border-radius: 10px; padding: 18px 22px; flex: 1;
                 min-width: 160px; box-shadow: 0 1px 4px rgba(0,0,0,0.07);
                 border-top: 3px solid #1565C0; }}
    .kpi-card .label {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.6px;
                        color: #78909C; font-weight: 600; }}
    .kpi-card .value {{ font-size: 22px; font-weight: 700; color: #1A237E; margin-top: 4px; }}
    .kpi-card .sub {{ font-size: 11px; color: #90A4AE; margin-top: 2px; }}

    /* ---- Sections ---- */
    .content {{ max-width: 1400px; margin: 0 auto; padding: 28px 32px; }}
    .section {{ background: white; border-radius: 12px; padding: 28px; margin-bottom: 24px;
                box-shadow: 0 1px 6px rgba(0,0,0,0.06); }}
    .section-title {{ font-size: 17px; font-weight: 700; color: #1A237E;
                      border-left: 4px solid #1565C0; padding-left: 12px; margin-bottom: 18px; }}
    .section-desc {{ font-size: 13px; color: #546E7A; margin-bottom: 16px; line-height: 1.6; }}
    .chart-container {{ width: 100%; }}

    /* ---- Footer ---- */
    .report-footer {{ background: #263238; color: #B0BEC5; text-align: center;
                      padding: 20px 32px; font-size: 12px; margin-top: 8px; }}
    .report-footer strong {{ color: white; }}

    /* ---- Divider ---- */
    .divider {{ border: none; border-top: 1px solid #ECEFF1; margin: 20px 0; }}

    @media (max-width: 768px) {{
      .report-header {{ flex-direction: column; gap: 16px; padding: 24px; }}
      .kpi-row {{ padding: 16px; }}
      .content {{ padding: 16px; }}
    }}
  </style>
</head>
<body>

<!-- ====================== HEADER ====================== -->
<div class="report-header">
  <div class="header-left">
    <h1>ACE Engineer &mdash; Field Development Economics Analysis</h1>
    <div class="subtitle">FDAS Module Demo &bull; Gulf of Mexico / Offshore O&amp;G Scenarios</div>
    <div class="badges">
      <span class="badge">Powered by worldenergydata</span>
      <span class="badge">EconomicsQuery API</span>
      <span class="badge">ArpsDeclineCurve</span>
      <span class="badge">4 Scenarios</span>
      <span class="badge">Interactive Plotly</span>
    </div>
  </div>
  <div class="header-right">
    <div class="date">2026-05-04</div>
    <div style="margin-top:4px;">Confidential &bull; Client Use Only</div>
    <div style="margin-top:4px;">ACEEngineer.com</div>
  </div>
</div>

<!-- ====================== KPI CARDS ====================== -->
<div class="kpi-row">
  <div class="kpi-card">
    <div class="label">Scenarios Analyzed</div>
    <div class="value">4</div>
    <div class="sub">Shelf to Ultra-deepwater</div>
  </div>
  <div class="kpi-card">
    <div class="label">CAPEX Range</div>
    <div class="value">$80M – $2B</div>
    <div class="sub">Tieback to FPSO</div>
  </div>
  <div class="kpi-card">
    <div class="label">Discount Rates</div>
    <div class="value">8% / 10% / 12%</div>
    <div class="sub">Industry standard range</div>
  </div>
  <div class="kpi-card">
    <div class="label">MIRR Parameters</div>
    <div class="value">10% / 6%</div>
    <div class="sub">Finance / Reinvestment</div>
  </div>
  <div class="kpi-card">
    <div class="label">Decline Curve Well</div>
    <div class="value">5,000 bbl/mo</div>
    <div class="sub">GoM Hyperbolic fit (b=0.6)</div>
  </div>
</div>

<!-- ====================== CONTENT ====================== -->
<div class="content">

  <!-- Section 1: Summary Table -->
  <div class="section">
    <div class="section-title">1. Scenario Summary &mdash; All Financial Metrics</div>
    <div class="section-desc">
      Four representative Gulf of Mexico field development scenarios spanning shallow water gas platforms
      to ultra-deepwater FPSO developments. NPV calculated at three discount rates; IRR and MIRR provide
      rate-based performance measures; payback confirms capital recovery timeline.
    </div>
    {table_html}
  </div>

  <!-- Section 2: NPV Sensitivity -->
  <div class="section">
    <div class="section-title">2. NPV Sensitivity by Discount Rate</div>
    <div class="section-desc">
      NPV sensitivity analysis across 8%, 10%, and 12% annual discount rates for all four development
      scenarios. Higher CAPEX developments (FPSO) show greater NPV variance with rate changes, highlighting
      the importance of cost of capital assumptions in deepwater investment decisions.
    </div>
    <div class="chart-container">{npv_div}</div>
  </div>

  <!-- Section 3: IRR / MIRR / Payback -->
  <div class="section">
    <div class="section-title">3. Rate-of-Return &amp; Payback Comparison</div>
    <div class="section-desc">
      IRR (unconstrained reinvestment assumption) vs MIRR (finance rate 10%, reinvestment rate 6%)
      across all scenarios. MIRR typically provides a more conservative and realistic return estimate.
      Payback period identifies when cumulative cashflows turn positive.
    </div>
    <div class="chart-container">{cmp_div}</div>
  </div>

  <!-- Section 4: Cumulative Cashflow -->
  <div class="section">
    <div class="section-title">4. Cumulative Cashflow Profiles</div>
    <div class="section-desc">
      Cumulative cashflow over project life for each scenario, illustrating the capital exposure profile
      and the timing of cashflow recovery. The breakeven line marks the transition from capital at risk
      to positive cumulative returns.
    </div>
    <div class="chart-container">{cum_div}</div>
  </div>

  <!-- Section 5: Decline Curve -->
  <div class="section">
    <div class="section-title">5. Production Decline Curve Analysis &mdash; GoM Well Demo</div>
    <div class="section-desc">
      Arps hyperbolic decline curve fit to 60 months of synthetic GoM well production history
      (qi&nbsp;=&nbsp;5,000&nbsp;bbl/mo, Di&nbsp;=&nbsp;0.08/mo, b&nbsp;=&nbsp;0.6).
      The <code>ArpsDeclineCurve</code> module performs nonlinear least-squares fitting
      (scipy.optimize.curve_fit) and produces a 240-month forecast with EUR estimation.
    </div>
    {stats_card}
    <div class="chart-container">{dec_div}</div>
  </div>

  <!-- Section 6: Methodology Notes -->
  <div class="section">
    <div class="section-title">6. Methodology &amp; Data Notes</div>
    <div class="section-desc">
      <strong>Economics Module (EconomicsQuery):</strong> Implements NPV via discounted cashflow
      accumulation, IRR via Newton-Raphson root finding on the NPV equation, MIRR per the
      Excel-compatible formula (negative cashflows discounted at finance rate, positive cashflows
      compounded at reinvestment rate), and payback as the period when cumulative cashflow first
      crosses zero.
    </div>
    <hr class="divider"/>
    <div class="section-desc">
      <strong>Cashflow Assumptions:</strong> Year 0 = full CAPEX outlay; Years 1&ndash;N = constant
      annual revenue (simplified proxy for production revenue net of OPEX). Real-world models would
      incorporate production ramp-up, decline curves, commodity price assumptions, OPEX escalation,
      and abandonment costs.
    </div>
    <hr class="divider"/>
    <div class="section-desc">
      <strong>Decline Curve (ArpsDeclineCurve):</strong> Hyperbolic Arps model
      q(t)&nbsp;=&nbsp;qᵢ·(1&nbsp;+&nbsp;b·Dᵢ·t)^(−1/b). EUR computed at economic limit
      (10&nbsp;bbl/mo) using analytical integration of the hyperbolic rate equation.
      R² goodness-of-fit reported to validate the curve match quality.
    </div>
    <hr class="divider"/>
    <div class="section-desc">
      <strong>Library:</strong> worldenergydata &bull;
      <strong>Modules:</strong> <code>worldenergydata.fdas.api.EconomicsQuery</code>,
      <code>worldenergydata.production.forecast.decline.ArpsDeclineCurve</code> &bull;
      <strong>Generated:</strong> 2026-05-04
    </div>
  </div>

</div><!-- /content -->

<!-- ====================== FOOTER ====================== -->
<div class="report-footer">
  <strong>ACE Engineer</strong> &bull; Field Development Analytics Suite (FDAS) &bull;
  worldenergydata Python Library &bull;
  Confidential &mdash; For client use only &bull;
  Generated 2026-05-04
</div>

</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    size_kb = output_path.stat().st_size / 1024
    print(f"Report written: {output_path}  ({size_kb:.1f} KB)")


# ---------------------------------------------------------------------------
# 4. Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("Running FDAS GTM report generation...")
    print(f"Output: {OUTPUT_PATH}")
    print()

    # Run scenarios
    scenario_results = []
    for sc in SCENARIOS:
        print(f"  Processing scenario: {sc['name']} ...", end=" ", flush=True)
        r = run_scenario(sc)
        scenario_results.append(r)
        print(
            f"NPV@10%={fmt_mm(r['npv_10pct'])}  IRR={fmt_pct(r['irr_annual'])}  "
            f"Payback={fmt_yr(r['payback_years'])}"
        )

    print()
    print("  Running ArpsDeclineCurve fit (60-month GoM well) ...", end=" ", flush=True)
    decline_result, historical_df = run_decline_curve_demo()
    print(
        f"R²={decline_result.r_squared:.4f}  EUR={decline_result.eur_bbl/1000:.0f} Mbbls"
    )

    print()
    print("  Generating HTML report ...")
    generate_html(scenario_results, decline_result, historical_df, OUTPUT_PATH)
    print()
    print("Done.")


if __name__ == "__main__":
    main()
