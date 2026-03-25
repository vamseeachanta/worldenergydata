"""Buckskin field HTML report generator.

Generates a comprehensive interactive HTML report for the Buckskin field
analysis including production summaries, wellbore inventory, drilling
timeline, WAR activity, operator history, and benchmark validation.
Follows the report template pattern from ``scripts/bsee/generate_field_report.py``.
"""

from __future__ import annotations

import html as html_mod
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from .analyzer import BuckskinAnalyzer
from .buckskin_config import BUCKSKIN

logger = logging.getLogger(__name__)

try:
    import plotly  # noqa: F401
    _HAS_PLOTLY = True
except ImportError:
    _HAS_PLOTLY = False

# Reference data (public domain)
_AREA = "Keathley Canyon (KC), Ultra-deepwater Gulf of Mexico"
_BLOCKS = "KC 785, KC 828, KC 829, KC 830, KC 871, KC 872"
_WATER_DEPTH_FT = 6_800
_FORMATION = "Lower Tertiary / Wilcox"
_HOST_FACILITY = "Lucius Spar (LLOG operated)"

# CSS matching generate_field_report.py (minified to stay within file-size budget)
_CSS = (
    "*{margin:0;padding:0;box-sizing:border-box}"
    "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,"
    "Oxygen,Ubuntu,Cantarell,sans-serif;line-height:1.6;color:#333;"
    "background:#f5f5f5;padding:20px}"
    ".container{max-width:1200px;margin:0 auto;background:#fff;"
    "box-shadow:0 2px 10px rgba(0,0,0,.1);border-radius:8px;overflow:hidden}"
    "header{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);"
    "color:#fff;padding:40px;text-align:center}"
    "header h1{font-size:2.5em;margin-bottom:10px}"
    "header p{font-size:1.1em;opacity:.9}"
    ".content{padding:40px}"
    ".section{margin-bottom:40px}"
    ".section h2{color:#667eea;font-size:1.8em;margin-bottom:20px;"
    "padding-bottom:10px;border-bottom:2px solid #667eea}"
    ".stats-grid{display:grid;"
    "grid-template-columns:repeat(auto-fit,minmax(250px,1fr));"
    "gap:20px;margin:20px 0}"
    ".stat-card{background:linear-gradient(135deg,#f5f7fa 0%,#c3cfe2 100%);"
    "padding:25px;border-radius:8px;box-shadow:0 2px 5px rgba(0,0,0,.1)}"
    ".stat-card h3{font-size:.9em;color:#666;text-transform:uppercase;"
    "letter-spacing:1px;margin-bottom:10px}"
    ".stat-card .value{font-size:2em;font-weight:bold;color:#667eea}"
    ".stat-card .unit{font-size:.9em;color:#888;margin-left:5px}"
    "table{width:100%;border-collapse:collapse;margin:20px 0;"
    "background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.1)}"
    "th{background:#667eea;color:#fff;padding:15px;text-align:left;"
    "font-weight:600}"
    "td{padding:12px 15px;border-bottom:1px solid #eee}"
    "tr:hover{background:#f9f9f9}"
    ".highlight{background:#fff3cd;padding:20px;"
    "border-left:4px solid #ffc107;border-radius:4px;margin:20px 0}"
    ".highlight strong{color:#856404}"
    ".data-note{background:#e7f3ff;border-left:4px solid #2196F3;"
    "padding:15px;margin:20px 0;border-radius:4px}"
    ".well-list{max-height:400px;overflow-y:auto;"
    "border:1px solid #ddd;border-radius:4px}"
    ".footer{background:#f8f9fa;padding:20px 40px;text-align:center;"
    "color:#666;border-top:1px solid #eee}"
)


