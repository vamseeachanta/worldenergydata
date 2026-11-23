"""GOM Intervention by Service Type -- Detail Report (WRK-115).

Produces a multi-section HTML report with Plotly charts breaking down
intervention activity by each of the 7 service types.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from worldenergydata.bsee.analysis.intervention.activity_aggregator import (
    WARActivityAggregator,
    classify_activity,
)

_SVC_DN: dict[str, str] = {
    "wireline_unit": "Wireline Unit",
    "coil_tubing_unit": "Coil Tubing Unit",
    "lift_boat": "Lift Boat",
    "snubbing_unit": "Snubbing Unit",
    "workover_rig": "Workover Rig",
    "support_vessel": "Support Vessel",
    "pumping_unit": "Pumping Unit",
}
_SVC_TYPES = list(_SVC_DN.keys())
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
_AN: dict[str, str] = {
    "EI": "Eugene Island",
    "SS": "Ship Shoal",
    "SP": "South Pass",
    "HI": "High Island",
    "SM": "South Marsh Island",
    "WD": "West Delta",
    "VR": "Vermilion",
    "ST": "South Timbalier",
    "MP": "Main Pass",
    "MC": "Mississippi Canyon",
    "GC": "Green Canyon",
    "WC": "West Cameron",
    "EC": "East Cameron",
    "GB": "Garden Banks",
    "VK": "Viosca Knoll",
    "GI": "Grand Isle",
    "WR": "Walker Ridge",
    "EW": "Ewing Bank",
    "MI": "Mustang Island",
    "EB": "East Breaks",
}
_MO = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]
_WK = 7  # Each WAR record ~ 1 week


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


def _bul(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>" if items else ""


def _mode(s: pd.Series) -> str:
    m = s.mode()
    return str(m.iloc[0]) if not m.empty else "N/A"


def _ivf(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to intervention records only."""
    if df.empty:
        return df
    return df[df["RIG_TYPE"].map(classify_activity) == "intervention"].copy()


def _camp(sub: pd.DataFrame) -> float:
    """Avg campaign duration (records * 7 days) per well."""
    if sub.empty or "API_WELL_NUMBER" not in sub.columns:
        return 0.0
    grp = sub.groupby("API_WELL_NUMBER").size()
    return float((grp * _WK).mean()) if not grp.empty else 0.0


def _yoy(sub: pd.DataFrame) -> str:
    """YoY growth rate string for latest 2 years."""
    if sub.empty or "YEAR" not in sub.columns:
        return "N/A"
    yc = sub.groupby("YEAR").size().sort_index()
    if len(yc) < 2:
        return "N/A"
    prev, cur = int(yc.iloc[-2]), int(yc.iloc[-1])
    return f"{(cur - prev) / prev * 100:+.1f}%" if prev else "N/A"


