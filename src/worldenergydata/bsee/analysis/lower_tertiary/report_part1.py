"""Part 1 HTML report: Lower Tertiary Performance Analysis.

Generates an interactive companion report to the World Oil October 2025
article 'America's Promising Lower Tertiary Frontier'.  Sections include
executive summary stat cards, validation metrics, recovery factor
comparison, Julia deep-dive, WAR drilling activity, rig utilization,
subsea production curves, cumulative production, well summary, and
methodology/attribution.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go

from .analyzer import LTAnalyzer

logger = logging.getLogger(__name__)

# -- Colour palette -----------------------------------------------------------

_CLR_SUBSEA = "#EF4444"
_CLR_DRYTREE = "#3B82F6"
_FIELD_COLORS = [
    "#3B82F6", "#EF4444", "#10B981", "#F59E0B",
    "#8B5CF6", "#EC4899", "#06B6D4", "#84CC16",
    "#F97316", "#6366F1", "#14B8A6", "#E11D48",
    "#0EA5E9",
]


# -- Module-level helpers -----------------------------------------------------

def _fhtml(fig: go.Figure, idx: int) -> str:
    """Convert Plotly figure to an HTML div.

    Includes the plotly.js bundle only on the first chart (*idx* == 0).
    """
    return fig.to_html(
        full_html=False,
        include_plotlyjs=(idx == 0),
        config={"displayModeBar": True, "responsive": True},
    )


def _card(title: str, value: str, unit: str = "") -> str:
    """Return a single stat-card HTML snippet."""
    u = f'<span class="unit">{unit}</span>' if unit else ""
    return (
        f'<div class="stat-card"><h3>{title}</h3>'
        f'<div class="value">{value}{u}</div></div>\n'
    )


def _tbl(hdr: list[str], rows: list[list[Any]]) -> str:
    """Return a styled HTML data table."""
    h = "".join(f"<th>{x}</th>" for x in hdr)
    b = "".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>"
        for r in rows
    )
    return (
        '<table class="data-table">'
        f"<thead><tr>{h}</tr></thead>"
        f"<tbody>{b}</tbody></table>"
    )


# -- Report class -------------------------------------------------------------

class Part1Report:
    """Generate the Part 1 -- LT Performance Analysis HTML report."""

    def __init__(self, analyzer: LTAnalyzer) -> None:
        self._a = analyzer
        self._fi = 0  # figure index (controls plotly.js inclusion)

    # -- Public API -----------------------------------------------------------

    def generate(self, output_path: Path) -> Path:
        """Build the full HTML report and write it to *output_path*.

        Returns the resolved output path.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._fi = 0

        sections = [
            self._executive_summary(),
            self._validation_metrics(),
            self._recovery_factors(),
            self._julia_deep_dive(),
            self._war_activity(),
            self._rig_utilization(),
            self._production_curves(),
            self._cumulative_production(),
            self._well_summary(),
            self._methodology(),
        ]

        ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        html = self._render(sections, ts)
        output_path.write_text(html, encoding="utf-8")
        logger.info("Part 1 report written to %s", output_path)
        return output_path

    # -- Section 1: Executive Summary -----------------------------------------

    def _executive_summary(self) -> dict:
        m = self._a.aggregate_metrics
        zr = m["zones_perforated_pct_range"]
        cards = [
            ("Total LT Investment", f"${m['total_investment_billion']}B", "USD"),
            ("Total MODU Days", f"{m['total_modu_days']:,}", "days"),
            ("D&C Cost", f"${m['total_dc_cost_billion']}B", "USD"),
            ("Subsea Uptime", f"{m['subsea_uptime_pct']}%", ""),
            ("Intervention Cost/Well", f"${m['intervention_cost_per_well_million']}M", "USD"),
            ("Zones Perforated", f"{zr[0]}-{zr[1]}%", "of pay"),
        ]
        grid = "".join(_card(t, v, u) for t, v, u in cards)
        content = f'<div class="stats-grid">\n{grid}</div>'
        return {"title": "Executive Summary", "content": content}

    # -- Section 2: Validation Metrics ----------------------------------------

    def _validation_metrics(self) -> dict:
        rows = [
            [f["name"], f["appraisal_wells"],
             f"{f['discovery_to_fo_years']}", f"{f['recovery_factor_pct']}%"]
            for f in self._a.validation_table
        ]
        hdr = ["Field", "Appraisal Wells", "Discovery to FO (years)",
               "Recovery Factor"]
        return {"title": "Validation Metrics", "content": _tbl(hdr, rows)}

    # -- Section 3: Recovery Factor Comparison --------------------------------

    def _recovery_factors(self) -> dict:
        rf = self._a.recovery_factors
        sub, dt = rf["subsea"], rf["dry_tree"]
        fig = go.Figure()
        for data, clr in [(sub, _CLR_SUBSEA), (dt, _CLR_DRYTREE)]:
            fig.add_trace(go.Bar(
                x=["Low", "High"], y=data["range_pct"],
                name=data["label"], marker_color=clr,
            ))
        fig.update_layout(title="Recovery Factor: Subsea vs Dry-Tree",
                          yaxis_title="Recovery Factor (%)",
                          barmode="group", height=400)
        chart = _fhtml(fig, self._fi); self._fi += 1
        content = (
            '<div class="highlight"><strong>Key Finding:</strong> '
            f"Subsea developments recover only "
            f"{sub['range_pct'][0]}-{sub['range_pct'][1]}% "
            f"STOIIP vs {dt['range_pct'][0]}-{dt['range_pct'][1]}% "
            f"for dry-tree platforms.</div>"
        )
        return {"title": "Recovery Factor Comparison",
                "content": content, "charts": [chart]}

    # -- Section 4: Julia Deep-Dive -------------------------------------------

    def _julia_deep_dive(self) -> dict:
        jdd = self._a.julia_deep_dive
        oip, sanc = jdd["oip_billion_bbl"], jdd["sanctioned_billion_bbl"]
        actual_bn = jdd["actual_recovery_mmbbl"] / 1000  # Bn for scale
        cats = ["OIP (Bn BBL)", "Sanctioned (Bn BBL)", "Actual Recovery (MMBBL)"]
        vals = [oip, sanc, actual_bn]

        fig = go.Figure(go.Bar(
            x=cats, y=vals, marker_color=["#94A3B8", "#60A5FA", _CLR_SUBSEA],
            text=[f"{v:.2f}" for v in vals], textposition="outside",
        ))
        fig.update_layout(title="Julia Field: OIP vs Sanctioned vs Actual Recovery",
                          yaxis_title="Billion Barrels", height=400)
        fig.add_annotation(
            x="Actual Recovery (MMBBL)", y=actual_bn,
            text=f"Only {jdd['actual_recovery_mmbbl']} MMBBL<br>of {oip}B OIP",
            showarrow=True, arrowhead=2, yshift=30,
        )
        chart = _fhtml(fig, self._fi); self._fi += 1
        content = (
            f'<div class="data-note"><strong>Julia:</strong> '
            f"{oip}B bbl OIP, {sanc}B sanctioned, "
            f"only {jdd['actual_recovery_mmbbl']} MMBBL actually recovered "
            f"(legacy CSV: {jdd['legacy_csv_mmbbl']} MMBBL).</div>"
        )
        return {"title": "Julia Field Deep-Dive",
                "content": content, "charts": [chart]}

    # -- Section 5: WAR Drilling Activity by Field ----------------------------

    def _war_activity(self) -> dict:
        df = self._a.drilling_activity_by_year()
        if df.empty:
            return {"title": "WAR Drilling Activity by Field",
                    "content": "<p>No WAR data available.</p>"}
        fig = go.Figure()
        for i, field in enumerate(sorted(df["field"].unique())):
            fdf = df[df["field"] == field]
            fig.add_trace(go.Bar(
                x=fdf["year"].tolist(), y=fdf["records"].tolist(),
                name=field, marker_color=_FIELD_COLORS[i % len(_FIELD_COLORS)],
            ))
        fig.update_layout(title="WAR Records by Field and Year",
                          xaxis_title="Year", yaxis_title="WAR Records",
                          barmode="stack", height=500,
                          legend=dict(orientation="h", yanchor="bottom", y=1.02))
        chart = _fhtml(fig, self._fi); self._fi += 1
        return {"title": "WAR Drilling Activity by Field", "charts": [chart]}

    # -- Section 6: Rig Utilization -------------------------------------------

    def _rig_utilization(self) -> dict:
        df = self._a.rig_utilization()
        if df.empty:
            return {"title": "Rig Utilization",
                    "content": "<p>No rig data available.</p>"}
        top = (df.groupby("rig_name")["records"].sum()
               .sort_values(ascending=True).tail(20))
        fig = go.Figure(go.Bar(
            y=top.index.tolist(), x=top.values.tolist(), orientation="h",
            marker_color=_CLR_DRYTREE,
            text=[f"{v:,}" for v in top.values], textposition="outside",
        ))
        fig.update_layout(title="Top 20 Rigs by WAR Records (LT Fields)",
                          xaxis_title="WAR Records", height=600,
                          margin=dict(l=250))
        chart = _fhtml(fig, self._fi); self._fi += 1
        return {"title": "Rig Utilization", "charts": [chart]}

    # -- Section 7: Subsea Production Curves ----------------------------------

    def _production_curves(self) -> dict:
        rates = self._a.production_comparison()
        if not rates:
            return {"title": "Subsea Production Curves",
                    "content": "<p>No legacy production data available.</p>"}
        fig = go.Figure()
        for i, (field, df) in enumerate(sorted(rates.items())):
            fig.add_trace(go.Scatter(
                x=df["date"].tolist(), y=df["total_rate"].tolist(),
                mode="lines", name=field.title(),
                line=dict(color=_FIELD_COLORS[i % len(_FIELD_COLORS)], width=2),
            ))
        fig.update_layout(title="Subsea Field Production Rates",
                          xaxis_title="Date", yaxis_title="Total Rate (BOPD)",
                          height=450,
                          legend=dict(orientation="h", yanchor="bottom", y=1.02))
        chart = _fhtml(fig, self._fi); self._fi += 1
        return {"title": "Subsea Production Curves", "charts": [chart]}

    # -- Section 8: Cumulative Production -------------------------------------

    def _cumulative_production(self) -> dict:
        cumul = self._a.cumulative_comparison()
        if not cumul:
            return {"title": "Cumulative Production",
                    "content": "<p>No cumulative data available.</p>"}
        fig = go.Figure()
        for i, (field, df) in enumerate(sorted(cumul.items())):
            fig.add_trace(go.Scatter(
                x=df["date"].tolist(), y=df["cumulative_mmbbl"].tolist(),
                mode="lines", name=field.title(),
                line=dict(color=_FIELD_COLORS[i % len(_FIELD_COLORS)], width=2),
            ))
        fig.update_layout(title="Cumulative Oil Production",
                          xaxis_title="Date", yaxis_title="Cumulative (MMBBL)",
                          height=450,
                          legend=dict(orientation="h", yanchor="bottom", y=1.02))
        chart = _fhtml(fig, self._fi); self._fi += 1
        return {"title": "Cumulative Production", "charts": [chart]}

    # -- Section 9: Well Summary ----------------------------------------------

    def _well_summary(self) -> dict:
        inventory = self._a.well_inventory()
        if not inventory:
            return {"title": "Well Summary",
                    "content": "<p>No well data available.</p>"}
        hdr = ["API12", "Completion", "Cumulative (MMBBL)",
               "Mean Rate (BOPD)", "Start Date", "Last Date"]
        tables = ""
        for field, df in sorted(inventory.items()):
            rows = [
                [r.get("API12", ""), r.get("COMPLETION_NAME", ""),
                 f"{r.get('O_CUMMULATIVE_PROD_MMBBL', 0):.2f}",
                 f"{r.get('O_MEAN_PROD_RATE_BOPD', 0):,.0f}",
                 r.get("START_PRODUCTION_DATE", ""),
                 r.get("LAST_PRODUCTION_DATE", "")]
                for _, r in df.iterrows()
            ]
            tables += f"<h3>{field.title()}</h3>" + _tbl(hdr, rows)
        return {"title": "Well Summary", "content": tables}

    # -- Section 10: Methodology & Attribution --------------------------------

    def _methodology(self) -> dict:
        attr = self._a.source_attribution
        content = (
            '<div class="data-note">'
            f"<strong>Source:</strong> {attr}<br>"
            "<strong>WAR Data:</strong> BSEE eWellWARRawData.zip<br>"
            "<strong>Legacy Production:</strong> "
            "CSV extracts from BSEE production database<br>"
            "<strong>Financial Metrics:</strong> "
            "Article-derived, not independently verified. "
            "All financial figures are sourced from the published "
            "articles and should be referenced accordingly."
            "</div>"
        )
        return {"title": "Methodology & Attribution", "content": content}

    # -- HTML rendering -------------------------------------------------------

    def _render(self, sections: list[dict], ts: str) -> str:
        """Assemble final HTML from section dicts."""
        toc, body = "", ""
        for i, s in enumerate(sections, 1):
            aid = f"section-{i}"
            toc += f'<li><a href="#{aid}">{s["title"]}</a></li>'
            body += (
                f'<div class="section" id="{aid}">'
                f"<h2>{i}. {s['title']}</h2>"
            )
            for c in s.get("charts", []):
                body += f'<div class="chart-container">{c}</div>'
            body += s.get("content", "") + "</div>"

        title = self._a._config.output_config["reports"]["part1"]["title"]
        return (
            '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
            '<meta name="viewport" '
            'content="width=device-width,initial-scale=1.0">'
            f"<title>{title}</title>"
            '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js">'
            "</script>"
            f"<style>{_CSS}</style></head><body>"
            '<div class="container">'
            '<div class="header">'
            f"<h1>{title}</h1>"
            '<div class="subtitle">'
            "World Oil Article Companion Report &mdash; "
            "America&#39;s Promising Lower Tertiary Frontier</div>"
            '<div class="subtitle" '
            'style="margin-top:8px;font-size:12px;">'
            f"Generated: {ts}</div>"
            "</div>"
            f'<div class="toc"><h3>Contents</h3><ul>{toc}</ul></div>'
            f"{body}"
            f'<div class="footer">Generated {ts} | '
            f"BSEE WAR + Legacy Production Data | "
            f"worldenergydata pipeline</div>"
            "</div></body></html>"
        )