class BuckskinReport:
    """Render an HTML report from a :class:`BuckskinAnalyzer` instance."""

    def __init__(self, analyzer: BuckskinAnalyzer) -> None:
        self._analyzer = analyzer

    def generate_html(
        self,
        output_path: Path,
        decline_results: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Generate full HTML report and return the output path.

        Parameters
        ----------
        output_path:
            Path to write the HTML report.
        decline_results:
            Optional decline curve analysis results from
            ``BuckskinAnalyzer.decline_curve_analysis()``.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        prod = self._analyzer.production_summary()
        inv = self._analyzer.wellbore_inventory()
        benchmarks = self._analyzer.validate_benchmarks()
        war = self._analyzer.war_activity_summary()
        timeline_df = self._analyzer.drilling_timeline()
        wells_df = self._analyzer._data.get("wells", pd.DataFrame())
        well_count_df = self._analyzer.well_count_by_year()
        boem_df = self._analyzer.boem_lease_table()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html_parts: list[str] = [
            self._head(), self._header(now),
            '<div class="content">',
            self._executive_summary(inv, prod),
            self._boem_lease_section(boem_df),
            self._production_section(prod),
            self._production_chart_section(),
            self._well_count_chart_section(well_count_df),
            self._decline_curve_section(decline_results),
            self._wellbore_table(wells_df),
            self._drilling_timeline_section(timeline_df),
            self._war_activity_section(war),
            self._operator_history_section(),
            self._lower_tertiary_section(),
            self._benchmark_section(benchmarks),
            self._buckskin_south_section(),
            "</div>",
            self._footer(now),
            "</div></body></html>",
        ]

        output_path.write_text("\n".join(html_parts), encoding="utf-8")
        logger.info("Report written to %s", output_path)
        return output_path

    # -- Boilerplate -------------------------------------------------------

    @staticmethod
    def _head() -> str:
        return (
            '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
            '<meta charset="UTF-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            "<title>Buckskin Field Analysis Report</title>\n"
            f"<style>{_CSS}</style>\n</head>\n<body>\n"
            '<div class="container">'
        )

    @staticmethod
    def _header(now: str) -> str:
        return (
            "<header><h1>Buckskin Field Analysis</h1>\n"
            "<p>Comprehensive Development &amp; Production Report</p>\n"
            f'<p style="font-size:0.9em;margin-top:10px;">Generated: {now}</p>'
            "</header>"
        )

    @staticmethod
    def _footer(now: str) -> str:
        return (
            '<div class="footer"><p><strong>WorldEnergyData</strong></p>\n'
            f"<p>Generated: {now}</p></div>"
        )

    # -- Executive Summary -------------------------------------------------

    @staticmethod
    def _executive_summary(inv: dict[str, Any], prod: dict[str, Any]) -> str:
        return (
            '<div class="section"><h2>Executive Summary</h2>\n'
            '<div class="stats-grid">\n'
            + _card("Total Wells", f"{inv['total_wells']}", "")
            + _card("Avg Water Depth", f"{_WATER_DEPTH_FT:,}", "ft")
            + _card("Cumulative Oil", f"{prod['cumulative_oil_mmbbl']:,.2f}", "MMBBL")
            + _card("Producing Wells", f"{prod['producing_well_count']}", "")
            + "</div></div>"
        )

    # -- Production Summary ------------------------------------------------

    @staticmethod
    def _production_section(prod: dict[str, Any]) -> str:
        per_block = prod.get("per_block", {})
        rows = ""
        for bn in sorted(per_block):
            b = per_block[bn]
            rows += (
                f"<tr><td>KC {bn}</td><td>{b['oil_bbl']*1e-6:,.3f}</td>"
                f"<td>{b['gas_mcf']*1e-6:,.3f}</td>"
                f"<td>{b['water_bbl']*1e-6:,.3f}</td></tr>\n"
            )
        return (
            '<div class="section"><h2>Production Summary</h2>\n'
            '<div class="stats-grid">\n'
            + _card("Cumulative Oil", f"{prod['cumulative_oil_mmbbl']:,.2f}", "MMBBL")
            + _card("Cumulative Gas", f"{prod['cumulative_gas_bcf']:,.2f}", "BCF")
            + _card("Cumulative Water", f"{prod['cumulative_water_mmbbl']:,.2f}", "MMBBL")
            + "</div>\n"
            + '<div class="data-note"><strong>Peak Annual Rate:</strong> '
            + f"~{prod['peak_oil_rate_bopd']:,.0f} bopd</div>\n"
            + "<table><thead><tr><th>Block</th><th>Oil (MMBBL)</th>"
            + "<th>Gas (BCF)</th><th>Water (MMBBL)</th></tr></thead><tbody>\n"
            + rows + "</tbody></table></div>"
        )

    # -- Production chart (Plotly or fallback) -----------------------------

    def _production_chart_section(self) -> str:
        chart = self._production_chart_html()
        return (
            f'<div class="section"><h2>Annual Production by Year</h2>\n'
            f"{chart}\n</div>"
        ) if chart else ""

    def _production_chart_html(self) -> str:
        """Generate Plotly bar chart of annual production."""
        df = self._analyzer._data.get("production", pd.DataFrame())
        if df.empty:
            return ""
        year_col = _col(df, ["PROD_YEAR", "YEAR"])
        oil_col = _col(df, ["MON_O_PROD_VOL", "OIL_STB"])
        gas_col = _col(df, ["MON_G_PROD_VOL", "GAS_MCF"])
        water_col = _col(df, ["MON_WTR_PROD_VOL", "WTR_STB"])
        if year_col is None or oil_col is None:
            return ""

        agg_spec: dict[str, tuple[str, str]] = {"oil": (oil_col, "sum")}
        if gas_col:
            agg_spec["gas"] = (gas_col, "sum")
        if water_col:
            agg_spec["water"] = (water_col, "sum")
        annual = df.groupby(year_col).agg(**agg_spec).reset_index()
        if "gas" not in annual.columns:
            annual["gas"] = 0
        if "water" not in annual.columns:
            annual["water"] = 0
        years = annual[year_col].tolist()

        if _HAS_PLOTLY:
            return _plotly_div(years, annual)
        return _fallback_prod_table(years, annual)

    # -- Wellbore Inventory ------------------------------------------------

    @staticmethod
    def _wellbore_table(wdf: pd.DataFrame) -> str:
        if wdf.empty:
            return '<div class="section"><h2>Wellbore Inventory</h2><p>No data.</p></div>'
        ac = _col(wdf, ["API_WELL_NUMBER", "API"])
        nc = _col(wdf, ["WELL_NAME", "WELL_NM"])
        tc = _col(wdf, ["WELL_TYPE_CODE", "TYPE_CODE"])
        bc = _col(wdf, ["BOTM_BLOCK_NUM", "BLOCK_NUM"])
        dc = _col(wdf, ["WATER_DEPTH"])
        sc = _col(wdf, ["WELL_SPUD_DATE", "SPUD_DATE"])
        rows = ""
        esc = html_mod.escape
        for _, r in wdf.iterrows():
            api = esc(str(r.get(ac, "N/A"))) if ac else "N/A"
            nm = esc(str(r.get(nc, "N/A"))) if nc else "N/A"
            wt = esc(_type_label(r.get(tc, ""))) if tc else "N/A"
            blk = esc(f"KC {r.get(bc, '')}") if bc else "N/A"
            d = r.get(dc, 0) if dc else 0
            ds = f"{float(d):,.0f}" if pd.notna(d) else "N/A"
            sp = esc(_fmt_date(r.get(sc))) if sc else "N/A"
            rows += (
                f"<tr><td>{api}</td><td>{nm}</td><td>{wt}</td>"
                f"<td>{blk}</td><td>{ds}</td><td>{sp}</td></tr>\n"
            )
        return (
            '<div class="section"><h2>Wellbore Inventory</h2>\n'
            '<div class="well-list"><table><thead><tr>'
            "<th>API Number</th><th>Well Name</th><th>Type</th>"
            "<th>Block</th><th>Water Depth (ft)</th><th>Spud Date</th>"
            "</tr></thead><tbody>\n" + rows + "</tbody></table></div></div>"
        )

    # -- Drilling Timeline -------------------------------------------------

    @staticmethod
    def _drilling_timeline_section(tdf: pd.DataFrame) -> str:
        if tdf.empty:
            return '<div class="section"><h2>Drilling Timeline</h2><p>No data.</p></div>'
        ac = _col(tdf, ["API_WELL_NUMBER", "API"])
        nc = _col(tdf, ["WELL_NAME", "WELL_NM"])
        sc = _col(tdf, ["WELL_SPUD_DATE", "SPUD_DATE"])
        tc = _col(tdf, ["WELL_TYPE_CODE", "TYPE_CODE"])
        rows = ""
        esc = html_mod.escape
        for _, r in tdf.iterrows():
            rows += (
                f"<tr><td>{esc(_fmt_date(r.get(sc))) if sc else 'N/A'}</td>"
                f"<td>{esc(str(r.get(ac, 'N/A'))) if ac else 'N/A'}</td>"
                f"<td>{esc(str(r.get(nc, 'N/A'))) if nc else 'N/A'}</td>"
                f"<td>{esc(_type_label(r.get(tc, ''))) if tc else 'N/A'}</td></tr>\n"
            )
        return (
            '<div class="section"><h2>Drilling Timeline</h2>\n'
            "<table><thead><tr><th>Spud Date</th><th>API Number</th>"
            "<th>Well Name</th><th>Type</th></tr></thead><tbody>\n"
            + rows + "</tbody></table></div>"
        )

    # -- WAR Activity Summary ----------------------------------------------

    @staticmethod
    def _war_activity_section(war: dict[str, int]) -> str:
        if not war:
            return '<div class="section"><h2>WAR Activity Summary</h2><p>No data.</p></div>'
        rows = "".join(
            f"<tr><td>{html_mod.escape(str(c))}</td><td>{n:,}</td></tr>\n"
            for c, n in sorted(war.items(), key=lambda x: -x[1])
        )
        return (
            '<div class="section"><h2>WAR Activity Summary</h2>\n'
            "<table><thead><tr><th>Activity Type</th><th>Count</th>"
            "</tr></thead><tbody>\n" + rows + "</tbody></table></div>"
        )

    # -- Operator History --------------------------------------------------

    @staticmethod
    def _operator_history_section() -> str:
        return (
            '<div class="section"><h2>Operator History</h2>\n'
            '<div class="highlight"><strong>Discovery (2009):</strong> '
            "Repsol discovered the Buckskin prospect in Keathley Canyon with "
            "an exploration well in ultra-deep water (~6,800 ft).</div>\n"
            '<div class="highlight"><strong>Development &amp; First Oil (2019):'
            "</strong> LLOG Exploration sanctioned the Buckskin development as "
            "a subsea tieback to the Lucius Spar. First oil was achieved in "
            "June 2019 with an initial rate of ~30,000 bopd.</div>\n"
            '<div class="highlight"><strong>Transition (2026):</strong> '
            "Harbour Energy announced the acquisition of LLOG assets including "
            "Buckskin, with the transition expected in 2026.</div></div>"
        )

    # -- Lower Tertiary Classification -------------------------------------

    @staticmethod
    def _lower_tertiary_section() -> str:
        return (
            '<div class="section"><h2>Lower Tertiary Classification</h2>\n'
            '<div class="data-note">Buckskin is a <strong>Wilcox formation'
            "</strong> play within the Lower Tertiary trend of the deepwater "
            "Gulf of Mexico. The Wilcox sandstone reservoirs lie beneath a "
            "thick sequence of Paleogene and Upper Cretaceous sediments in "
            f"water depths exceeding 6,000 ft. Area: {_AREA}. "
            f"Blocks: {_BLOCKS}. Host facility: {_HOST_FACILITY}.</div></div>"
        )

    # -- Benchmark Validation ----------------------------------------------

    @staticmethod
    def _benchmark_section(bm: dict[str, Any]) -> str:
        match = "Yes" if bm.get("first_oil_year_match") else "No"
        return (
            '<div class="section"><h2>Benchmark Validation</h2>\n'
            '<div class="stats-grid">\n'
            + _card("Expected First Oil", str(bm.get("expected_first_oil_year", 2019)), "")
            + _card("Actual First Oil", str(bm.get("first_oil_year", "N/A")), "")
            + _card("Year Match", match, "")
            + _card("Expected Peak Rate", f"{bm.get('expected_peak_rate_bopd', 30_000):,}", "bopd")
            + _card("Producing Wells", str(bm.get("producing_well_count", 0)), "")
            + _card("Formation", str(bm.get("geological_era", _FORMATION)), "")
            + "</div></div>"
        )

    # -- BOEM Lease Mapping ------------------------------------------------

    @staticmethod
    def _boem_lease_section(boem_df: pd.DataFrame) -> str:
        """BOEM OCS lease number mapping table."""
        if boem_df.empty:
            return ""
        rows = ""
        for _, r in boem_df.iterrows():
            ocs = html_mod.escape(str(r.get("BOEM_OCS_Lease", "")))
            blks = html_mod.escape(str(r.get("Blocks", "")))
            rows += f"<tr><td>{ocs}</td><td>{blks}</td></tr>\n"
        return (
            '<div class="section"><h2>BOEM OCS Lease Mapping</h2>\n'
            "<table><thead><tr><th>BOEM OCS Lease</th>"
            "<th>Keathley Canyon Blocks</th></tr></thead><tbody>\n"
            + rows + "</tbody></table></div>"
        )

    # -- Well Count Over Time ----------------------------------------------

    @staticmethod
    def _well_count_chart_section(wc_df: pd.DataFrame) -> str:
        """Cumulative well count over time chart."""
        if wc_df.empty:
            return ""
        years = wc_df["year"].tolist()
        counts = wc_df["cumulative_wells"].tolist()

        if _HAS_PLOTLY:
            trace = json.dumps([{
                "x": years, "y": counts,
                "type": "scatter", "mode": "lines+markers",
                "name": "Cumulative Wells",
                "line": {"color": "#667eea", "width": 3},
                "marker": {"size": 8},
            }])
            layout = json.dumps({
                "title": "Cumulative Well Count Over Time",
                "xaxis": {"title": "Year", "dtick": 1},
                "yaxis": {"title": "Cumulative Wells"},
            })
            div_id = "buckskin-well-count"
            chart = (
                f'<div id="{div_id}" style="width:100%;height:400px;"></div>\n'
                f"<script>Plotly.newPlot('{div_id}',{trace},{layout});</script>"
            )
        else:
            rows = "".join(
                f"<tr><td>{y}</td><td>{c}</td></tr>\n"
                for y, c in zip(years, counts)
            )
            chart = (
                "<table><thead><tr><th>Year</th>"
                "<th>Cumulative Wells</th></tr></thead><tbody>\n"
                + rows + "</tbody></table>"
            )

        return (
            '<div class="section"><h2>Well Count Over Time</h2>\n'
            f"{chart}\n</div>"
        )

    # -- Decline Curve Analysis --------------------------------------------

    @staticmethod
    def _decline_curve_section(
        decline_results: Optional[Dict[str, Any]],
    ) -> str:
        """Decline curve analysis section with model comparison."""
        if not decline_results:
            return ""

        comparison = decline_results.get("comparison")
        forecast = decline_results.get("forecast")
        eur = decline_results.get("eur")

        if comparison is None:
            return ""

        parts = ['<div class="section"><h2>Decline Curve Analysis</h2>\n']

        # Model comparison table
        best = html_mod.escape(comparison.best_model)
        parts.append(
            f'<div class="data-note">Best-fit model: '
            f"<strong>{best}</strong> "
            f"(R\u00b2={comparison.best_fit.curve.r_squared:.4f})</div>\n"
        )

        parts.append(
            "<table><thead><tr><th>Model</th><th>qi</th><th>D</th>"
            "<th>b</th><th>R\u00b2</th><th>RMSE</th><th>AIC</th>"
            "</tr></thead><tbody>\n"
        )
        for name, fit in comparison.fits.items():
            esc_name = html_mod.escape(name)
            is_best = name == comparison.best_model
            cls = ' class="best"' if is_best else ""
            parts.append(
                f"<tr{cls}><td>{esc_name}</td>"
                f"<td>{fit.curve.initial_rate:,.0f}</td>"
                f"<td>{fit.curve.decline_rate:.4f}</td>"
                f"<td>{fit.curve.b_factor:.3f}</td>"
                f"<td>{fit.curve.r_squared:.4f}</td>"
                f"<td>{fit.curve.rmse:,.0f}</td>"
                f"<td>{fit.aic:,.1f}</td></tr>\n"
            )
        parts.append("</tbody></table>\n")

        # EUR comparison
        if eur:
            parts.append('<div class="stats-grid">\n')
            for model, value in eur.items():
                esc_model = html_mod.escape(model)
                parts.append(
                    _card(f"EUR ({esc_model})", f"{value:,.0f}", "units")
                )
            parts.append("</div>\n")

        # Forecast summary
        if forecast is not None:
            vals = forecast.forecast_values
            if len(vals) > 0:
                parts.append(
                    f'<div class="data-note">Forecast: {len(vals)} periods, '
                    f"start={vals[0]:,.0f}, end={vals[-1]:,.0f}</div>\n"
                )

        parts.append("</div>")
        return "".join(parts)

    # -- Buckskin South Expansion ------------------------------------------

    @staticmethod
    def _buckskin_south_section() -> str:
        return (
            '<div class="section"><h2>Buckskin South Expansion</h2>\n'
            '<div class="highlight"><strong>December 2025:</strong> A contract '
            "was awarded for the supply and installation of a subsea umbilical "
            "and flowline system to support the Buckskin South expansion. This "
            "development extends the existing Buckskin field infrastructure in "
            "Keathley Canyon into adjacent blocks, leveraging the Lucius Spar "
            "as the host facility.</div></div>"
        )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Return the first column name present in *df*, or ``None``."""
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _card(title: str, value: str, unit: str) -> str:
    t = html_mod.escape(title)
    v = html_mod.escape(value)
    u = f'<span class="unit">{html_mod.escape(unit)}</span>' if unit else ""
    return f'<div class="stat-card"><h3>{t}</h3><div class="value">{v}{u}</div></div>\n'


def _type_label(code: str | None) -> str:
    if code == "D":
        return "Development"
    if code == "E":
        return "Exploration"
    return str(code) if code else "N/A"


def _fmt_date(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "N/A"
    try:
        return pd.to_datetime(value).strftime("%Y-%m-%d")
    except Exception:
        return str(value)


def _plotly_div(years: list[Any], annual: pd.DataFrame) -> str:
    """Return a Plotly ``<div>`` + ``<script>`` for the production chart."""
    def _trace(col: str, name: str, color: str) -> dict[str, Any]:
        return {"x": years, "y": annual[col].tolist(),
                "type": "bar", "name": name, "marker": {"color": color}}
    traces = [_trace("oil", "Oil (BBL)", "#2ca02c"),
              _trace("gas", "Gas (MCF)", "#d62728"),
              _trace("water", "Water (BBL)", "#1f77b4")]
    layout = {"title": "Annual Production by Year", "barmode": "group",
              "xaxis": {"title": "Year"}, "yaxis": {"title": "Volume"}}
    d = "buckskin-prod-chart"
    return (
        '<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>\n'
        f'<div id="{d}" style="width:100%;height:450px;"></div>\n'
        f"<script>Plotly.newPlot('{d}',"
        f"{json.dumps(traces)},{json.dumps(layout)});</script>"
    )


def _fallback_prod_table(years: list[Any], annual: pd.DataFrame) -> str:
    """Return a plain HTML table when Plotly is unavailable."""
    rows = "".join(
        f"<tr><td>{yr}</td><td>{annual['oil'].iloc[i]:,.0f}</td>"
        f"<td>{annual['gas'].iloc[i]:,.0f}</td>"
        f"<td>{annual['water'].iloc[i]:,.0f}</td></tr>\n"
        for i, yr in enumerate(years)
    )
    return (
        "<table><thead><tr><th>Year</th><th>Oil (BBL)</th>"
        "<th>Gas (MCF)</th><th>Water (BBL)</th></tr></thead><tbody>\n"
        + rows + "</tbody></table>"
    )
