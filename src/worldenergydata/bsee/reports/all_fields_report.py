"""All-Fields Report Generator for BSEE analysis.

Generates structured reports from AllFieldsRunner output:
- Markdown report with executive summary and era grouping
- CSV export with all fields and metrics
- HTML interactive dashboard via Plotly
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class AllFieldsReport:
    """Generates reports from all-fields analysis results."""

    def __init__(self, df: pd.DataFrame):
        self._df = df

    def get_era_summary(self) -> pd.DataFrame:
        """Compute summary statistics grouped by geological era."""
        if self._df.empty or "GEOLOGICAL_ERA" not in self._df.columns:
            return pd.DataFrame(columns=["FIELD_COUNT", "TOTAL_OIL_MMBBL"])

        grouped = self._df.groupby("GEOLOGICAL_ERA").agg(
            FIELD_COUNT=("FIELD_CODE", "count"),
            TOTAL_OIL_MMBBL=("CUM_OIL_MMBBL", "sum"),
            TOTAL_GAS_BCF=("CUM_GAS_BCF", "sum"),
            AVG_WATER_DEPTH=("WATER_DEPTH_AVG", "mean"),
            TOTAL_WELLS=("WELL_COUNT", "sum"),
        )
        return grouped.sort_values("TOTAL_OIL_MMBBL", ascending=False)

    def generate_markdown(self, output_path: Path) -> None:
        """Generate a structured Markdown report."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines = []
        lines.append("# BSEE All-Fields Analysis")
        lines.append("")
        lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
        lines.append("")

        # Executive Summary
        lines.append("## Executive Summary")
        lines.append("")
        n_fields = len(self._df)
        total_oil = self._df["CUM_OIL_MMBBL"].sum() if not self._df.empty else 0
        total_gas = self._df["CUM_GAS_BCF"].sum() if not self._df.empty else 0
        n_eras = self._df["GEOLOGICAL_ERA"].nunique() if not self._df.empty else 0

        lines.append(f"- **Total fields analyzed**: {n_fields}")
        lines.append(f"- **Cumulative oil production**: {total_oil:,.1f} MMBBL")
        lines.append(f"- **Cumulative gas production**: {total_gas:,.1f} BCF")
        lines.append(f"- **Geological eras represented**: {n_eras}")
        lines.append("")

        # Era Grouping
        if not self._df.empty:
            lines.append("## Production by Geological Era")
            lines.append("")
            era_summary = self.get_era_summary()
            if not era_summary.empty:
                lines.append(
                    "| Era | Fields | Oil (MMBBL) | Gas (BCF) | Wells |"
                )
                lines.append("|-----|--------|-------------|-----------|-------|")
                for era, row in era_summary.iterrows():
                    lines.append(
                        f"| {era} | {int(row['FIELD_COUNT'])} "
                        f"| {row['TOTAL_OIL_MMBBL']:,.1f} "
                        f"| {row['TOTAL_GAS_BCF']:,.1f} "
                        f"| {int(row['TOTAL_WELLS'])} |"
                    )
                lines.append("")

            # Top Fields Table
            lines.append("## Top Fields by Production")
            lines.append("")
            top = self._df.head(20)
            if not top.empty:
                lines.append(
                    "| Field | Era | Oil (MMBBL) | Gas (BCF) | "
                    "Wells | First Prod | Water Depth (ft) |"
                )
                lines.append(
                    "|-------|-----|-------------|-----------|"
                    "-------|------------|------------------|"
                )
                for _, row in top.iterrows():
                    name = row.get("FIELD_NAME", row.get("FIELD_CODE", ""))
                    era = row.get("GEOLOGICAL_ERA", "")
                    oil = row.get("CUM_OIL_MMBBL", 0)
                    gas = row.get("CUM_GAS_BCF", 0)
                    wells = int(row.get("WELL_COUNT", 0))
                    first = row.get("FIRST_PRODUCTION", "")
                    wd = row.get("WATER_DEPTH_AVG", "")
                    wd_str = f"{wd:,.0f}" if pd.notna(wd) else ""
                    lines.append(
                        f"| {name} | {era} | {oil:,.1f} | {gas:,.1f} "
                        f"| {wells} | {first} | {wd_str} |"
                    )
                lines.append("")

            # Tier 2 Financial Summary
            tier2 = self._df[self._df["NPV10_MM_USD"].notna()]
            if not tier2.empty:
                lines.append("## Lower Tertiary Financial Summary")
                lines.append("")
                lines.append(
                    "| Field | NPV10 ($MM) | IRR (%) | Payback (yrs) |"
                )
                lines.append(
                    "|-------|-------------|---------|---------------|"
                )
                for _, row in tier2.iterrows():
                    name = row.get("FIELD_NAME", row.get("FIELD_CODE", ""))
                    npv = row.get("NPV10_MM_USD", 0)
                    irr = row.get("IRR_PCT", 0)
                    payback = row.get("PAYBACK_YRS", "")
                    lines.append(
                        f"| {name} | {npv:,.0f} | {irr:.1f} | {payback} |"
                    )
                lines.append("")

        output_path.write_text("\n".join(lines))
        logger.info("Markdown report written to %s", output_path)

    def generate_csv(self, output_path: Path) -> None:
        """Export all-fields data as CSV."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        df_sorted = self._df.sort_values(
            "CUM_OIL_MMBBL", ascending=False
        ).reset_index(drop=True)
        df_sorted.to_csv(output_path, index=False)
        logger.info("CSV exported to %s (%d fields)", output_path, len(df_sorted))

    def generate_html(self, output_path: Path) -> None:
        """Generate an interactive HTML dashboard using Plotly."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots

            html_parts = []
            html_parts.append(
                "<html><head><title>BSEE All-Fields Dashboard</title></head><body>"
            )
            html_parts.append("<h1>BSEE All-Fields Analysis Dashboard</h1>")

            if not self._df.empty:
                # Chart 1: Oil production by era (bar)
                era_summary = self.get_era_summary()
                if not era_summary.empty:
                    fig1 = go.Figure(
                        data=[
                            go.Bar(
                                x=era_summary.index.tolist(),
                                y=era_summary["TOTAL_OIL_MMBBL"].tolist(),
                                marker_color="#1f77b4",
                            )
                        ]
                    )
                    fig1.update_layout(
                        title="Cumulative Oil Production by Geological Era",
                        xaxis_title="Geological Era",
                        yaxis_title="Cumulative Oil (MMBBL)",
                    )
                    html_parts.append(fig1.to_html(full_html=False))

                # Chart 2: Top 15 fields by production (horizontal bar)
                top15 = self._df.head(15)
                if not top15.empty:
                    fig2 = go.Figure(
                        data=[
                            go.Bar(
                                y=top15["FIELD_NAME"].tolist()[::-1],
                                x=top15["CUM_OIL_MMBBL"].tolist()[::-1],
                                orientation="h",
                                marker_color="#ff7f0e",
                            )
                        ]
                    )
                    fig2.update_layout(
                        title="Top 15 Fields by Cumulative Oil Production",
                        xaxis_title="Cumulative Oil (MMBBL)",
                        height=500,
                    )
                    html_parts.append(fig2.to_html(full_html=False))

            html_parts.append("</body></html>")
            output_path.write_text("\n".join(html_parts))
            logger.info("HTML dashboard written to %s", output_path)

        except ImportError:
            # Fallback: simple HTML table without Plotly
            logger.warning("Plotly not available — generating basic HTML table")
            self._generate_html_table_fallback(output_path)

    def _generate_html_table_fallback(self, output_path: Path) -> None:
        """Generate a basic HTML table when Plotly is not available."""
        html = ["<html><head><title>BSEE All-Fields</title></head><body>"]
        html.append("<h1>BSEE All-Fields Analysis</h1>")

        if not self._df.empty:
            html.append(self._df.to_html(index=False, na_rep=""))

        html.append("</body></html>")
        output_path.write_text("\n".join(html))
