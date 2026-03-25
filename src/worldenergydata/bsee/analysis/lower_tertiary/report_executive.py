"""Executive Summary HTML report: Lower Tertiary overview."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import plotly.graph_objects as go

from .analyzer import LTAnalyzer

logger = logging.getLogger(__name__)

_CLR_SUBSEA = "#EF4444"
_CLR_DRYTREE = "#3B82F6"


def _fhtml(fig: go.Figure, idx: int) -> str:
    """Render a Plotly figure to an HTML fragment.

    The first chart (idx == 0) includes the plotly.js bundle; subsequent
    charts reuse it.  The outer template also loads plotly via CDN as a
    fallback, so ``include_plotlyjs`` is ``'cdn'`` only for the first
    figure and ``False`` thereafter.
    """
    return fig.to_html(
        full_html=False,
        include_plotlyjs=(idx == 0),
        config={"displayModeBar": True, "responsive": True},
    )


def _card(title: str, value: str, unit: str = "") -> str:
    u = f'<span class="unit">{unit}</span>' if unit else ""
    return (
        f'<div class="stat-card"><h3>{title}</h3>'
        f'<div class="value">{value}{u}</div></div>\n'
    )


def _tbl(hdr: list[str], rows: list[list[Any]]) -> str:
    h = "".join(f"<th>{x}</th>" for x in hdr)
    b = "".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>"
        for r in rows
    )
    return (
        '<table class="data-table"><thead><tr>'
        f"{h}</tr></thead><tbody>{b}</tbody></table>"
    )


class ExecutiveReport:
    """Generate the Executive Summary HTML report.

    Combines highlights from both World Oil articles into a concise
    overview backed by live BSEE WAR data and YAML-driven article
    metrics.

    Parameters
    ----------
    analyzer : LTAnalyzer
        Fully initialised analyzer with access to config, WAR data, and
        legacy production loaders.
    """

    def __init__(self, analyzer: LTAnalyzer) -> None:
        self._a = analyzer
        self._fi = 0

    def generate(self, output_path: Path) -> Path:
        """Build the HTML report and write it to *output_path*.

        Returns
        -------
        Path
            The resolved output path that was written.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._fi = 0

        sections = [
            self._scorecard(),
            self._performance_gap(),
            self._war_snapshot(),
            self._investment_implications(),
            self._path_forward(),
        ]

        ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        html = self._render(sections, ts)
        output_path.write_text(html, encoding="utf-8")
        logger.info("Executive report written to %s", output_path)
        return output_path

    # -- Section 1: Two-Decade Scorecard ------------------------------------

    def _scorecard(self) -> dict:
        m = self._a.aggregate_metrics
        rf = self._a.recovery_factors
        econ = self._a.economics
        content = '<div class="stats-grid">\n'
        content += _card(
            "Total Investment", f"${m['total_investment_billion']}B"
        )
        content += _card("D&C Cost", f"${m['total_dc_cost_billion']}B")
        content += _card("MODU Days", f"{m['total_modu_days']:,}")
        content += _card(
            "Subsea Recovery",
            f"{rf['subsea']['range_pct'][0]}-{rf['subsea']['range_pct'][1]}%",
        )
        content += _card(
            "Dry-Tree Recovery",
            f"{rf['dry_tree']['range_pct'][0]}-"
            f"{rf['dry_tree']['range_pct'][1]}%",
        )
        content += _card(
            "Mean Subsea NPV",
            f"${econ['mean_subsea_npv_billion']}B",
            "@10%",
        )
        content += "</div>"
        return {"title": "Two-Decade Scorecard", "content": content}

    # -- Section 2: The Performance Gap -------------------------------------

    def _performance_gap(self) -> dict:
        rf = self._a.recovery_factors

        subsea_mid = sum(rf["subsea"]["range_pct"]) / 2
        dt_mid = sum(rf["dry_tree"]["range_pct"]) / 2

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=[rf["subsea"]["label"]],
                y=[subsea_mid],
                name=rf["subsea"]["label"],
                marker_color=_CLR_SUBSEA,
                width=0.4,
                error_y=dict(
                    type="data",
                    symmetric=False,
                    array=[rf["subsea"]["range_pct"][1] - subsea_mid],
                    arrayminus=[subsea_mid - rf["subsea"]["range_pct"][0]],
                ),
                text=[
                    f"{rf['subsea']['range_pct'][0]}-"
                    f"{rf['subsea']['range_pct'][1]}%"
                ],
                textposition="outside",
            )
        )
        fig.add_trace(
            go.Bar(
                x=[rf["dry_tree"]["label"]],
                y=[dt_mid],
                name=rf["dry_tree"]["label"],
                marker_color=_CLR_DRYTREE,
                width=0.4,
                error_y=dict(
                    type="data",
                    symmetric=False,
                    array=[rf["dry_tree"]["range_pct"][1] - dt_mid],
                    arrayminus=[dt_mid - rf["dry_tree"]["range_pct"][0]],
                ),
                text=[
                    f"{rf['dry_tree']['range_pct'][0]}-"
                    f"{rf['dry_tree']['range_pct'][1]}%"
                ],
                textposition="outside",
            )
        )
        fig.update_layout(
            title="The Recovery Gap: Subsea vs Dry-Tree",
            yaxis_title="Recovery Factor (%)",
            height=400,
            showlegend=False,
        )
        chart = _fhtml(fig, self._fi)
        self._fi += 1
        return {"title": "The Performance Gap", "charts": [chart]}

    # -- Section 3: Live WAR Data Snapshot ----------------------------------

    def _war_snapshot(self) -> dict:
        summary = self._a.war_summary_table()
        if summary.empty:
            return {
                "title": "Live WAR Data Snapshot",
                "content": "<p>No WAR data available.</p>",
            }

        rows: list[list[Any]] = []
        for _, r in summary.iterrows():
            fo_val = r["first_oil"]
            if fo_val is not None and fo_val == fo_val:  # NaN guard
                fo = str(int(fo_val))
            else:
                fo = "TBD"
            rows.append([
                r["field"],
                r["area"],
                r["operator"],
                r["category"].replace("_", " ").title(),
                fo,
                f"{r['records']:,}",
            ])

        table = _tbl(
            ["Field", "Area", "Operator", "Category", "First Oil",
             "WAR Records"],
            rows,
        )
        total = summary["records"].sum()
        content = (
            '<div class="data-note">'
            f"<strong>Total WAR Records:</strong> {total:,} "
            f"across {len(summary)} Lower Tertiary fields</div>"
            + table
        )
        return {"title": "Live WAR Data Snapshot", "content": content}

    # -- Section 4: Investment Implications ---------------------------------

    def _investment_implications(self) -> dict:
        m = self._a.aggregate_metrics
        econ = self._a.economics
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=["Total LT Investment", "D&C Cost", "Mean Subsea NPV"],
                y=[
                    m["total_investment_billion"],
                    m["total_dc_cost_billion"],
                    econ["mean_subsea_npv_billion"],
                ],
                marker_color=["#3B82F6", "#60A5FA", _CLR_SUBSEA],
                text=[
                    f"${m['total_investment_billion']}B",
                    f"${m['total_dc_cost_billion']}B",
                    f"${econ['mean_subsea_npv_billion']}B",
                ],
                textposition="outside",
            )
        )
        fig.update_layout(
            title="Investment vs Returns",
            yaxis_title="$ Billion",
            height=400,
        )
        fig.add_annotation(
            x="Mean Subsea NPV",
            y=econ["mean_subsea_npv_billion"],
            text="Negative NPV indicates<br>value destruction",
            showarrow=True,
            arrowhead=2,
            yshift=-40,
        )
        chart = _fhtml(fig, self._fi)
        self._fi += 1
        return {"title": "Investment Implications", "charts": [chart]}

    # -- Section 5: Path Forward --------------------------------------------

    def _path_forward(self) -> dict:
        content = (
            '<div class="highlight">'
            "<strong>Architecture Matters Most:</strong> "
            "Twenty years of BSEE data demonstrate that development "
            "architecture — not reservoir quality — determines Lower "
            "Tertiary recovery factors. Subsea tiebacks consistently "
            "recover 2-10% STOIIP vs 30-40% for dry-tree.</div>"
            '<div class="highlight">'
            "<strong>Next-Generation Options:</strong> "
            "Semi/DDS and FrPS architectures offer a path to combine "
            "ultra-deepwater capability with dry-tree intervention "
            "access, potentially closing the recovery gap for future "
            "developments.</div>"
            '<div class="highlight">'
            "<strong>Industry Implications:</strong> "
            "With $50B invested and mean subsea NPV of -$1.2B, the "
            "Lower Tertiary play requires fundamental rethinking of "
            "development philosophy to unlock its estimated 6+ billion "
            "barrel resource base.</div>"
            '<div class="data-note">'
            f"<strong>Source:</strong> {self._a.source_attribution}"
            "</div>"
        )
        return {"title": "Path Forward", "content": content}

    # -- HTML rendering -----------------------------------------------------

    def _render(self, sections: list[dict], ts: str) -> str:
        title = self._a.report_title("executive")

        toc = ""
        body = ""
        for i, s in enumerate(sections, 1):
            aid = f"section-{i}"
            toc += f'<li><a href="#{aid}">{s["title"]}</a></li>'
            body += (
                f'<div class="section" id="{aid}">'
                f"<h2>{i}. {s['title']}</h2>"
            )
            for c in s.get("charts", []):
                body += f'<div class="chart-container">{c}</div>'
            body += s.get("content", "")
            body += "</div>"

        return (
            "<!DOCTYPE html>"
            '<html lang="en"><head><meta charset="UTF-8">'
            '<meta name="viewport" '
            'content="width=device-width,initial-scale=1.0">'
            f"<title>{title}</title>"
            '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js">'
            "</script>"
            f"<style>{_CSS}</style>"
            "</head><body>"
            '<div class="container">'
            '<div class="header">'
            f"<h1>{title}</h1>"
            '<div class="subtitle">'
            "World Oil Lower Tertiary Article Series "
            "— Combined Insights</div>"
            '<div class="subtitle" '
            'style="margin-top:8px;font-size:12px;">'
            f"Generated: {ts}</div></div>"
            f'<div class="toc"><h3>Contents</h3><ul>{toc}</ul></div>'
            f"{body}"
            f'<div class="footer">Generated {ts} '
            "| BSEE WAR Data + Article Analysis "
            "| worldenergydata pipeline</div>"
            "</div></body></html>"
        )


