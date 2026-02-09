"""Intervention insights dashboard (WRK-115 Phase 2).

Produces an interactive 8-panel Plotly HTML dashboard visualising
BSEE WAR intervention activity in the Gulf of Mexico.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from worldenergydata.bsee.analysis.intervention.activity_aggregator import (
    WARActivityAggregator,
    classify_activity,
)

_DISPLAY_NAMES: dict[str, str] = {
    "wireline_unit": "Wireline",
    "coil_tubing_unit": "Coil Tubing",
    "lift_boat": "Lift Boat",
    "snubbing_unit": "Snubbing",
    "support_vessel": "Support Vessel",
    "pumping_unit": "Pumping",
    "workover_rig": "Workover Rig",
}
_INTERVENTION_TYPES = list(_DISPLAY_NAMES.keys())

_CLR_DRILLING = "#3B82F6"
_CLR_INTERVENTION = "#EF4444"
_CLR_PALETTE = [
    "#3B82F6", "#EF4444", "#10B981", "#F59E0B",
    "#8B5CF6", "#EC4899", "#06B6D4", "#84CC16",
]
_CLR_BG = "#FAFAFA"
_CLR_GRID = "#E5E7EB"
_CLR_TEXT = "#1F2937"
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _yearly_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot record counts by [YEAR, ACTIVITY_CATEGORY]."""
    tmp = df.copy()
    tmp["ACTIVITY_CATEGORY"] = tmp["RIG_TYPE"].map(classify_activity)
    tbl = (
        tmp[tmp["ACTIVITY_CATEGORY"].isin(["drilling", "intervention"])]
        .groupby(["YEAR", "ACTIVITY_CATEGORY"]).size()
        .unstack(fill_value=0)
    )
    for cat in ("drilling", "intervention"):
        if cat not in tbl.columns:
            tbl[cat] = 0
    return tbl


def _intervention_slice(
    df: pd.DataFrame, year_lo: int = 2015, year_hi: int = 2025,
) -> pd.DataFrame:
    """Filter to intervention records within a year range."""
    mask = (
        (df["YEAR"] >= year_lo)
        & (df["YEAR"] <= year_hi)
        & (df["RIG_TYPE"].map(classify_activity) == "intervention")
    )
    return df[mask]


