# ABOUTME: MetoceanDashboard — Plotly HTML dashboard for unified metocean results.
# ABOUTME: Generates time-series overlay, source comparison scatter, coverage map, stats table.

"""
MetoceanDashboard

Builds an interactive Plotly HTML dashboard from a MetoceanResult,
containing at least three panels:

    1. Time-series panel   — overlays data from all sources per parameter
    2. Source comparison   — scatter plot of source A vs source B
    3. Coverage map        — geographic markers coloured by source
    4. Summary stats table — count, mean, std, min, max per source/parameter
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

if TYPE_CHECKING:
    from worldenergydata.metocean.unified.unified_query import MetoceanResult

logger = logging.getLogger(__name__)

# Colour palette for sources
_SOURCE_COLOURS: Dict[str, str] = {
    "ndbc": "#1f77b4",
    "coops": "#ff7f0e",
    "open_meteo": "#2ca02c",
    "met_norway": "#d62728",
    "erddap": "#9467bd",
}


class MetoceanDashboard:
    """
    Builds Plotly HTML dashboards from MetoceanResult objects.

    Panels:
        - Time series: multi-source overlay per parameter
        - Source comparison: scatter A vs B for shared timestamps
        - Coverage map: geographic marker map coloured by source
        - Summary stats: pandas describe() table per (source, parameter)

    Example:
        dash = MetoceanDashboard()
        html = dash.build(result)
        dash.save(result, "output/dashboard.html")
    """

    def __init__(self) -> None:
        """Initialise the dashboard builder."""
        pass

    # ------------------------------------------------------------------
    # Main build method
    # ------------------------------------------------------------------

    def build(self, result: "MetoceanResult") -> str:
        """
        Build a full HTML dashboard from a MetoceanResult.

        Combines time-series, source-comparison, coverage-map, and
        summary-stats panels into a single HTML string.

        Args:
            result: MetoceanResult from UnifiedMetoceanClient.query()

        Returns:
            HTML string containing the full dashboard
        """
        df = result.data
        params = df["parameter"].unique().tolist() if not df.empty else []
        primary_param = params[0] if params else "Hs"

        # Build individual figures
        ts_fig = self.build_time_series(result)
        comp_fig = self.build_source_comparison(result, parameter=primary_param)
        map_fig = self.build_coverage_map(result)
        stats_df = self.build_summary_stats(result)

        # Convert figures to HTML div strings
        ts_html = ts_fig.to_html(full_html=False, include_plotlyjs="cdn")
        comp_html = comp_fig.to_html(full_html=False, include_plotlyjs=False)
        map_html = map_fig.to_html(full_html=False, include_plotlyjs=False)
        stats_html = stats_df.to_html(classes="stats-table", border=1)

        lat = result.query.lat
        lon = result.query.lon
        start = result.query.start_date.date()
        end = result.query.end_date.date()

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Metocean Dashboard ({lat}, {lon})</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
    h1 {{ color: #333; }}
    h2 {{ color: #555; margin-top: 30px; }}
    .stats-table {{ border-collapse: collapse; width: 100%; }}
    .stats-table th, .stats-table td {{ padding: 6px 12px; text-align: right; }}
    .meta {{ color: #777; font-size: 0.9em; }}
  </style>
</head>
<body>
  <h1>Metocean Dashboard</h1>
  <p class="meta">
    Location: ({lat}, {lon}) &nbsp;|&nbsp;
    Period: {start} to {end} &nbsp;|&nbsp;
    Sources: {', '.join(result.sources_used)}
  </p>

  <h2>Time Series</h2>
  {ts_html}

  <h2>Source Comparison ({primary_param})</h2>
  {comp_html}

  <h2>Coverage Map</h2>
  {map_html}

  <h2>Summary Statistics</h2>
  {stats_html}
</body>
</html>"""
        return html

    # ------------------------------------------------------------------
    # Panel builders
    # ------------------------------------------------------------------

    def build_time_series(self, result: "MetoceanResult") -> go.Figure:
        """
        Build a time-series overlay figure from all sources.

        Each unique parameter gets its own subplot row. Each source is
        shown as a separate coloured trace.

        Args:
            result: MetoceanResult

        Returns:
            Plotly Figure object
        """
        df = result.data

        if df.empty:
            fig = go.Figure()
            fig.update_layout(title="Time Series (no data)")
            return fig

        params = df["parameter"].unique().tolist()
        n_rows = max(len(params), 1)

        fig = make_subplots(
            rows=n_rows,
            cols=1,
            shared_xaxes=True,
            subplot_titles=[f"{p}" for p in params],
            vertical_spacing=0.05,
        )

        for row_idx, param in enumerate(params, start=1):
            param_df = df[df["parameter"] == param]
            for source in param_df["source"].unique():
                src_df = param_df[param_df["source"] == source].sort_values("timestamp")
                colour = _SOURCE_COLOURS.get(source, "#888888")
                unit = src_df["unit"].iloc[0] if len(src_df) > 0 else ""
                fig.add_trace(
                    go.Scatter(
                        x=src_df["timestamp"],
                        y=src_df["value"],
                        mode="lines",
                        name=f"{source}",
                        line={"color": colour},
                        legendgroup=source,
                        showlegend=(row_idx == 1),
                        hovertemplate=(
                            f"<b>{source}</b><br>"
                            f"{param}: %{{y:.2f}} {unit}<br>"
                            "%{x}<extra></extra>"
                        ),
                    ),
                    row=row_idx,
                    col=1,
                )

        fig.update_layout(
            height=300 * n_rows,
            title_text="Metocean Time Series",
            template="plotly_white",
        )
        return fig

    def build_source_comparison(
        self,
        result: "MetoceanResult",
        parameter: str = "Hs",
        source_a: Optional[str] = None,
        source_b: Optional[str] = None,
    ) -> go.Figure:
        """
        Build a scatter plot comparing two sources for the same parameter.

        If source_a and source_b are not specified, the first two available
        sources for that parameter are used.

        Args:
            result:    MetoceanResult
            parameter: Standard parameter name (e.g. "Hs")
            source_a:  First source name (optional)
            source_b:  Second source name (optional)

        Returns:
            Plotly Figure object
        """
        df = result.data

        if df.empty:
            fig = go.Figure()
            fig.update_layout(title="Source Comparison (no data)")
            return fig

        param_df = df[df["parameter"] == parameter]
        sources = param_df["source"].unique().tolist()

        if len(sources) < 2:
            # Only one (or zero) source: return a single-source scatter
            fig = go.Figure()
            fig.update_layout(
                title=f"Source Comparison — {parameter} (insufficient sources)"
            )
            return fig

        sa = source_a or sources[0]
        sb = source_b or sources[1]

        a_df = (
            param_df[param_df["source"] == sa]
            .set_index("timestamp")["value"]
            .rename(sa)
        )
        b_df = (
            param_df[param_df["source"] == sb]
            .set_index("timestamp")["value"]
            .rename(sb)
        )

        combined = pd.concat([a_df, b_df], axis=1).dropna()

        unit = param_df["unit"].iloc[0] if not param_df.empty else ""

        fig = go.Figure(
            go.Scatter(
                x=combined[sa],
                y=combined[sb],
                mode="markers",
                marker={"opacity": 0.6, "size": 5},
                hovertemplate=(
                    f"{sa}: %{{x:.2f}} {unit}<br>"
                    f"{sb}: %{{y:.2f}} {unit}<extra></extra>"
                ),
            )
        )

        # 1:1 line
        if not combined.empty:
            mn = combined.values.min()
            mx = combined.values.max()
            fig.add_trace(
                go.Scatter(
                    x=[mn, mx],
                    y=[mn, mx],
                    mode="lines",
                    line={"dash": "dash", "color": "gray"},
                    name="1:1",
                    showlegend=True,
                )
            )

        fig.update_layout(
            title=f"Source Comparison: {parameter} ({sa} vs {sb})",
            xaxis_title=f"{sa} [{unit}]",
            yaxis_title=f"{sb} [{unit}]",
            template="plotly_white",
        )
        return fig

    def build_coverage_map(self, result: "MetoceanResult") -> go.Figure:
        """
        Build a coverage map showing which sources have data at the query location.

        Args:
            result: MetoceanResult

        Returns:
            Plotly Figure object with geographic markers
        """
        lat = result.query.lat
        lon = result.query.lon
        sources_used = result.sources_used

        # Slight offsets so markers don't stack exactly
        offsets = [0, 0.3, -0.3, 0.15, -0.15]

        map_data: List[Dict[str, Any]] = []
        for i, src in enumerate(sources_used):
            offset = offsets[i % len(offsets)]
            map_data.append(
                {
                    "source": src,
                    "lat": lat + offset * 0.1,
                    "lon": lon + offset * 0.1,
                }
            )

        if not map_data:
            map_data.append({"source": "query", "lat": lat, "lon": lon})

        map_df = pd.DataFrame(map_data)

        fig = px.scatter_mapbox(
            map_df,
            lat="lat",
            lon="lon",
            color="source",
            color_discrete_map=_SOURCE_COLOURS,
            zoom=4,
            height=400,
            hover_name="source",
            title="Coverage Map",
        )
        fig.update_layout(
            mapbox_style="open-street-map",
            margin={"r": 0, "t": 40, "l": 0, "b": 0},
        )
        return fig

    def build_summary_stats(self, result: "MetoceanResult") -> pd.DataFrame:
        """
        Build a summary statistics table from the result data.

        Computes count, mean, std, min, and max for each
        (source, parameter) combination.

        Args:
            result: MetoceanResult

        Returns:
            DataFrame with statistics; empty DataFrame if no data
        """
        df = result.data
        if df.empty:
            return pd.DataFrame(
                columns=["source", "parameter", "count", "mean", "std", "min", "max"]
            )

        stats = (
            df.groupby(["source", "parameter"])["value"]
            .agg(count="count", mean="mean", std="std", min="min", max="max")
            .reset_index()
        )
        stats = stats.round(3)
        return stats

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------

    def save(self, result: "MetoceanResult", output_path: str) -> None:
        """
        Build and save the dashboard HTML to a file.

        Args:
            result:      MetoceanResult to visualise
            output_path: File path for the output HTML file
        """
        html = self.build(result)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
        logger.info(f"Dashboard saved to {path}")