_CSS = (
    "body{font-family:system-ui,-apple-system,sans-serif;margin:0;"
    "padding:20px;background:#fff;color:#1F2937}"
    ".container{max-width:1200px;margin:0 auto}"
    ".header{text-align:center;padding:30px 0;"
    "border-bottom:3px solid #1e3a5f}"
    ".header h1{color:#1e3a5f;margin:0 0 8px;font-size:28px}"
    ".header .subtitle{color:#6B7280;font-size:14px}"
    ".toc{background:#F9FAFB;border:1px solid #E5E7EB;"
    "border-radius:6px;padding:20px 30px;margin:20px 0}"
    ".toc h3{margin-top:0;color:#1e3a5f}"
    ".toc ul{padding-left:20px}"
    ".toc a{color:#3B82F6;text-decoration:none}"
    ".toc a:hover{text-decoration:underline}"
    ".section{margin:30px 0;padding-top:10px}"
    ".section h2{color:#1e3a5f;border-bottom:2px solid #1e3a5f;"
    "padding-bottom:8px;font-size:22px}"
    ".chart-container{margin:16px 0}"
    ".stats-grid{display:grid;"
    "grid-template-columns:repeat(auto-fit,minmax(200px,1fr));"
    "gap:16px;margin:16px 0}"
    ".stat-card{background:linear-gradient(135deg,#f5f7fa 0%,"
    "#c3cfe2 100%);padding:20px;border-radius:8px;"
    "box-shadow:0 2px 5px rgba(0,0,0,.1)}"
    ".stat-card h3{font-size:.85em;color:#666;"
    "text-transform:uppercase;letter-spacing:1px;margin:0 0 8px}"
    ".stat-card .value{font-size:1.8em;font-weight:bold;"
    "color:#1e3a5f}"
    ".stat-card .unit{font-size:.7em;color:#888;margin-left:4px}"
    ".data-table{width:100%;border-collapse:collapse;margin:16px 0;"
    "font-size:13px}"
    ".data-table th{background:#1e3a5f;color:#fff;"
    "padding:8px 12px;text-align:left}"
    ".data-table td{padding:6px 12px;"
    "border-bottom:1px solid #E5E7EB}"
    ".data-table tr:nth-child(even){background:#F9FAFB}"
    ".data-table tr:hover{background:#EFF6FF}"
    ".highlight{background:#FEF3C7;"
    "border-left:4px solid #F59E0B;padding:16px 20px;"
    "border-radius:4px;margin:16px 0}"
    ".highlight strong{color:#92400E}"
    ".data-note{background:#EFF6FF;"
    "border-left:4px solid #3B82F6;padding:16px 20px;"
    "border-radius:4px;margin:16px 0}"
    ".footer{text-align:center;padding:20px 0;margin-top:40px;"
    "border-top:1px solid #E5E7EB;color:#9CA3AF;font-size:12px}"
    "ul{line-height:1.8}p{line-height:1.7}"
)