class InterventionDetailReport:
    """Generate an intervention-by-service-type HTML report."""

    def __init__(self, war_df: pd.DataFrame, fleet_df: pd.DataFrame) -> None:
        self._agg = WARActivityAggregator(war_df, fleet_df)
        enriched = self._agg._join_rig_types()
        self._df = enriched[
            enriched["RIG_NAME"].notna() & enriched["YEAR"].notna()
        ].copy()
        if not self._df.empty:
            self._df["YEAR"] = self._df["YEAR"].astype(int)
        self._hb = "BUS_ASC_NAME" in self._df.columns
        self._fi = 0

    def generate(
        self,
        output_path: str = "reports/bsee/intervention/intervention_by_service.html",
    ) -> str:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        self._fi = 0
        iv = _ivf(self._df)
        n = len(iv)
        y0 = int(iv["YEAR"].min()) if not iv.empty else 0
        y1 = int(iv["YEAR"].max()) if not iv.empty else 0
        ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        secs = [
            self._s1(iv, n, y0, y1),
            self._s2(iv),
            self._s3(iv),
            self._s4(iv),
            self._s5(iv),
            self._s6(iv),
            self._s7(iv),
            self._s8(iv),
            self._s9(n, y0, y1),
        ]
        Path(output_path).write_text(self._html(secs, n, y0, y1, ts), encoding="utf-8")
        return output_path

    # S1: Executive Summary
    def _s1(self, iv: pd.DataFrame, n: int, y0: int, y1: int) -> dict:
        bl: list[str] = []
        if iv.empty:
            bl.append("No intervention records found.")
            return {"title": "Executive Summary", "content": _bul(bl)}
        bl.append(
            f"<strong>{n:,}</strong> intervention WAR records spanning "
            f"<strong>{y0}-{y1}</strong>."
        )
        bl.append(
            f"Unique wells served: <strong>{iv['API_WELL_NUMBER'].nunique():,}</strong>."
        )
        if self._hb:
            bl.append(
                f"Unique operators: <strong>{iv['BUS_ASC_NAME'].nunique():,}</strong>."
            )
        ch: list[str] = []
        cnt = iv.groupby("RIG_TYPE").size().reindex(_SVC_TYPES, fill_value=0)
        lbl = [_SVC_DN.get(t, t) for t in cnt.index]
        fig = go.Figure(
            go.Pie(
                labels=lbl,
                values=cnt.values.tolist(),
                marker=dict(colors=_PAL[: len(lbl)]),
                textinfo="label+percent",
                hole=0.35,
            )
        )
        fig.update_layout(title="Intervention Records by Service Type", height=400)
        ch.append(_fhtml(fig, self._fi))
        self._fi += 1
        return {"title": "Executive Summary", "content": _bul(bl), "charts": ch}

    # S2: Service Type Deep-Dive
    def _s2(self, iv: pd.DataFrame) -> dict:
        parts: list[str] = []
        ch: list[str] = []
        if iv.empty:
            return {
                "title": "Service Type Deep-Dive",
                "content": "<p>No data.</p>",
                "charts": [],
            }
        for i, (sk, sn) in enumerate(_SVC_DN.items()):
            sub = iv[iv["RIG_TYPE"] == sk]
            parts.append(f"<h3>2.{i + 1} {sn}</h3>")
            nr = len(sub)
            if nr == 0:
                parts.append("<p>No records for this service type.</p>")
                continue
            nw = sub["API_WELL_NUMBER"].nunique()
            nl = sub["BOTM_LEASE_NUM"].nunique()
            nop = sub["BUS_ASC_NAME"].nunique() if self._hb else 0
            parts.append(
                f"<p>Records: <strong>{nr:,}</strong> | "
                f"Wells: <strong>{nw:,}</strong> | "
                f"Leases: <strong>{nl:,}</strong> | "
                f"Operators: <strong>{nop:,}</strong> | "
                f"Avg campaign: <strong>{_camp(sub):.0f} days</strong> | "
                f"YoY growth: <strong>{_yoy(sub)}</strong></p>"
            )
            yc = sub.groupby("YEAR").size().sort_index()
            fig = go.Figure(
                go.Scatter(
                    x=yc.index.tolist(),
                    y=yc.values.tolist(),
                    mode="lines+markers",
                    line=dict(color=_PAL[i % len(_PAL)], width=2),
                )
            )
            fig.update_layout(
                title=f"{sn} -- Activity Trend",
                xaxis_title="Year",
                yaxis_title="WAR Records",
                height=300,
            )
            ch.append(_fhtml(fig, self._fi))
            self._fi += 1
            if self._hb:
                top_op = (
                    sub.groupby("BUS_ASC_NAME")
                    .size()
                    .sort_values(ascending=False)
                    .head(5)
                )
                parts.append(
                    _tbl(
                        ["Operator", "Records"],
                        [[op, f"{c:,}"] for op, c in top_op.items()],
                    )
                )
            top_rig = (
                sub.groupby("RIG_NAME").size().sort_values(ascending=False).head(5)
            )
            parts.append(
                _tbl(
                    ["Equipment", "Records"],
                    [[r, f"{c:,}"] for r, c in top_rig.items()],
                )
            )
            top_area = (
                sub.groupby("AREA_CODE").size().sort_values(ascending=False).head(5)
            )
            parts.append(
                _tbl(
                    ["Area", "Records"],
                    [[f"{a} - {_AN.get(a, a)}", f"{c:,}"] for a, c in top_area.items()],
                )
            )
        return {
            "title": "Service Type Deep-Dive",
            "content": "\n".join(parts),
            "charts": ch,
        }

    # S3: Service Type Comparison
    def _s3(self, iv: pd.DataFrame) -> dict:
        ch: list[str] = []
        if iv.empty:
            return {
                "title": "Service Type Comparison",
                "content": "<p>No data.</p>",
                "charts": [],
            }
        yrs = sorted(iv["YEAR"].unique())
        ya = 2020 if 2020 in yrs else yrs[0]
        yb = yrs[-1]
        ea = (
            iv[iv["YEAR"] == ya]
            .groupby("RIG_TYPE")
            .size()
            .reindex(_SVC_TYPES, fill_value=0)
        )
        la = (
            iv[iv["YEAR"] == yb]
            .groupby("RIG_TYPE")
            .size()
            .reindex(_SVC_TYPES, fill_value=0)
        )
        lbl = [_SVC_DN[t] for t in _SVC_TYPES]
        fig = go.Figure()
        fig.add_trace(
            go.Bar(x=lbl, y=ea.values.tolist(), name=str(ya), marker_color=_PAL[0])
        )
        fig.add_trace(
            go.Bar(x=lbl, y=la.values.tolist(), name=str(yb), marker_color=_PAL[1])
        )
        fig.update_layout(
            title=f"Records by Service Type: {ya} vs {yb}",
            barmode="group",
            yaxis_title="WAR Records",
            height=400,
        )
        ch.append(_fhtml(fig, self._fi))
        self._fi += 1
        rows: list[list] = []
        for sk in _SVC_TYPES:
            sub = iv[iv["RIG_TYPE"] == sk]
            nr = len(sub)
            nw = sub["API_WELL_NUMBER"].nunique() if nr else 0
            nop = sub["BUS_ASC_NAME"].nunique() if (self._hb and nr) else 0
            ta = _mode(sub["AREA_CODE"]) if nr else "N/A"
            rows.append(
                [
                    _SVC_DN[sk],
                    f"{nr:,}",
                    f"{nw:,}",
                    f"{nop:,}",
                    f"{_camp(sub):.0f}",
                    _AN.get(ta, ta),
                    _yoy(sub),
                ]
            )
        content = _tbl(
            [
                "Service Type",
                "Total Records",
                "Unique Wells",
                "Unique Operators",
                "Avg Campaign Days",
                "Top Area",
                "Growth Rate",
            ],
            rows,
        )
        return {"title": "Service Type Comparison", "content": content, "charts": ch}

    # S4: Geographic Distribution by Service Type
    def _s4(self, iv: pd.DataFrame) -> dict:
        ch: list[str] = []
        if iv.empty:
            return {
                "title": "Geographic Distribution by Service Type",
                "content": "<p>No data.</p>",
                "charts": [],
            }
        ta = (
            iv.groupby("AREA_CODE")
            .size()
            .sort_values(ascending=False)
            .head(12)
            .index.tolist()
        )
        al = [f"{a} - {_AN.get(a, a)}" for a in ta]
        fig = go.Figure()
        for i, sk in enumerate(_SVC_TYPES):
            ac = (
                iv[iv["RIG_TYPE"] == sk]
                .groupby("AREA_CODE")
                .size()
                .reindex(ta, fill_value=0)
            )
            fig.add_trace(
                go.Bar(
                    x=al,
                    y=ac.values.tolist(),
                    name=_SVC_DN[sk],
                    marker_color=_PAL[i % len(_PAL)],
                )
            )
        fig.update_layout(
            title="Service Type Distribution Across GOM Areas",
            barmode="stack",
            yaxis_title="WAR Records",
            height=450,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        ch.append(_fhtml(fig, self._fi))
        self._fi += 1
        return {
            "title": "Geographic Distribution by Service Type",
            "content": "",
            "charts": ch,
        }

    # S5: Operator-Service Matrix
    def _s5(self, iv: pd.DataFrame) -> dict:
        ch: list[str] = []
        if not self._hb or iv.empty:
            return {
                "title": "Operator-Service Matrix",
                "content": "<p>No operator data.</p>",
                "charts": [],
            }
        ops = (
            iv.groupby("BUS_ASC_NAME")
            .size()
            .sort_values(ascending=False)
            .head(15)
            .index.tolist()
        )
        sl = [_SVC_DN[s] for s in _SVC_TYPES]
        z = [
            [
                int(((iv["BUS_ASC_NAME"] == op) & (iv["RIG_TYPE"] == sk)).sum())
                for sk in _SVC_TYPES
            ]
            for op in ops
        ]
        fig = go.Figure(
            go.Heatmap(z=z, x=sl, y=ops, colorscale="Blues", texttemplate="%{z}")
        )
        fig.update_layout(
            title="Operator-Service Matrix (Top 15 Operators)",
            height=max(400, 30 * len(ops) + 100),
            yaxis=dict(autorange="reversed"),
        )
        ch.append(_fhtml(fig, self._fi))
        self._fi += 1
        return {"title": "Operator-Service Matrix", "content": "", "charts": ch}

    # S6: Seasonal Patterns by Service Type
    def _s6(self, iv: pd.DataFrame) -> dict:
        ch: list[str] = []
        if iv.empty or "WAR_START_DT" not in iv.columns:
            return {
                "title": "Seasonal Patterns by Service Type",
                "content": "<p>No data.</p>",
                "charts": [],
            }
        tmp = iv.copy()
        tmp["MONTH"] = pd.to_datetime(
            tmp["WAR_START_DT"], format="mixed", dayfirst=False, errors="coerce"
        ).dt.month
        tmp = tmp[tmp["MONTH"].notna()]
        if tmp.empty:
            return {
                "title": "Seasonal Patterns by Service Type",
                "content": "<p>No parseable dates.</p>",
                "charts": [],
            }
        fig = go.Figure()
        for i, sk in enumerate(_SVC_TYPES):
            sub = tmp[tmp["RIG_TYPE"] == sk]
            if sub.empty:
                continue
            mc = sub.groupby("MONTH").size().reindex(range(1, 13), fill_value=0)
            fig.add_trace(
                go.Bar(
                    x=_MO,
                    y=mc.values.tolist(),
                    name=_SVC_DN[sk],
                    marker_color=_PAL[i % len(_PAL)],
                )
            )
        fig.update_layout(
            title="Monthly Distribution by Service Type",
            barmode="group",
            yaxis_title="WAR Records",
            height=420,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        ch.append(_fhtml(fig, self._fi))
        self._fi += 1
        rows: list[list] = []
        for sk in _SVC_TYPES:
            sub = tmp[tmp["RIG_TYPE"] == sk]
            if sub.empty:
                rows.append([_SVC_DN[sk], "N/A"])
                continue
            pk = int(sub.groupby("MONTH").size().idxmax())
            rows.append([_SVC_DN[sk], _MO[pk - 1]])
        return {
            "title": "Seasonal Patterns by Service Type",
            "content": _tbl(["Service Type", "Peak Month"], rows),
            "charts": ch,
        }

    # S7: Duration Analysis by Service Type
    def _s7(self, iv: pd.DataFrame) -> dict:
        ch: list[str] = []
        if iv.empty:
            return {
                "title": "Duration Analysis by Service Type",
                "content": "<p>No data.</p>",
                "charts": [],
            }
        fig = go.Figure()
        rows: list[list] = []
        for i, sk in enumerate(_SVC_TYPES):
            sub = iv[iv["RIG_TYPE"] == sk]
            if sub.empty:
                rows.append([_SVC_DN[sk], "0", "0", "0", "0"])
                continue
            dur = sub.groupby("API_WELL_NUMBER").size() * _WK
            fig.add_trace(
                go.Box(
                    y=dur.values.tolist(),
                    name=_SVC_DN[sk],
                    marker_color=_PAL[i % len(_PAL)],
                )
            )
            rows.append(
                [
                    _SVC_DN[sk],
                    f"{dur.median():.0f}",
                    f"{dur.mean():.0f}",
                    f"{dur.max():.0f}",
                    f"{dur.count():,}",
                ]
            )
        fig.update_layout(
            title="Well Campaign Duration by Service Type",
            yaxis_title="Estimated Days",
            height=420,
        )
        ch.append(_fhtml(fig, self._fi))
        self._fi += 1
        return {
            "title": "Duration Analysis by Service Type",
            "content": _tbl(
                [
                    "Service Type",
                    "Median Days",
                    "Mean Days",
                    "Max Days",
                    "Wells Served",
                ],
                rows,
            ),
            "charts": ch,
        }

    # S8: Market Share Trends
    def _s8(self, iv: pd.DataFrame) -> dict:
        ch: list[str] = []
        if iv.empty:
            return {
                "title": "Market Share Trends",
                "content": "<p>No data.</p>",
                "charts": [],
            }
        yrs = sorted(iv["YEAR"].unique())
        # pre-compute yearly totals
        ytot = {yr: len(iv[iv["YEAR"] == yr]) for yr in yrs}
        fig = go.Figure()
        for i, sk in enumerate(_SVC_TYPES):
            vals = [
                (
                    len(iv[(iv["YEAR"] == yr) & (iv["RIG_TYPE"] == sk)])
                    / ytot[yr]
                    * 100
                    if ytot[yr]
                    else 0
                )
                for yr in yrs
            ]
            fig.add_trace(
                go.Scatter(
                    x=[int(y) for y in yrs],
                    y=vals,
                    name=_SVC_DN[sk],
                    stackgroup="one",
                    line=dict(color=_PAL[i % len(_PAL)]),
                )
            )
        fig.update_layout(
            title="Market Share by Service Type Over Time",
            xaxis_title="Year",
            yaxis_title="Share (%)",
            height=420,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        ch.append(_fhtml(fig, self._fi))
        self._fi += 1
        recent = yrs[-min(5, len(yrs)) :]
        hdr = ["Service Type"] + [str(int(y)) for y in recent]
        rows: list[list] = []
        for sk in _SVC_TYPES:
            row: list[str] = [_SVC_DN[sk]]
            for yr in recent:
                n = len(iv[(iv["YEAR"] == yr) & (iv["RIG_TYPE"] == sk)])
                row.append(f"{n / ytot[yr] * 100:.1f}%" if ytot[yr] else "0.0%")
            rows.append(row)
        return {
            "title": "Market Share Trends",
            "content": _tbl(hdr, rows),
            "charts": ch,
        }

    # S9: Methodology
    def _s9(self, n: int, y0: int, y1: int) -> dict:
        return {
            "title": "Methodology",
            "content": "<ul>"
            "<li><strong>Source:</strong> BSEE Well Activity Reports (eWellWARRawData.zip)</li>"
            f"<li><strong>Intervention Records:</strong> {n:,} | "
            f"<strong>Range:</strong> {y0}-{y1}</li>"
            "<li><strong>Classification:</strong> keyword-based rig type from RIG_NAME "
            "via <code>classify_rig_type()</code></li>"
            "<li><strong>Service Types:</strong> wireline, coil tubing, lift boat, "
            "snubbing, support vessel, workover rig, pumping</li>"
            "<li><strong>Duration Estimate:</strong> records per well &times; 7 days "
            "(WAR records are weekly)</li>"
            "<li><strong>Limitations:</strong> generic entries may aggregate multiple "
            "units; operator names may vary; duration estimated from record counts</li>"
            "</ul>",
        }

    # HTML shell
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
            "<title>GOM Intervention by Service Type</title>"
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
            "<h1>GOM Intervention by Service Type &mdash; Detail Report</h1>"
            f'<div class="subtitle">Source: BSEE Well Activity Reports | '
            f"{n:,} intervention records | {y0}-{y1}</div></div>"
            f'<div class="toc"><h3>Table of Contents</h3><ul>{toc}</ul></div>'
            f"{body}"
            f'<div class="footer">Generated {ts} | BSEE WAR Data | '
            f"worldenergydata pipeline</div></div></body></html>"
        )
