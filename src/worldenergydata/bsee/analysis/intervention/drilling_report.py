"""GOM Drilling Analysis Report (WRK-115).

Produces a multi-section HTML report with Plotly charts analysing
drilling activity in the Gulf of Mexico using BSEE WAR weekly records
and rig fleet classification data.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from worldenergydata.bsee.analysis.intervention.activity_aggregator import (
    WARActivityAggregator,
)

_DRILL_DN: dict[str, str] = {
    "drillship": "Drillship",
    "semi_submersible": "Semi-Submersible",
    "jack_up": "Jack-Up",
    "platform_rig": "Platform Rig",
    "tender_assisted": "Tender Assisted",
    "inland_barge": "Inland Barge",
    "submersible": "Submersible",
}
_DT = list(_DRILL_DN.keys())
_CLR_D, _CLR_I = "#3B82F6", "#EF4444"
_PAL = [
    "#3B82F6",
    "#EF4444",
    "#10B981",
    "#F59E0B",
    "#8B5CF6",
    "#EC4899",
    "#06B6D4",
    "#84CC16",
]
_AP: dict[str, str] = {
    "EI": "Shelf",
    "SS": "Shelf",
    "SP": "Shelf",
    "HI": "Shelf",
    "SM": "Shelf",
    "WD": "Shelf",
    "VR": "Shelf",
    "ST": "Shelf",
    "MP": "Shelf",
    "WC": "Shelf",
    "EC": "Shelf",
    "GI": "Shelf",
    "MI": "Shelf",
    "EB": "Slope",
    "EW": "Slope",
    "MC": "Deepwater",
    "GC": "Deepwater",
    "GB": "Deepwater",
    "VK": "Deepwater",
    "WR": "Ultra-Deepwater",
}
_WDB = [
    (0, 500, "Shallow (<500 ft)"),
    (500, 1500, "Mid-water (500-1500 ft)"),
    (1500, 5000, "Deepwater (1500-5000 ft)"),
    (5000, float("inf"), "Ultra-deepwater (>5000 ft)"),
]


def _fhtml(fig: go.Figure, idx: int) -> str:
    return fig.to_html(
        full_html=False,
        include_plotlyjs=(idx == 0),
        config={"displayModeBar": True, "responsive": True},
    )


def _tbl(hdr: list[str], rows: list[list]) -> str:
    h = "".join(f"<th>{x}</th>" for x in hdr)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table class="data-table"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>'


def _mode(s: pd.Series) -> str:
    m = s.mode()
    return str(m.iloc[0]) if not m.empty else "N/A"


def _wdc(depth: float) -> str:
    for lo, hi, label in _WDB:
        if lo <= depth < hi:
            return label
    return "Unknown"


class DrillingAnalysisReport:
    """Generate a comprehensive drilling analysis HTML report."""

    def __init__(self, war_df: pd.DataFrame, fleet_df: pd.DataFrame) -> None:
        self._agg = WARActivityAggregator(war_df, fleet_df)
        enriched = self._agg._join_rig_types()
        self._df = enriched[
            enriched["RIG_NAME"].notna() & enriched["YEAR"].notna()
        ].copy()
        if not self._df.empty:
            self._df["YEAR"] = self._df["YEAR"].astype(int)
        self._drill = self._df[self._df["RIG_TYPE"].isin(_DT)]
        self._has_bus = "BUS_ASC_NAME" in self._df.columns
        self._has_wd = "WATER_DEPTH" in self._df.columns
        self._fi = 0
        self._enhanced = False
        self._analysis: dict = {}
        self._insights: dict = {}

    @classmethod
    def from_enriched(
        cls,
        enriched_df: pd.DataFrame,
        analysis_results: dict,
        insights: dict,
    ) -> "DrillingAnalysisReport":
        """Construct from Phase 2-4 pipeline output."""
        inst = cls.__new__(cls)
        inst._enhanced = True
        inst._analysis = analysis_results
        inst._insights = insights
        inst._fi = 0
        df = enriched_df.copy()
        # Ensure YEAR column is present and integer typed.
        if "YEAR" not in df.columns:
            dt = pd.to_datetime(
                df["WAR_START_DT"], format="mixed", dayfirst=False, errors="coerce"
            )
            df["YEAR"] = dt.dt.year
        df = df[df["RIG_NAME"].notna() & df["YEAR"].notna()].copy()
        if not df.empty:
            df["YEAR"] = df["YEAR"].astype(int)
        inst._df = df
        inst._drill = df[df["RIG_TYPE"].astype(str).isin(_DT)]
        inst._has_bus = "BUS_ASC_NAME" in df.columns
        inst._has_wd = "WATER_DEPTH" in df.columns
        return inst

    def generate(
        self, output_path: str = "reports/bsee/intervention/drilling_analysis.html"
    ) -> str:
        """Generate full drilling analysis HTML report."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        self._fi = 0
        d = self._drill
        n = len(d)
        y0 = int(d["YEAR"].min()) if not d.empty else 0
        y1 = int(d["YEAR"].max()) if not d.empty else 0
        ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        secs = [
            self._s1(n, y0, y1),
            self._s2(),
            self._s3(),
            self._s4(),
            self._s5(),
            self._s6(),
            self._s7(),
            self._s8(),
        ]
        if self._enhanced:
            secs += [self._se_duration(), self._se_depth(), self._se_insights()]
        secs.append(self._s9(n, y0, y1))
        Path(output_path).write_text(self._html(secs, n, y0, y1, ts), encoding="utf-8")
        return output_path

    # S1: Executive Summary
    def _s1(self, n: int, y0: int, y1: int) -> dict:
        bl: list[str] = []
        d = self._drill
        if d.empty:
            bl.append("No drilling records found in dataset.")
            return {"title": "Executive Summary", "content": self._bul(bl)}
        uw, ur = d["API_WELL_NUMBER"].nunique(), d["RIG_NAME"].nunique()
        top_rt = d["RIG_TYPE"].value_counts().idxmax()
        bl.append(
            f"<strong>{n:,}</strong> drilling WAR records spanning "
            f"<strong>{y0}-{y1}</strong>."
        )
        bl.append(
            f"<strong>{uw:,}</strong> unique wells drilled by "
            f"<strong>{ur:,}</strong> unique rigs."
        )
        bl.append(
            f"Dominant rig type: <strong>{_DRILL_DN.get(top_rt, top_rt)}</strong>."
        )
        if self._has_bus:
            bl.append(
                f"Top operator: <strong>{d.groupby('BUS_ASC_NAME').size().idxmax()}</strong>."
            )
        return {"title": "Executive Summary", "content": self._bul(bl)}

    # S2: Drilling Fleet Composition
    def _s2(self) -> dict:
        ch: list[str] = []
        d = self._drill
        if d.empty:
            return {
                "title": "Drilling Fleet Composition",
                "content": "<p>No drilling data.</p>",
                "charts": [],
            }
        cnt = d["RIG_TYPE"].value_counts().reindex(_DT, fill_value=0)
        cnt = cnt.loc[cnt > 0].sort_values()
        tot = cnt.sum()
        lb = [_DRILL_DN.get(t, t) for t in cnt.index]
        f1 = go.Figure(
            go.Bar(
                y=lb,
                x=cnt.values,
                orientation="h",
                text=[f"{v:,} ({v/tot*100:.1f}%)" for v in cnt.values],
                textposition="outside",
                marker_color=_PAL[: len(lb)],
            )
        )
        f1.update_layout(
            title="Drilling Rig Type Distribution",
            xaxis_title="WAR Records",
            height=400,
            margin=dict(l=160),
        )
        ch.append(_fhtml(f1, self._fi))
        self._fi += 1
        top = d.groupby("RIG_NAME").size().sort_values(ascending=False).head(20)
        rows = []
        for rig in top.index:
            s = d[d["RIG_NAME"] == rig]
            rt = _DRILL_DN.get(_mode(s["RIG_TYPE"]), _mode(s["RIG_TYPE"]))
            rows.append([rig, rt, f"{len(s):,}", str(s["API_WELL_NUMBER"].nunique())])
        tbl = _tbl(["Rig Name", "Type", "Records", "Unique Wells"], rows)
        return {
            "title": "Drilling Fleet Composition",
            "content": "<h3>Top 20 Rigs by Activity</h3>" + tbl,
            "charts": ch,
        }

    # S3: Water Depth Analysis
    def _s3(self) -> dict:
        ch: list[str] = []
        d = self._drill
        if d.empty or not self._has_wd:
            return {
                "title": "Water Depth Analysis",
                "content": "<p>No water depth data available.</p>",
                "charts": [],
            }
        wd = d[d["WATER_DEPTH"].notna()].copy()
        cov = len(wd) / len(d) * 100 if len(d) else 0
        note = (
            f"<p><em>Water depth available for {len(wd):,} of {len(d):,} "
            f"drilling records ({cov:.1f}% coverage).</em></p>"
        )
        if wd.empty:
            return {"title": "Water Depth Analysis", "content": note, "charts": []}
        wd["WD_CAT"] = wd["WATER_DEPTH"].astype(float).apply(_wdc)
        co = [b[2] for b in _WDB]
        cc = wd["WD_CAT"].value_counts().reindex(co, fill_value=0)
        f1 = go.Figure(
            go.Bar(
                x=cc.index.tolist(),
                y=cc.values,
                marker_color=[_PAL[i % len(_PAL)] for i in range(len(cc))],
                text=[f"{v:,}" for v in cc.values],
                textposition="outside",
            )
        )
        f1.update_layout(
            title="Water Depth Distribution",
            xaxis_title="Depth Category",
            yaxis_title="Drilling Records",
            height=400,
        )
        ch.append(_fhtml(f1, self._fi))
        self._fi += 1
        rows = [
            [cat, f"{int(cc.get(cat, 0)):,}", f"{int(cc.get(cat, 0))/len(wd)*100:.1f}%"]
            for cat in co
        ]
        return {
            "title": "Water Depth Analysis",
            "content": note + _tbl(["Depth Category", "Records", "Share"], rows),
            "charts": ch,
        }

    # S4: Drilling Activity by Year
    def _s4(self) -> dict:
        ch: list[str] = []
        d = self._drill
        if d.empty:
            return {
                "title": "Drilling Activity by Year",
                "content": "<p>No data.</p>",
                "charts": [],
            }
        piv = d.groupby(["YEAR", "RIG_TYPE"]).size().unstack(fill_value=0)
        f1 = go.Figure()
        for i, rt in enumerate(_DT):
            if rt not in piv.columns:
                continue
            f1.add_trace(
                go.Bar(
                    x=piv.index.tolist(),
                    y=piv[rt].tolist(),
                    name=_DRILL_DN.get(rt, rt),
                    marker_color=_PAL[i % len(_PAL)],
                )
            )
        totals = d.groupby("YEAR").size()
        f1.add_trace(
            go.Scatter(
                x=totals.index.tolist(),
                y=totals.values.tolist(),
                name="Total",
                mode="lines+markers",
                line=dict(color="#1F2937", width=2, dash="dot"),
                yaxis="y2",
            )
        )
        f1.update_layout(
            title="Drilling Activity by Rig Type per Year",
            barmode="stack",
            xaxis_title="Year",
            yaxis_title="WAR Records",
            yaxis2=dict(title="Total", overlaying="y", side="right"),
            height=450,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        ch.append(_fhtml(f1, self._fi))
        self._fi += 1
        rows, prev = [], 0
        for yr in sorted(d["YEAR"].unique()):
            c = int(totals.get(yr, 0))
            chg = f"{(c-prev)/prev*100:+.1f}%" if prev > 0 else "N/A"
            rows.append([str(yr), f"{c:,}", chg])
            prev = c
        return {
            "title": "Drilling Activity by Year",
            "content": _tbl(["Year", "Records", "YoY Change"], rows),
            "charts": ch,
        }

    # S5: Drilling Duration Analysis
    def _s5(self) -> dict:
        ch: list[str] = []
        d = self._drill
        if d.empty:
            return {
                "title": "Drilling Duration Analysis",
                "content": "<p>No data.</p>",
                "charts": [],
            }
        well = d.groupby("API_WELL_NUMBER").agg(
            records=("RIG_NAME", "size"), rig_type=("RIG_TYPE", "first")
        )
        well["est_days"] = well["records"] * 7
        ad, md, xd = (
            well["est_days"].mean(),
            well["est_days"].median(),
            well["est_days"].max(),
        )
        f1 = go.Figure(
            go.Histogram(x=well["est_days"].tolist(), nbinsx=30, marker_color=_CLR_D)
        )
        f1.update_layout(
            title="Well Drilling Duration (Estimated Days)",
            xaxis_title="Estimated Drilling Days",
            yaxis_title="Number of Wells",
            height=400,
        )
        ch.append(_fhtml(f1, self._fi))
        self._fi += 1
        stats = (
            f"<p>Average: <strong>{ad:.0f}</strong> days | "
            f"Median: <strong>{md:.0f}</strong> days | "
            f"Maximum: <strong>{xd:.0f}</strong> days</p>"
            f"<p><em>Each WAR record ~ 1 week; duration = record count x 7 days.</em></p>"
        )
        rd = well.groupby("rig_type")["est_days"].agg(["mean", "median", "count"])
        rd = rd.sort_values("count", ascending=False)
        rows = [
            [
                _DRILL_DN.get(str(rt), str(rt)),
                f"{r['mean']:.0f}",
                f"{r['median']:.0f}",
                f"{int(r['count']):,}",
            ]
            for rt, r in rd.iterrows()
        ]
        return {
            "title": "Drilling Duration Analysis",
            "content": stats
            + _tbl(["Rig Type", "Avg Days", "Med Days", "Wells"], rows),
            "charts": ch,
        }

    # S6: Geographic Analysis
    def _s6(self) -> dict:
        ch: list[str] = []
        d = self._drill
        if d.empty:
            return {
                "title": "Geographic Analysis",
                "content": "<p>No data.</p>",
                "charts": [],
            }
        d = d.copy()
        d["PROVINCE"] = d["AREA_CODE"].map(_AP).fillna("Other")
        po = ["Shelf", "Slope", "Deepwater", "Ultra-Deepwater", "Other"]
        piv = d.groupby(["YEAR", "PROVINCE"]).size().unstack(fill_value=0)
        clrs = {
            "Shelf": _PAL[0],
            "Slope": _PAL[1],
            "Deepwater": _PAL[2],
            "Ultra-Deepwater": _PAL[3],
            "Other": _PAL[4],
        }
        f1 = go.Figure()
        for prov in po:
            if prov not in piv.columns:
                continue
            f1.add_trace(
                go.Bar(
                    x=piv.index.tolist(),
                    y=piv[prov].tolist(),
                    name=prov,
                    marker_color=clrs.get(prov, "#6B7280"),
                )
            )
        f1.update_layout(
            title="Drilling by Geological Province Over Time",
            barmode="stack",
            xaxis_title="Year",
            yaxis_title="WAR Records",
            height=450,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        ch.append(_fhtml(f1, self._fi))
        self._fi += 1
        ac = d.groupby("AREA_CODE").size().sort_values(ascending=False).head(15)
        rows = [[a, _AP.get(a, "Other"), f"{int(ac[a]):,}"] for a in ac.index]
        return {
            "title": "Geographic Analysis",
            "content": _tbl(["Area Code", "Province", "Records"], rows),
            "charts": ch,
        }

    # S7: Operator Intelligence
    def _s7(self) -> dict:
        ch: list[str] = []
        d = self._drill
        if d.empty or not self._has_bus:
            return {
                "title": "Operator Intelligence",
                "content": "<p>No operator data.</p>",
                "charts": [],
            }
        top = d.groupby("BUS_ASC_NAME").size().sort_values(ascending=True).tail(20)
        f1 = go.Figure(
            go.Bar(
                y=top.index.tolist(),
                x=top.values,
                orientation="h",
                marker_color=_CLR_D,
                text=[f"{v:,}" for v in top.values],
                textposition="outside",
            )
        )
        f1.update_layout(
            title="Top Drilling Operators",
            xaxis_title="WAR Records",
            height=600,
            margin=dict(l=250),
        )
        ch.append(_fhtml(f1, self._fi))
        self._fi += 1
        rows = []
        for op in reversed(top.index):
            s = d[d["BUS_ASC_NAME"] == op]
            rows.append(
                [
                    op,
                    f"{len(s):,}",
                    _DRILL_DN.get(_mode(s["RIG_TYPE"]), _mode(s["RIG_TYPE"])),
                    _mode(s["AREA_CODE"]),
                    str(s["API_WELL_NUMBER"].nunique()),
                ]
            )
        tbl = _tbl(
            ["Operator", "Records", "Primary Rig Type", "Top Area", "Wells"], rows
        )
        return {"title": "Operator Intelligence", "content": tbl, "charts": ch}

    # S8: Drilling Parameters Summary
    def _s8(self) -> dict:
        d = self._drill
        if d.empty:
            return {
                "title": "Drilling Parameters Summary",
                "content": "<p>No data.</p>",
            }
        wpr = d.groupby(["RIG_NAME", "YEAR"])["API_WELL_NUMBER"].nunique().mean()
        avg_camp = (d.groupby("API_WELL_NUMBER").size() * 7).mean()
        avg_mob = d.groupby("RIG_NAME")["API_WELL_NUMBER"].nunique().mean()
        params = (
            "<ul>"
            f"<li>Wells per rig per year (avg): <strong>{wpr:.1f}</strong></li>"
            f"<li>Average well campaign: <strong>{avg_camp:.0f}</strong> est. days</li>"
            f"<li>Avg unique wells per rig: <strong>{avg_mob:.1f}</strong></li></ul>"
        )
        hhi_tbl = ""
        if self._has_bus:
            ops = d.groupby("BUS_ASC_NAME").size().sort_values(ascending=False).head(10)
            hr: list[list] = []
            for op in ops.index:
                s = d[d["BUS_ASC_NAME"] == op]
                ash = s.groupby("AREA_CODE").size() / len(s)
                hr.append([op, f"{len(s):,}", f"{float((ash**2).sum()):.3f}"])
            hhi_tbl = (
                "<h3>Operator Area Concentration (HHI)</h3>"
                + _tbl(["Operator", "Records", "HHI"], hr)
                + "<p><em>HHI = 1.0 means all activity in one area; "
                "lower = more diversified.</em></p>"
            )
        return {"title": "Drilling Parameters Summary", "content": params + hhi_tbl}

    # S9: Methodology
    def _s9(self, n: int, y0: int, y1: int) -> dict:
        dur_line = (
            "<li><strong>Duration:</strong> actual SPUD&#8594;TD from borehole data</li>"
            if self._enhanced
            else "<li><strong>Duration estimate:</strong> each WAR record ~ 1 week; per-well "
            "duration = record count x 7 days</li>"
        )
        enrich_line = (
            "<li><strong>Enrichment:</strong> enriched with borehole and paleowells data</li>"
            if self._enhanced
            else ""
        )
        return {
            "title": "Methodology",
            "content": "<ul>"
            "<li><strong>Source:</strong> BSEE Well Activity Reports (eWellWARRawData.zip)</li>"
            f"<li><strong>Drilling records:</strong> {n:,} | <strong>Range:</strong> {y0}-{y1}</li>"
            "<li><strong>Classification:</strong> keyword-based rig type from RIG_NAME</li>"
            "<li><strong>Drilling rigs:</strong> drillship, semi-sub, jack-up, platform rig, "
            "tender, barge, submersible</li>"
            + dur_line
            + "<li><strong>Limitations:</strong> BH_TOTAL_MD, DRILLING_MD, DRILLING_TVD are "
            "empty in WAR data; WATER_DEPTH ~11% coverage; WELL_ACTIVITY_CD all NaN</li>"
            + enrich_line
            + "</ul>",
        }

    # SE1: Actual Drilling Duration (enhanced only)
    def _se_duration(self) -> dict:
        eff = self._analysis.get("drilling_efficiency", {})
        mean_d = eff.get("mean_drilling_days", 0.0)
        med_d = eff.get("median_drilling_days", 0.0)
        n = eff.get("total_wells_with_duration", 0)
        stats = (
            f"<p>Actual mean: <strong>{mean_d:.1f}</strong> days | "
            f"Median: <strong>{med_d:.1f}</strong> days | "
            f"Wells: <strong>{n:,}</strong></p>"
            "<p><em>Duration from borehole SPUD to TD dates (not WAR x 7 "
            "estimate).</em></p>"
        )
        by_rt = eff.get("by_rig_type")
        if hasattr(by_rt, "iterrows") and not by_rt.empty:
            rows = [
                [
                    str(r.get("RIG_TYPE", "")),
                    f"{float(r.get('mean_days', 0)):.0f}",
                    f"{float(r.get('median_days', 0)):.0f}",
                    f"{int(r.get('count', 0)):,}",
                ]
                for _, r in by_rt.iterrows()
            ]
            stats += _tbl(["Rig Type", "Mean Days", "Median Days", "Count"], rows)
        return {"title": "Actual Drilling Duration", "content": stats}

    # SE2: Well Depth Analysis (enhanced only)
    def _se_depth(self) -> dict:
        wd = self._analysis.get("well_depth", {})
        mean_md = wd.get("mean_total_md", 0.0)
        max_md = wd.get("max_total_md", 0.0)
        stats = (
            f"<p>Mean total MD: <strong>{mean_md:,.0f}</strong> ft | "
            f"Max total MD: <strong>{max_md:,.0f}</strong> ft</p>"
        )
        by_area = wd.get("by_area")
        if hasattr(by_area, "iterrows") and not by_area.empty:
            rows = [
                [
                    str(r.get("AREA_CODE", "")),
                    f"{float(r.get('mean_md', 0)):,.0f}",
                    f"{float(r.get('max_md', 0)):,.0f}",
                    f"{int(r.get('count', 0)):,}",
                ]
                for _, r in by_area.iterrows()
            ]
            stats += _tbl(["Area", "Mean MD (ft)", "Max MD (ft)", "Count"], rows)
        return {"title": "Well Depth Analysis (Borehole)", "content": stats}

    # SE3: Key Insights (enhanced only)
    def _se_insights(self) -> dict:
        cats = [
            "key_findings",
            "market_trends",
            "competitive_intelligence",
            "opportunity_areas",
            "risk_factors",
        ]
        labels = {
            "key_findings": "Key Findings",
            "market_trends": "Market Trends",
            "competitive_intelligence": "Competitive Intelligence",
            "opportunity_areas": "Opportunity Areas",
            "risk_factors": "Risk Factors",
        }
        body = ""
        for cat in cats:
            items = self._insights.get(cat, [])
            if items:
                body += f"<h3>{labels[cat]}</h3>" + self._bul(items)
        return {
            "title": "Key Insights",
            "content": body if body else "<p>No insights.</p>",
        }

    @staticmethod
    def _bul(items: list[str]) -> str:
        return (
            "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>" if items else ""
        )

    def _html(self, secs: list[dict], n: int, y0: int, y1: int, ts: str) -> str:
        toc, body = "", ""
        for i, s in enumerate(secs, 1):
            aid = f"section-{i}"
            toc += f'<li><a href="#{aid}">{s["title"]}</a></li>'
            body += f'<div class="section" id="{aid}"><h2>{i}. {s["title"]}</h2>'
            for c in s.get("charts", []):
                body += f'<div class="chart-container">{c}</div>'
            body += s.get("content", "") + "</div>"
        return (
            '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1.0">'
            "<title>GOM Drilling Analysis Report</title>"
            '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script><style>'
            "body{font-family:system-ui,-apple-system,sans-serif;margin:0;padding:20px;"
            "background:#fff;color:#1F2937}"
            ".container{max-width:1200px;margin:0 auto}"
            ".header{text-align:center;padding:30px 0;border-bottom:3px solid #1e3a5f}"
            ".header h1{color:#1e3a5f;margin:0 0 8px;font-size:28px}"
            ".header .subtitle{color:#6B7280;font-size:14px}"
            ".back-link{display:inline-block;margin:12px 0;color:#3B82F6;"
            "text-decoration:none;font-size:14px}"
            ".back-link:hover{text-decoration:underline}"
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
            ".data-table{width:100%;border-collapse:collapse;margin:16px 0;font-size:13px}"
            ".data-table th{background:#1e3a5f;color:#fff;padding:8px 12px;text-align:left}"
            ".data-table td{padding:6px 12px;border-bottom:1px solid #E5E7EB}"
            ".data-table tr:nth-child(even){background:#F9FAFB}"
            ".data-table tr:hover{background:#EFF6FF}"
            ".footer{text-align:center;padding:20px 0;margin-top:40px;"
            "border-top:1px solid #E5E7EB;color:#9CA3AF;font-size:12px}"
            "ul{line-height:1.8}p{line-height:1.7}"
            '</style></head><body><div class="container">'
            '<a class="back-link" href="intervention_dashboard.html">'
            "&larr; Back to Main Report</a>"
            '<div class="header">'
            "<h1>GOM Drilling Analysis Report</h1>"
            f'<div class="subtitle">Source: BSEE Well Activity Reports | '
            f"{n:,} drilling records | {y0}-{y1}</div></div>"
            f'<div class="toc"><h3>Table of Contents</h3><ul>{toc}</ul></div>'
            f"{body}"
            f'<div class="footer">Generated {ts} | BSEE WAR Data | worldenergydata pipeline</div>'
            "</div></body></html>"
        )