class InterventionDashboard:
    """Generate an interactive 8-panel intervention market dashboard."""

    def __init__(self, war_df: pd.DataFrame, fleet_df: pd.DataFrame) -> None:
        self._agg = WARActivityAggregator(war_df, fleet_df)
        enriched = self._agg._join_rig_types()
        self._df = enriched[
            enriched["RIG_NAME"].notna() & enriched["YEAR"].notna()
        ].copy()
        if not self._df.empty:
            self._df["YEAR"] = self._df["YEAR"].astype(int)
        self._has_bus_asc = "BUS_ASC_NAME" in self._df.columns

    def generate(
        self,
        output_path: str = "reports/bsee/intervention/intervention_dashboard.html",
    ) -> str:
        """Generate full dashboard HTML and save to *output_path*."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        fig = make_subplots(
            rows=4, cols=2,
            subplot_titles=[
                "GOM Has Become an Intervention Basin",
                "Intervention-to-Drilling Ratio",
                "Intervention Activity by Service Type (2015-2025)",
                "Service Type Growth: 2015 vs 2024",
                "Top Operators Using Intervention Services (2020-2025)",
                "Addressable Market: Wells & Leases Requiring Intervention",
                "Seasonal Intervention Activity Index",
                "Intervention Activity by GOM Area (2015-2025)",
            ],
            vertical_spacing=0.07, horizontal_spacing=0.10,
            specs=[[{}, {}], [{}, {}],
                   [{}, {"secondary_y": True}],
                   [{"type": "polar"}, {}]],
        )
        for fn, r, c in [
            (self._p1_structural_shift, 1, 1),
            (self._p2_ratio_trend, 1, 2),
            (self._p3_service_type_bar, 2, 1),
            (self._p4_service_type_growth, 2, 2),
            (self._p5_top_operators, 3, 1),
            (self._p6_addressable_market, 3, 2),
            (self._p7_seasonal_pattern, 4, 1),
            (self._p8_geographic, 4, 2),
        ]:
            fn(fig, r, c)

        total = len(self._df)
        yr_min = int(self._df["YEAR"].min()) if not self._df.empty else 0
        yr_max = int(self._df["YEAR"].max()) if not self._df.empty else 0
        ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        fig.update_layout(
            title=dict(
                text=(
                    "GOM Intervention & Workover Services Market Intelligence"
                    "<br><sup>Source: BSEE Well Activity Reports (WAR) | "
                    f"{total:,} enriched records | {yr_min}-{yr_max}</sup>"
                ),
                x=0.5, font=dict(size=22, color=_CLR_TEXT),
            ),
            height=2400, width=1400,
            paper_bgcolor=_CLR_BG, plot_bgcolor="white",
            font=dict(color=_CLR_TEXT, size=11),
            showlegend=False, margin=dict(t=120, b=100),
        )
        fig.add_annotation(
            text=(f"Generated from BSEE WAR data | {total:,} records "
                  f"| {yr_min}-{yr_max} | Dashboard built {ts}"),
            xref="paper", yref="paper", x=0.5, y=-0.02,
            showarrow=False, font=dict(size=10, color="#6B7280"),
        )
        fig.write_html(output_path, include_plotlyjs=True)
        return output_path

    # -- Panel helpers ------------------------------------------------------

    def _p1_structural_shift(self, fig: go.Figure, r: int, c: int) -> None:
        if self._df.empty:
            return
        yearly = _yearly_by_category(self._df)
        if yearly.empty:
            return
        for cat, clr, fill_c in [
            ("drilling", _CLR_DRILLING, "rgba(59,130,246,0.3)"),
            ("intervention", _CLR_INTERVENTION, "rgba(239,68,68,0.3)"),
        ]:
            fig.add_trace(go.Scatter(
                x=yearly.index, y=yearly[cat], name=cat.title(),
                fill="tozeroy", mode="lines",
                line=dict(color=clr, width=1), fillcolor=fill_c,
                showlegend=False,
            ), row=r, col=c)
        cross = yearly[yearly["intervention"] >= yearly["drilling"]].index
        if len(cross):
            yr = int(cross[0])
            fig.add_annotation(
                x=yr, y=float(yearly.loc[yr, "intervention"]),
                text=f"Crossover ~{yr}", showarrow=True, arrowhead=2,
                font=dict(size=10, color=_CLR_INTERVENTION), row=r, col=c,
            )
        fig.update_xaxes(title_text="Year", row=r, col=c)
        fig.update_yaxes(title_text="WAR Records", row=r, col=c)

    def _p2_ratio_trend(self, fig: go.Figure, r: int, c: int) -> None:
        if self._df.empty:
            return
        yearly = _yearly_by_category(self._df)
        if yearly.empty:
            return
        yearly = yearly[yearly.index >= 2000]
        if yearly.empty:
            return
        ratio = (yearly["intervention"]
                 / yearly["drilling"].replace(0, np.nan)).dropna()
        if ratio.empty:
            return
        colours = ["#10B981" if v > 1 else _CLR_INTERVENTION for v in ratio]
        fig.add_trace(go.Scatter(
            x=ratio.index, y=ratio.values, mode="lines+markers",
            marker=dict(color=colours, size=6),
            line=dict(color="#6B7280", width=2), showlegend=False,
        ), row=r, col=c)
        fig.add_hline(
            y=1.0, line_dash="dash", line_color="#9CA3AF",
            annotation_text="Parity (1.0)", annotation_font_size=9,
            row=r, col=c,
        )
        fig.update_xaxes(title_text="Year", row=r, col=c)
        fig.update_yaxes(title_text="Ratio (Intervention / Drilling)",
                         row=r, col=c)

    def _p3_service_type_bar(self, fig: go.Figure, r: int, c: int) -> None:
        if self._df.empty:
            return
        df = self._df[(self._df["YEAR"] >= 2015) & (self._df["YEAR"] <= 2025)]
        counts = (df[df["RIG_TYPE"].isin(_INTERVENTION_TYPES)]
                  .groupby("RIG_TYPE").size().sort_values(ascending=True))
        if counts.empty:
            return
        total = counts.sum()
        labels = [_DISPLAY_NAMES.get(t, t) for t in counts.index]
        fig.add_trace(go.Bar(
            y=labels, x=counts.values, orientation="h",
            text=[f"{v:,} ({v/total*100:.1f}%)" for v in counts.values],
            textposition="outside",
            marker_color=_CLR_PALETTE[:len(labels)], showlegend=False,
        ), row=r, col=c)
        fig.update_xaxes(title_text="WAR Records", row=r, col=c)

    def _p4_service_type_growth(self, fig: go.Figure, r: int, c: int) -> None:
        if self._df.empty:
            return
        df = self._df[self._df["RIG_TYPE"].isin(_INTERVENTION_TYPES)]
        if df.empty:
            return
        yrs = sorted(df["YEAR"].unique())
        y0 = 2015 if 2015 in yrs else yrs[0]
        y1 = 2024 if 2024 in yrs else yrs[-1]
        early = (df[df["YEAR"] == y0].groupby("RIG_TYPE").size()
                 .reindex(_INTERVENTION_TYPES, fill_value=0))
        late = (df[df["YEAR"] == y1].groupby("RIG_TYPE").size()
                .reindex(_INTERVENTION_TYPES, fill_value=0))
        labels = [_DISPLAY_NAMES.get(t, t) for t in _INTERVENTION_TYPES]
        for vals, yr, clr in [(early, y0, _CLR_DRILLING),
                              (late, y1, _CLR_INTERVENTION)]:
            fig.add_trace(go.Bar(
                x=labels, y=vals.values, name=str(yr),
                marker_color=clr, showlegend=False, textposition="none",
            ), row=r, col=c)
        for stype in _INTERVENTION_TYPES:
            e, l = early[stype], late[stype]
            txt = ""
            if e > 0:
                pct = (l - e) / e * 100
                txt = f"{'+' if pct > 0 else ''}{pct:.0f}%"
            elif l > 0:
                txt = "New"
            if txt:
                fig.add_annotation(
                    x=_DISPLAY_NAMES.get(stype, stype), y=max(e, l),
                    text=txt, showarrow=False,
                    font=dict(size=9, color=_CLR_TEXT), yshift=12,
                    row=r, col=c,
                )
        fig.update_layout(barmode="group")
        fig.update_yaxes(title_text="WAR Records", row=r, col=c)

    def _p5_top_operators(self, fig: go.Figure, r: int, c: int) -> None:
        if self._df.empty or not self._has_bus_asc:
            return
        df = _intervention_slice(self._df, 2020, 2025)
        if df.empty:
            return
        top = df.groupby("BUS_ASC_NAME").size().sort_values(ascending=True).tail(15)
        if top.empty:
            return
        decom_kw = ("DECOMMISSION", "ABANDONMENT", "P&A", "PLUG")
        colours = [
            "#F59E0B" if any(k in str(n).upper() for k in decom_kw)
            else _CLR_INTERVENTION for n in top.index
        ]
        fig.add_trace(go.Bar(
            y=top.index, x=top.values, orientation="h",
            marker_color=colours, showlegend=False,
            text=[f"{v:,}" for v in top.values], textposition="outside",
        ), row=r, col=c)
        fig.update_xaxes(title_text="Intervention Records", row=r, col=c)

    def _p6_addressable_market(self, fig: go.Figure, r: int, c: int) -> None:
        if self._df.empty:
            return
        df = _intervention_slice(self._df, 2015, 2025)
        if df.empty:
            return
        by_yr = df.groupby("YEAR").agg(
            wells=("API_WELL_NUMBER", "nunique"),
            leases=("BOTM_LEASE_NUM", "nunique"),
        )
        fig.add_trace(go.Scatter(
            x=by_yr.index, y=by_yr["wells"], mode="lines+markers",
            name="Unique Wells", line=dict(color=_CLR_DRILLING, width=2),
            marker=dict(size=6), showlegend=False,
        ), row=r, col=c)
        fig.add_trace(go.Scatter(
            x=by_yr.index, y=by_yr["leases"], mode="lines+markers",
            name="Unique Leases",
            line=dict(color="#10B981", width=2, dash="dash"),
            marker=dict(size=6), showlegend=False,
        ), row=r, col=c, secondary_y=True)
        fig.update_xaxes(title_text="Year", row=r, col=c)
        fig.update_yaxes(title_text="Unique Wells", row=r, col=c,
                         secondary_y=False)
        fig.update_yaxes(title_text="Unique Leases", row=r, col=c,
                         secondary_y=True)

    def _p7_seasonal_pattern(self, fig: go.Figure, r: int, c: int) -> None:
        if self._df.empty:
            return
        df = _intervention_slice(self._df, 2020, 2025).copy()
        if df.empty:
            return
        if "WAR_START_DT" not in df.columns:
            return
        dt = pd.to_datetime(df["WAR_START_DT"], format="mixed",
                            dayfirst=False, errors="coerce")
        df["MONTH"] = dt.dt.month
        df = df[df["MONTH"].notna()]
        if df.empty:
            return
        monthly = df.groupby("MONTH").size().reindex(range(1, 13), fill_value=0)
        avg = monthly.mean()
        if avg == 0:
            return
        idx = monthly / avg
        colours = [
            "#EF4444" if m in range(6, 12) else _CLR_DRILLING
            for m in range(1, 13)
        ]
        theta = _MONTHS + [_MONTHS[0]]
        r_vals = list(idx.values) + [idx.values[0]]
        c_vals = colours + [colours[0]]
        fig.add_trace(go.Scatterpolar(
            r=r_vals, theta=theta, fill="toself",
            fillcolor="rgba(59,130,246,0.15)",
            line=dict(color=_CLR_DRILLING, width=2),
            marker=dict(color=c_vals, size=7), showlegend=False,
        ), row=r, col=c)
        fig.update_polars(
            radialaxis=dict(gridcolor=_CLR_GRID, tickfont=dict(size=9)),
            angularaxis=dict(gridcolor=_CLR_GRID, tickfont=dict(size=9)),
            bgcolor="white",
        )

    def _p8_geographic(self, fig: go.Figure, r: int, c: int) -> None:
        if self._df.empty:
            return
        df = _intervention_slice(self._df, 2015, 2025)
        if df.empty:
            return
        counts = (df.groupby("AREA_CODE").size()
                  .sort_values(ascending=True).tail(10))
        if counts.empty:
            return
        total = counts.sum()
        labels = [f"{cd} ({v/total*100:.1f}%)"
                  for cd, v in zip(counts.index, counts.values)]
        fig.add_trace(go.Bar(
            y=labels, x=counts.values, orientation="h",
            marker_color=_CLR_PALETTE[:len(labels)], showlegend=False,
            text=[f"{v:,}" for v in counts.values], textposition="outside",
        ), row=r, col=c)
        fig.update_xaxes(title_text="Intervention Records", row=r, col=c)
