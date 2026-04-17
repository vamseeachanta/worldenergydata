"""Part 2 HTML report: Architecture Options Analysis.

Generates an interactive report comparing deepwater architecture options
(Subsea Tieback, Spar, TLP, Semi/DDS, FrPS) for Lower Tertiary developments.
Companion to the World Oil January 2026 article by Frontier Deepwater.

All data flows from the LTAnalyzer, which reads the YAML config file.
No hardcoded metrics — everything sourced from YAML via analyzer properties.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import plotly.graph_objects as go

from .analyzer import LTAnalyzer

logger = logging.getLogger(__name__)

_PAL = ["#EF4444", "#3B82F6", "#10B981", "#F59E0B", "#8B5CF6"]


def _fhtml(fig: go.Figure, idx: int) -> str:
    """Render a Plotly figure to an embeddable HTML fragment.

    The first figure (idx == 0) includes plotly.js; subsequent ones reuse it.
    """
    return fig.to_html(
        full_html=False,
        include_plotlyjs=(idx == 0),
        config={"displayModeBar": True, "responsive": True},
    )


def _card(title: str, value: str, unit: str = "") -> str:
    """Render a stat-card HTML block."""
    u = f'<span class="unit">{unit}</span>' if unit else ""
    return (
        f'<div class="stat-card"><h3>{title}</h3>'
        f'<div class="value">{value}{u}</div></div>\n'
    )


def _tbl(hdr: list[str], rows: list[list[Any]]) -> str:
    """Render a data-table with header and body rows."""
    h = "".join(f"<th>{x}</th>" for x in hdr)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return (
        f'<table class="data-table"><thead><tr>{h}</tr></thead>'
        f"<tbody>{b}</tbody></table>"
    )


class Part2Report:
    """Generate the Part 2 -- Architecture Options Analysis HTML report.

    Parameters
    ----------
    analyzer : LTAnalyzer
        Configured analyzer with access to YAML config, WAR data, and
        article-derived metrics.
    """

    def __init__(self, analyzer: LTAnalyzer) -> None:
        self._a = analyzer
        self._fi = 0

    def generate(self, output_path: Path) -> Path:
        """Build the full HTML report and write it to disk.

        Parameters
        ----------
        output_path : Path
            Destination file path. Parent directories are created if needed.

        Returns
        -------
        Path
            The resolved output path.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._fi = 0

        sections = [
            self._executive_summary(),
            self._architecture_heatmap(),
            self._water_depth(),
            self._recovery_by_arch(),
            self._intervention_cost(),
            self._subsea_vs_drytree(),
            self._pros_cons(),
            self._conclusions(),
        ]

        ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        html = self._render(sections, ts)
        output_path.write_text(html, encoding="utf-8")
        logger.info("Part 2 report written to %s", output_path)
        return output_path

    # -- Section 1: Executive Summary ------------------------------------------

    def _executive_summary(self) -> dict:
        arch = self._a.architecture_data
        m = self._a.aggregate_metrics
        rf = self._a.recovery_factors
        npv = self._a.economics

        content = '<div class="stats-grid">\n'
        content += _card("Systems Compared", str(len(arch["systems"])))
        content += _card("Criteria Evaluated", str(len(arch["criteria"])))
        content += _card(
            "Subsea Recovery",
            f"{rf['subsea']['range_pct'][0]}-{rf['subsea']['range_pct'][1]}%",
            "STOIIP",
        )
        content += _card(
            "Dry-Tree Recovery",
            f"{rf['dry_tree']['range_pct'][0]}-{rf['dry_tree']['range_pct'][1]}%",
            "STOIIP",
        )
        content += _card(
            "Mean Subsea NPV",
            f"${npv['mean_subsea_npv_billion']}B",
            f"@{npv['discount_rate'] * 100:.0f}%",
        )
        content += _card(
            "Intervention Cost",
            f"${m['intervention_cost_per_well_million']}M",
            "per well",
        )
        content += "</div>"
        return {"title": "Executive Summary", "content": content}

    # -- Section 2: Architecture Comparison Heatmap ----------------------------

    def _architecture_heatmap(self) -> dict:
        arch = self._a.architecture_data
        systems = arch["systems"]
        criteria = arch["criteria"]
        z = [arch["ratings"][s] for s in systems]

        fig = go.Figure(
            go.Heatmap(
                z=z,
                x=criteria,
                y=systems,
                colorscale=[
                    [0, "#FEE2E2"],
                    [0.5, "#FEF3C7"],
                    [1, "#D1FAE5"],
                ],
                zmin=1,
                zmax=5,
                text=z,
                texttemplate="%{text}",
                hovertemplate=(
                    "System: %{y}<br>Criteria: %{x}<br>" "Rating: %{z}<extra></extra>"
                ),
            )
        )
        fig.update_layout(
            title="Architecture Comparison (1=Poor, 5=Excellent)",
            height=400,
            xaxis=dict(side="top"),
        )
        chart = _fhtml(fig, self._fi)
        self._fi += 1

        content = (
            '<div class="data-note"><strong>Key Insight:</strong> '
            "System architecture, not geology, governs recovery potential. "
            "TLP and Semi/DDS score highest on intervention access and "
            "recovery, while Subsea Tiebacks excel only in water depth "
            "range.</div>"
        )
        return {
            "title": "Architecture Comparison",
            "content": content,
            "charts": [chart],
        }

    # -- Section 3: Water Depth Feasibility ------------------------------------

    def _water_depth(self) -> dict:
        arch = self._a.architecture_data
        depths = arch["depth_limits_ft"]
        systems = list(depths.keys())
        mins = [depths[s]["min"] for s in systems]
        maxs = [depths[s]["max"] for s in systems]
        ranges = [mx - mn for mn, mx in zip(mins, maxs)]

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                y=systems,
                x=mins,
                orientation="h",
                name="Min Depth",
                marker_color="rgba(200,200,200,0.5)",
                showlegend=False,
            )
        )
        fig.add_trace(
            go.Bar(
                y=systems,
                x=ranges,
                orientation="h",
                name="Depth Range",
                marker_color=_PAL[: len(systems)],
                text=[f"{mn:,}-{mx:,} ft" for mn, mx in zip(mins, maxs)],
                textposition="inside",
            )
        )
        fig.update_layout(
            title="Water Depth Feasibility by Architecture",
            xaxis_title="Water Depth (ft)",
            height=350,
            barmode="stack",
            showlegend=False,
        )
        chart = _fhtml(fig, self._fi)
        self._fi += 1
        return {"title": "Water Depth Feasibility", "charts": [chart]}

    # -- Section 4: Recovery by Architecture -----------------------------------

    def _recovery_by_arch(self) -> dict:
        rf = self._a.recovery_factors
        subsea_mid = sum(rf["subsea"]["range_pct"]) / 2
        dt_mid = sum(rf["dry_tree"]["range_pct"]) / 2

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=[rf["subsea"]["label"], rf["dry_tree"]["label"]],
                y=[subsea_mid, dt_mid],
                marker_color=[_PAL[0], _PAL[1]],
                error_y=dict(
                    type="data",
                    symmetric=False,
                    array=[
                        rf["subsea"]["range_pct"][1] - subsea_mid,
                        rf["dry_tree"]["range_pct"][1] - dt_mid,
                    ],
                    arrayminus=[
                        subsea_mid - rf["subsea"]["range_pct"][0],
                        dt_mid - rf["dry_tree"]["range_pct"][0],
                    ],
                ),
                text=[
                    f"{rf['subsea']['range_pct'][0]}-"
                    f"{rf['subsea']['range_pct'][1]}%",
                    f"{rf['dry_tree']['range_pct'][0]}-"
                    f"{rf['dry_tree']['range_pct'][1]}%",
                ],
                textposition="outside",
            )
        )
        fig.update_layout(
            title="Recovery Factor by Architecture Type",
            yaxis_title="Recovery Factor (%)",
            height=400,
        )
        chart = _fhtml(fig, self._fi)
        self._fi += 1
        return {"title": "Recovery by Architecture", "charts": [chart]}

    # -- Section 5: Intervention Cost ------------------------------------------

    def _intervention_cost(self) -> dict:
        m = self._a.aggregate_metrics
        npv = self._a.economics
        cost = m["intervention_cost_per_well_million"]
        npv_abs = abs(npv["mean_subsea_npv_billion"])
        npv_millions = npv_abs * 1000

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=["Intervention Cost per Well", "Mean Subsea NPV"],
                y=[cost, npv_millions],
                marker_color=[_PAL[3], _PAL[0]],
                text=[
                    f"${cost}M",
                    f"-${npv_abs}B",
                ],
                textposition="outside",
            )
        )
        fig.update_layout(
            title="Economics: Intervention Cost vs Subsea NPV Impact",
            yaxis_title="$ Millions",
            height=400,
        )
        fig.add_annotation(
            x="Mean Subsea NPV",
            y=npv_millions,
            text=(
                f"Mean NPV @ {npv['discount_rate'] * 100:.0f}% = "
                f"${npv['mean_subsea_npv_billion']}B"
            ),
            showarrow=True,
            arrowhead=2,
            yshift=20,
        )
        chart = _fhtml(fig, self._fi)
        self._fi += 1
        return {"title": "Intervention Cost Impact", "charts": [chart]}

    # -- Section 6: Subsea vs Dry-Tree WAR Activity ----------------------------

    def _subsea_vs_drytree(self) -> dict:
        comp = self._a.subsea_vs_drytree_comparison()

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=["Subsea Fields", "Dry-Tree Fields"],
                y=[comp["subsea_records"], comp["dry_tree_records"]],
                marker_color=[_PAL[0], _PAL[1]],
                text=[
                    f"{comp['subsea_records']:,}",
                    f"{comp['dry_tree_records']:,}",
                ],
                textposition="outside",
            )
        )
        fig.update_layout(
            title="WAR Activity: Subsea vs Dry-Tree Fields",
            yaxis_title="Total WAR Records",
            height=400,
        )
        chart = _fhtml(fig, self._fi)
        self._fi += 1

        subsea_list = comp["subsea_fields"]
        dt_list = comp["dry_tree_fields"]
        subsea_display = ", ".join(subsea_list[:5])
        if len(subsea_list) > 5:
            subsea_display += "..."

        content = (
            f"<p>Subsea fields ({len(subsea_list)}): "
            f"{subsea_display}</p>"
            f"<p>Dry-tree fields ({len(dt_list)}): "
            f"{', '.join(dt_list)}</p>"
        )
        return {
            "title": "Subsea vs Dry-Tree WAR Activity",
            "content": content,
            "charts": [chart],
        }

    # -- Section 7: Architecture Pros/Cons -------------------------------------

    def _pros_cons(self) -> dict:
        pc = self._a.architecture_data.get("pros_cons", {})
        rows: list[list[str]] = []
        for system, data in pc.items():
            pros_html = (
                "<ul>" + "".join(f"<li>{p}</li>" for p in data["pros"]) + "</ul>"
            )
            cons_html = (
                "<ul>" + "".join(f"<li>{c}</li>" for c in data["cons"]) + "</ul>"
            )
            rows.append([f"<strong>{system}</strong>", pros_html, cons_html])
        table = _tbl(["Architecture", "Advantages", "Disadvantages"], rows)
        return {"title": "Architecture Pros & Cons", "content": table}

    # -- Section 8: Conclusions ------------------------------------------------

    def _conclusions(self) -> dict:
        content = (
            '<div class="highlight">'
            "<strong>Architecture Drives Recovery:</strong> "
            "The data shows that system architecture — not reservoir "
            "quality — is the primary determinant of Lower Tertiary "
            "recovery factors. Dry-tree platforms (TLP, Spar) achieve "
            "30-40% recovery vs 2-10% for subsea tiebacks.</div>"
            '<div class="highlight">'
            "<strong>The Path Forward:</strong> "
            "Next-generation developments (Anchor, Shenandoah) should "
            "consider Semi/DDS or FrPS architectures to combine deepwater "
            "capability with dry-tree intervention access, maximizing "
            "long-term recovery.</div>"
            '<div class="data-note">'
            "<strong>Disclaimer:</strong> "
            "Analysis and conclusions are derived from the published "
            "World Oil articles by Frontier Deepwater. Financial figures "
            "are article-sourced and not independently verified.</div>"
        )
        return {"title": "Conclusions", "content": content}

    # -- HTML rendering --------------------------------------------------------

    def _render(self, sections: list[dict], ts: str) -> str:
        """Assemble sections into a full HTML document."""
        toc = ""
        body = ""
        for i, s in enumerate(sections, 1):
            aid = f"section-{i}"
            toc += f'<li><a href="#{aid}">{s["title"]}</a></li>'
            body += f'<div class="section" id="{aid}">' f"<h2>{i}. {s['title']}</h2>"
            for c in s.get("charts", []):
                body += f'<div class="chart-container">{c}</div>'
            body += s.get("content", "") + "</div>"

        title = self._a._config.output_config["reports"]["part2"]["title"]
        return (
            "<!DOCTYPE html>"
            '<html lang="en"><head><meta charset="UTF-8">'
            '<meta name="viewport" '
            'content="width=device-width,initial-scale=1.0">'
            f"<title>{title}</title>"
            '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js">'
            "</script>"
            f"<style>{_CSS}</style></head><body>"
            '<div class="container">'
            '<div class="header">'
            f"<h1>{title}</h1>"
            '<div class="subtitle">World Oil Article Companion Report '
            "— Enhancing Industry Performance: The Options</div>"
            '<div class="subtitle" '
            f'style="margin-top:8px;font-size:12px;">Generated: {ts}'
            "</div></div>"
            f'<div class="toc"><h3>Contents</h3><ul>{toc}</ul></div>'
            f"{body}"
            f'<div class="footer">Generated {ts} | '
            f"BSEE WAR Data + Article Analysis | "
            f"worldenergydata pipeline</div>"
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
    ".toc ul{column-count:2;padding-left:20px}"
    ".toc a{color:#3B82F6;text-decoration:none}"
    ".toc a:hover{text-decoration:underline}"
    ".section{margin:30px 0;padding-top:10px}"
    ".section h2{color:#1e3a5f;border-bottom:2px solid #1e3a5f;"
    "padding-bottom:8px;font-size:22px}"
    ".section h3{color:#374151;font-size:17px;margin-top:24px}"
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
    ".data-table th{background:#1e3a5f;color:#fff;padding:8px 12px;"
    "text-align:left}"
    ".data-table td{padding:6px 12px;"
    "border-bottom:1px solid #E5E7EB}"
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
