"""All-Fields Report Generator for BSEE analysis.

Generates structured reports from AllFieldsRunner output:
- Markdown report with executive summary and era grouping
- CSV export with all fields and metrics
- HTML interactive dashboard via Plotly
"""

import logging
from datetime import datetime
from pathlib import Path

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

    def get_operator_concentration(self) -> dict:
        """Compute basin-level operator concentration from dominant operators.

        Oil is attributed to each field's DOMINANT_OPERATOR, summed across the
        basin.  Returns the Herfindahl-Hirschman Index (HHI, sum of squared
        market shares as fractions in 0..1), top-1 and top-5 oil shares, and
        the ranked operator oil totals.  Guards empty / missing-column input.
        """
        empty = {
            "hhi": None,
            "top1_share": None,
            "top5_share": None,
            "n_operators": 0,
            "operator_oil": {},
        }
        if (
            self._df.empty
            or "DOMINANT_OPERATOR" not in self._df.columns
            or "CUM_OIL_MMBBL" not in self._df.columns
        ):
            return empty

        work = self._df[["DOMINANT_OPERATOR", "CUM_OIL_MMBBL"]].copy()
        work = work[work["DOMINANT_OPERATOR"].notna()]
        work["DOMINANT_OPERATOR"] = work["DOMINANT_OPERATOR"].astype(str).str.strip()
        work = work[work["DOMINANT_OPERATOR"] != ""]
        if work.empty:
            return empty

        by_op = (
            work.groupby("DOMINANT_OPERATOR")["CUM_OIL_MMBBL"]
            .sum()
            .sort_values(ascending=False)
        )
        total = by_op.sum()
        if total <= 0:
            return empty

        shares = by_op / total
        return {
            "hhi": round(float((shares**2).sum()), 4),
            "top1_share": round(float(shares.iloc[0]), 4),
            "top5_share": round(float(shares.iloc[:5].sum()), 4),
            "n_operators": int(by_op.shape[0]),
            "operator_oil": {str(k): round(float(v), 1) for k, v in by_op.items()},
        }

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
                lines.append("| Era | Fields | Oil (MMBBL) | Gas (BCF) | Wells |")
                lines.append("|-----|--------|-------------|-----------|-------|")
                for era, row in era_summary.iterrows():
                    lines.append(
                        f"| {era} | {int(row['FIELD_COUNT'])} "
                        f"| {row['TOTAL_OIL_MMBBL']:,.1f} "
                        f"| {row['TOTAL_GAS_BCF']:,.1f} "
                        f"| {int(row['TOTAL_WELLS'])} |"
                    )
                lines.append("")

            # Operator Concentration
            conc = self.get_operator_concentration()
            if conc.get("hhi") is not None:
                lines.append("## Operator Concentration")
                lines.append("")
                lines.append(
                    f"- **Basin HHI (by dominant-operator oil)**: {conc['hhi']:.4f}"
                )
                lines.append(
                    f"- **Top-1 operator oil share**: {conc['top1_share']:.1%}"
                )
                lines.append(
                    f"- **Top-5 operator oil share**: {conc['top5_share']:.1%}"
                )
                lines.append(
                    f"- **Distinct dominant operators**: {conc['n_operators']}"
                )
                lines.append("")
                lines.append("| Operator | Oil (MMBBL) | Share |")
                lines.append("|----------|-------------|-------|")
                total_oil_conc = sum(conc["operator_oil"].values()) or 1.0
                for op, oil in list(conc["operator_oil"].items())[:5]:
                    lines.append(f"| {op} | {oil:,.1f} | {oil / total_oil_conc:.1%} |")
                lines.append("")

            # Top Fields Table
            lines.append("## Top Fields by Production")
            lines.append("")
            top = self._df.head(20)
            if not top.empty:
                lines.append(
                    "| Field | Era | Oil (MMBBL) | Gas (BCF) | Wells | "
                    "Rec/Well (MMBBL) | BOPD/Well | First Prod | Water Depth (ft) |"
                )
                lines.append(
                    "|-------|-----|-------------|-----------|-------|"
                    "------------------|-----------|------------|------------------|"
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
                    rpw = row.get("REC_PER_WELL_MMBBL", None)
                    rpw_str = f"{rpw:,.3f}" if pd.notna(rpw) else ""
                    bpw = row.get("AVG_BOPD_PER_WELL", None)
                    bpw_str = f"{bpw:,.0f}" if pd.notna(bpw) else ""
                    lines.append(
                        f"| {name} | {era} | {oil:,.1f} | {gas:,.1f} | {wells} "
                        f"| {rpw_str} | {bpw_str} | {first} | {wd_str} |"
                    )
                lines.append("")

            # Tier 2 Financial Summary
            tier2 = self._df[self._df["NPV10_MM_USD"].notna()]
            if not tier2.empty:
                lines.append("## Lower Tertiary Financial Summary")
                lines.append("")
                lines.append("| Field | NPV10 ($MM) | IRR (%) | Payback (yrs) |")
                lines.append("|-------|-------------|---------|---------------|")
                for _, row in tier2.iterrows():
                    name = row.get("FIELD_NAME", row.get("FIELD_CODE", ""))
                    npv = row.get("NPV10_MM_USD", 0)
                    irr = row.get("IRR_PCT", 0)
                    payback = row.get("PAYBACK_YRS", "")
                    lines.append(f"| {name} | {npv:,.0f} | {irr:.1f} | {payback} |")
                lines.append("")

        output_path.write_text("\n".join(lines))
        logger.info("Markdown report written to %s", output_path)

    def generate_csv(self, output_path: Path) -> None:
        """Export all-fields data as CSV."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        df_sorted = self._df.sort_values("CUM_OIL_MMBBL", ascending=False).reset_index(
            drop=True
        )
        df_sorted.to_csv(output_path, index=False)
        logger.info("CSV exported to %s (%d fields)", output_path, len(df_sorted))

    def generate_html(self, output_path: Path) -> None:
        """Generate an interactive HTML dashboard using Plotly."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots  # noqa: F401

            from worldenergydata.bsee.reports.atlas_charts import (
                access_scatter_figure,
                access_scatter_frame,
                rec_per_well_by_era,
                rec_per_well_figure,
                water_depth_figure,
                water_depth_split,
            )

            html_parts = []
            html_parts.append(
                "<html><head><title>BSEE All-Fields Dashboard</title></head><body>"
            )
            html_parts.append(self._html_header())

            if not self._df.empty:
                # Headline: access / concentration scatter (Lower Tertiary thesis)
                scatter_sub = access_scatter_frame(self._df)
                n_shown = len(scatter_sub)
                n_total = len(self._df)
                logger.info(
                    "Access scatter: %d/%d fields shown (material, >=3 wells, "
                    "water depth present); %d dropped",
                    n_shown,
                    n_total,
                    n_total - n_shown,
                )
                html_parts.append(
                    access_scatter_figure(scatter_sub).to_html(full_html=False)
                )
                html_parts.append(
                    f"<p style='color:#555;font-size:0.9em'>Access scatter shows "
                    f"{n_shown} of {n_total} fields (material: cumulative oil &ge; 1 "
                    f"MMBBL, &ge; 3 wells, water depth present); "
                    f"{n_total - n_shown} dropped for missing/insufficient data.</p>"
                )

                # Recovery per well by era cohort
                cohorts = rec_per_well_by_era(self._df)
                html_parts.append(rec_per_well_figure(cohorts).to_html(full_html=False))

                # Water depth distribution + deepwater/shelf split
                split = water_depth_split(self._df)
                html_parts.append(water_depth_figure(self._df).to_html(full_html=False))
                html_parts.append(
                    f"<p style='color:#555;font-size:0.9em'>{split['n_deepwater']} "
                    f"deepwater (&gt;1000 ft) vs {split['n_shelf']} shelf fields of "
                    f"{split['n_with_depth']} with a water-depth source.</p>"
                )

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

                # Chart 1b: Top 10 operators by cumulative oil (bar)
                conc = self.get_operator_concentration()
                op_oil = conc.get("operator_oil") or {}
                if op_oil:
                    top_ops = list(op_oil.items())[:10]
                    figop = go.Figure(
                        data=[
                            go.Bar(
                                x=[o for o, _ in top_ops],
                                y=[v for _, v in top_ops],
                                marker_color="#2ca02c",
                            )
                        ]
                    )
                    figop.update_layout(
                        title="Top 10 Operators by Cumulative Oil Production",
                        xaxis_title="Operator (dominant per field)",
                        yaxis_title="Cumulative Oil (MMBBL)",
                    )
                    html_parts.append(figop.to_html(full_html=False))

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

            html_parts.append(self._html_footnote())
            html_parts.append("</body></html>")
            output_path.write_text("\n".join(html_parts))
            logger.info("HTML dashboard written to %s", output_path)

        except ImportError:
            # Fallback: simple HTML table without Plotly
            logger.warning("Plotly not available — generating basic HTML table")
            self._generate_html_table_fallback(output_path)

    @staticmethod
    def _html_header() -> str:
        """Report title + data-vintage note block."""
        return (
            "<h1>BSEE Gulf of Mexico All-Fields Atlas</h1>"
            "<p style='color:#444;max-width:60em'>"
            "Visualizing the Lower-Tertiary <b>access / concentration</b> thesis "
            "basin-wide: deepwater, high-recovery-per-well hubs (few hard-to-reach "
            "wells) versus the shallow shelf.</p>"
            "<p style='color:#666;font-size:0.9em'>"
            "Data vintage: BSEE OGOR-A public production, 1996&ndash;2025.</p>"
        )

    @staticmethod
    def _html_footnote() -> str:
        """Honest coverage caveat footnote."""
        return (
            "<hr/><p style='color:#777;font-size:0.85em;max-width:60em'>"
            "<b>Footnote.</b> Access is a composite proxy (water depth + BOPD/well "
            "+ operator concentration); OGOR-A has no subsea/dry-tree completion "
            "flag. Fields without a water-depth or era source are shown as "
            "blank/Unknown, not estimated.</p>"
        )

    def _generate_html_table_fallback(self, output_path: Path) -> None:
        """Generate a basic HTML table when Plotly is not available."""
        html = ["<html><head><title>BSEE All-Fields</title></head><body>"]
        html.append("<h1>BSEE All-Fields Analysis</h1>")

        if not self._df.empty:
            html.append(self._df.to_html(index=False, na_rep=""))

        html.append("</body></html>")
        output_path.write_text("\n".join(html))