# -- CSS (module-level, matching dashboard.py pattern) ------------------------

_CSS = (
    "body{font-family:system-ui,-apple-system,sans-serif;margin:0;padding:20px;"
    "background:#fff;color:#1F2937}"
    ".container{max-width:1200px;margin:0 auto}"
    ".header{text-align:center;padding:30px 0;border-bottom:3px solid #1e3a5f}"
    ".header h1{color:#1e3a5f;margin:0 0 8px;font-size:28px}"
    ".header .subtitle{color:#6B7280;font-size:14px}"
    ".toc{background:#F9FAFB;border:1px solid #E5E7EB;border-radius:6px;"
    "padding:20px 30px;margin:20px 0}"
    ".toc h3{margin-top:0;color:#1e3a5f}.toc ul{column-count:2;padding-left:20px}"
    ".toc a{color:#3B82F6;text-decoration:none}"
    ".toc a:hover{text-decoration:underline}"
    ".section{margin:30px 0;padding-top:10px}"
    ".section h2{color:#1e3a5f;border-bottom:2px solid #1e3a5f;padding-bottom:8px;"
    "font-size:22px}"
    ".section h3{color:#374151;font-size:17px;margin-top:24px}"
    ".chart-container{margin:16px 0}"
    ".stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));"
    "gap:16px;margin:16px 0}"
    ".stat-card{background:linear-gradient(135deg,#f5f7fa 0%,#c3cfe2 100%);"
    "padding:20px;border-radius:8px;box-shadow:0 2px 5px rgba(0,0,0,.1)}"
    ".stat-card h3{font-size:.85em;color:#666;text-transform:uppercase;"
    "letter-spacing:1px;margin:0 0 8px}"
    ".stat-card .value{font-size:1.8em;font-weight:bold;color:#1e3a5f}"
    ".stat-card .unit{font-size:.7em;color:#888;margin-left:4px}"
    ".data-table{width:100%;border-collapse:collapse;margin:16px 0;font-size:13px}"
    ".data-table th{background:#1e3a5f;color:#fff;padding:8px 12px;text-align:left}"
    ".data-table td{padding:6px 12px;border-bottom:1px solid #E5E7EB}"
    ".data-table tr:nth-child(even){background:#F9FAFB}"
    ".data-table tr:hover{background:#EFF6FF}"
    ".highlight{background:#FEF3C7;border-left:4px solid #F59E0B;"
    "padding:16px 20px;border-radius:4px;margin:16px 0}"
    ".highlight strong{color:#92400E}"
    ".data-note{background:#EFF6FF;border-left:4px solid #3B82F6;"
    "padding:16px 20px;border-radius:4px;margin:16px 0}"
    ".footer{text-align:center;padding:20px 0;margin-top:40px;"
    "border-top:1px solid #E5E7EB;color:#9CA3AF;font-size:12px}"
    "ul{line-height:1.8}p{line-height:1.7}"
)
