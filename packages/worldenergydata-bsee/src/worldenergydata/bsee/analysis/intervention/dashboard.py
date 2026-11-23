"""GOM Intervention Market Intelligence Report (WRK-115 Phase 2).

Produces a comprehensive multi-section HTML report with Plotly charts,
data tables, and narrative text for engineering/intervention services
market intelligence in the Gulf of Mexico.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from worldenergydata.bsee.analysis.intervention.activity_aggregator import (
    WARActivityAggregator,
    classify_activity,
)

_DN: dict[str, str] = {
    "wireline_unit": "Wireline Unit",
    "coil_tubing_unit": "Coil Tubing Unit",
    "lift_boat": "Lift Boat",
    "snubbing_unit": "Snubbing Unit",
    "support_vessel": "Support Vessel",
    "pumping_unit": "Pumping Unit",
    "workover_rig": "Workover Rig",
}
_IT = list(_DN.keys())
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
_DK = ("DECOMMISSION", "ABANDONMENT", "P&A", "PLUG")
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

_SREF = [
    (
        "Wireline Unit",
        "Electric line or slickline operations",
        "Wireline truck/skid, lubricator, sheaves",
        "Well logging, perforation, plug setting, gauge monitoring",
    ),
    (
        "Coil Tubing Unit",
        "Continuous steel tubing operations",
        "CT reel, injector head, BOP stack",
        "Well cleanouts, nitrogen lifts, acid stimulation, sand removal",
    ),
    (
        "Lift Boat",
        "Self-elevating work platform",
        "Jackup-style legs, crane, work deck",
        "Platform access, equipment staging, light well work",
    ),
    (
        "Snubbing Unit",
        "Hydraulic workover under pressure",
        "Snubbing jack, traveling slips, BOP",
        "Live well intervention, tubing changes under pressure",
    ),
    (
        "Support Vessel",
        "Marine support operations",
        "DP vessel, ROV, dive systems",
        "Subsea intervention, dive support, construction",
    ),
    (
        "Workover Rig",
        "Full workover capability",
        "Mast/derrick, drawworks, mud system",
        "Major workovers, recompletions, sidetrack prep",
    ),
    (
        "Pumping Unit",
        "Pressure pumping services",
        "Pump trucks, blender, manifold",
        "Cementing, stimulation, squeeze jobs",
    ),
]
_AREF = [
    ("EI", "Eugene Island", "Shelf", "Central GOM"),
    ("SS", "Ship Shoal", "Shelf", "Central GOM"),
    ("SP", "South Pass", "Shelf", "Central GOM"),
    ("HI", "High Island", "Shelf", "Western GOM"),
    ("SM", "South Marsh Island", "Shelf", "Central GOM"),
    ("WD", "West Delta", "Shelf", "Central GOM"),
    ("VR", "Vermilion", "Shelf", "Central GOM"),
    ("ST", "South Timbalier", "Shelf", "Central GOM"),
    ("MP", "Main Pass", "Shelf", "Central GOM"),
    ("EB", "East Breaks", "Slope", "Western GOM"),
    ("MC", "Mississippi Canyon", "Deepwater", "Central GOM"),
    ("GC", "Green Canyon", "Deepwater", "Central GOM"),
    ("WC", "West Cameron", "Shelf", "Western GOM"),
    ("EC", "East Cameron", "Shelf", "Western GOM"),
    ("GB", "Garden Banks", "Deepwater", "Western GOM"),
    ("VK", "Viosca Knoll", "Deepwater", "Central GOM"),
    ("GI", "Grand Isle", "Shelf", "Central GOM"),
    ("WR", "Walker Ridge", "Ultra-Deepwater", "Central GOM"),
    ("EW", "Ewing Bank", "Slope", "Central GOM"),
    ("MI", "Mustang Island", "Shelf", "Western GOM"),
]
_AL = {r[0]: r[1] for r in _AREF}


def _ybc(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot record counts by [YEAR, ACTIVITY_CATEGORY]."""
    tmp = df.copy()
    tmp["ACTIVITY_CATEGORY"] = tmp["RIG_TYPE"].map(classify_activity)
    tbl = (
        tmp[tmp["ACTIVITY_CATEGORY"].isin(["drilling", "intervention"])]
        .groupby(["YEAR", "ACTIVITY_CATEGORY"])
        .size()
        .unstack(fill_value=0)
    )
    for c in ("drilling", "intervention"):
        if c not in tbl.columns:
            tbl[c] = 0
    return tbl


def _islice(df: pd.DataFrame, lo: int = 2015, hi: int = 2025) -> pd.DataFrame:
    """Filter to intervention records within a year range."""
    return df[
        (df["YEAR"] >= lo)
        & (df["YEAR"] <= hi)
        & (df["RIG_TYPE"].map(classify_activity) == "intervention")
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


def _decom(n: str) -> bool:
    u = str(n).upper()
    return any(k in u for k in _DK)


def _mode(s: pd.Series) -> str:
    m = s.mode()
    return m.iloc[0] if not m.empty else "N/A"


class InterventionDashboard:
    """Generate a comprehensive intervention market intelligence HTML report."""

    def __init__(
        self,
        war_df: pd.DataFrame,
        fleet_df: pd.DataFrame,
        insights: dict | None = None,
    ) -> None:
        self._agg = WARActivityAggregator(war_df, fleet_df)
        enriched = self._agg._join_rig_types()
        self._df = enriched[
            enriched["RIG_NAME"].notna() & enriched["YEAR"].notna()
        ].copy()
        if not self._df.empty:
            self._df["YEAR"] = self._df["YEAR"].astype(int)
        self._has_bus = "BUS_ASC_NAME" in self._df.columns
        self._has_con = "CONTACT_NAME" in self._df.columns
        self._insights = insights
        self._fi = 0

    def generate(
        self,
        output_path: str = "reports/bsee/intervention/intervention_dashboard.html",
    ) -> str:
        """Generate full market intelligence HTML report."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        self._fi = 0
        n = len(self._df)
        y0 = int(self._df["YEAR"].min()) if not self._df.empty else 0
        y1 = int(self._df["YEAR"].max()) if not self._df.empty else 0
        ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        secs = [self._s1(n, y0, y1)]
        if self._insights is not None:
            secs.append(self._s_insights())
        secs.extend(
            [
                self._s2(),
                self._s3(),
                self._s4(),
                self._s5(),
                self._s6(),
                self._s7(),
                self._s8(),
                self._s9(),
                self._s10(n, y0, y1),
            ]
        )
        Path(output_path).write_text(self._html(secs, n, y0, y1, ts), encoding="utf-8")
        return output_path

    def _s1(self, n: int, y0: int, y1: int) -> dict:
        bl = []
        if self._df.empty:
            bl.append(f"Dataset contains {n} records.")
            return {"title": "Executive Summary", "content": self._bul(bl)}
        yy = _ybc(self._df)
        iv = int(yy["intervention"].sum())
        dr = int(yy["drilling"].sum())
        sh = iv / (iv + dr) * 100 if (iv + dr) else 0
        bl.append(
            f"<strong>{n:,}</strong> enriched WAR records spanning "
            f"<strong>{y0}-{y1}</strong>. Intervention = <strong>{sh:.0f}%</strong> "
            f"of classified activity."
        )
        idf = _islice(self._df)
        if not idf.empty:
            svc = idf.groupby("RIG_TYPE").size()
            bl.append(
                f"Top service line: <strong>{_DN.get(svc.idxmax(), svc.idxmax())}</strong>."
            )
        if self._has_bus and not idf.empty:
            bl.append(
                f"Top operator: <strong>{idf.groupby('BUS_ASC_NAME').size().idxmax()}</strong>."
            )
        if not idf.empty:
            aa = idf.groupby("AREA_CODE").size().sort_values(ascending=False).head(3)
            bl.append(
                f"Key areas: <strong>{', '.join(_AL.get(a, a) for a in aa.index)}</strong>."
            )
        return {"title": "Executive Summary", "content": self._bul(bl)}

    def _s_insights(self) -> dict:
        """Key insights summary from Phase 4 pipeline."""
        if not self._insights:
            return {
                "title": "Key Insights",
                "content": "<p><em>Run enhanced pipeline for AI-generated insights.</em></p>",
            }
        bl: list[str] = []
        for category in ["key_findings", "market_trends", "risk_factors"]:
            items = self._insights.get(category, [])
            if items:
                bl.append(f"<h3>{category.replace('_', ' ').title()}</h3>")
                bl.append(
                    "<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"
                )
        content = "\n".join(bl) if bl else "<p>No insights available.</p>"
        return {"title": "Key Insights", "content": content}

    def _s2(self) -> dict:
        ch, nar = [], ""
        if self._df.empty:
            return {
                "title": "Market Structure -- Drilling vs Intervention Shift",
                "content": "<p>No data available.</p>",
                "charts": [],
            }
        yy = _ybc(self._df)
        f1 = go.Figure()
        for cat, clr, fc in [
            ("drilling", _CLR_D, "rgba(59,130,246,0.3)"),
            ("intervention", _CLR_I, "rgba(239,68,68,0.3)"),
        ]:
            f1.add_trace(
                go.Scatter(
                    x=yy.index.tolist(),
                    y=yy[cat].tolist(),
                    name=cat.title(),
                    fill="tozeroy",
                    mode="lines",
                    line=dict(color=clr, width=1.5),
                    fillcolor=fc,
                )
            )
        f1.update_layout(
            title="GOM Has Become an Intervention Basin",
            xaxis_title="Year",
            yaxis_title="WAR Records",
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        ch.append(_fhtml(f1, self._fi))
        self._fi += 1
        y2 = yy[yy.index >= 2000]
        if not y2.empty:
            rat = (y2["intervention"] / y2["drilling"].replace(0, np.nan)).dropna()
            if not rat.empty:
                f2 = go.Figure(
                    go.Scatter(
                        x=rat.index.tolist(),
                        y=rat.values.tolist(),
                        mode="lines+markers",
                        line=dict(color="#6B7280", width=2),
                        marker=dict(
                            size=6, color=["#10B981" if v > 1 else _CLR_I for v in rat]
                        ),
                    )
                )
                f2.add_hline(
                    y=1.0,
                    line_dash="dash",
                    line_color="#9CA3AF",
                    annotation_text="Parity (1.0)",
                )
                f2.update_layout(
                    title="Intervention-to-Drilling Ratio",
                    xaxis_title="Year",
                    yaxis_title="Ratio (Intervention / Drilling)",
                    height=350,
                )
                ch.append(_fhtml(f2, self._fi))
                self._fi += 1
        last = yy.tail(1)
        if not last.empty:
            yr = int(last.index[0])
            iv, dr = int(last["intervention"].iloc[0]), int(last["drilling"].iloc[0])
            nar = (
                f"<p>In {yr}, intervention ({iv:,}) "
                f"{'exceeded' if iv > dr else 'trailed'} drilling ({dr:,}).</p>"
            )
        return {
            "title": "Market Structure -- Drilling vs Intervention Shift",
            "content": nar,
            "charts": ch,
        }

    def _s3(self) -> dict:
        ch = []
        idf = _islice(self._df)
        if idf.empty:
            return {
                "title": "Service Line Analysis",
                "content": "<p>No data 2015-2025.</p>",
                "charts": [],
            }
        cnt = (
            idf[idf["RIG_TYPE"].isin(_IT)]
            .groupby("RIG_TYPE")
            .size()
            .sort_values(ascending=True)
        )
        if not cnt.empty:
            tot = cnt.sum()
            lb = [_DN.get(t, t) for t in cnt.index]
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
                title="Intervention Activity by Service Type (2015-2025)",
                xaxis_title="WAR Records",
                height=400,
                margin=dict(l=160),
            )
            ch.append(_fhtml(f1, self._fi))
            self._fi += 1
        yrs = sorted(idf["YEAR"].unique())
        ya, yb = (2015 if 2015 in yrs else yrs[0]), (2024 if 2024 in yrs else yrs[-1])
        ea = (
            idf[idf["YEAR"] == ya].groupby("RIG_TYPE").size().reindex(_IT, fill_value=0)
        )
        la = (
            idf[idf["YEAR"] == yb].groupby("RIG_TYPE").size().reindex(_IT, fill_value=0)
        )
        lg = [_DN.get(t, t) for t in _IT]
        f2 = go.Figure()
        f2.add_trace(go.Bar(x=lg, y=ea.values, name=str(ya), marker_color=_CLR_D))
        f2.add_trace(go.Bar(x=lg, y=la.values, name=str(yb), marker_color=_CLR_I))
        f2.update_layout(
            title=f"Service Type Growth: {ya} vs {yb}",
            barmode="group",
            yaxis_title="WAR Records",
            height=400,
        )
        ch.append(_fhtml(f2, self._fi))
        self._fi += 1
        ref = _tbl(
            ["Service Type", "Description", "Typical Equipment", "Use Case"],
            [list(r) for r in _SREF],
        )
        return {
            "title": "Service Line Analysis",
            "content": "<h3>Service Type Reference</h3>" + ref,
            "charts": ch,
        }

    def _s4(self) -> dict:
        ch = []
        if not self._has_bus or self._df.empty:
            return {
                "title": "Operator & Client Intelligence",
                "content": "<p>No operator data.</p>",
                "charts": [],
            }
        idf = _islice(self._df, 2020, 2025)
        if idf.empty:
            return {
                "title": "Operator & Client Intelligence",
                "content": "<p>No records 2020-2025.</p>",
                "charts": [],
            }
        top = idf.groupby("BUS_ASC_NAME").size().sort_values(ascending=True).tail(20)
        clr = ["#F59E0B" if _decom(n) else _CLR_I for n in top.index]
        f1 = go.Figure(
            go.Bar(
                y=top.index.tolist(),
                x=top.values,
                orientation="h",
                marker_color=clr,
                text=[f"{v:,}" for v in top.values],
                textposition="outside",
            )
        )
        f1.update_layout(
            title="Top Operators Using Intervention Services (2020-2025)",
            xaxis_title="Intervention Records",
            height=600,
            margin=dict(l=250),
        )
        ch.append(_fhtml(f1, self._fi))
        self._fi += 1
        rows = []
        for op in reversed(top.index):
            s = idf[idf["BUS_ASC_NAME"] == op]
            si = s[s["RIG_TYPE"].isin(_IT)]
            ps = (
                _DN.get(_mode(si["RIG_TYPE"]), _mode(si["RIG_TYPE"]))
                if not si.empty
                else "N/A"
            )
            rows.append(
                [
                    op,
                    f"{len(s):,}",
                    ps,
                    _mode(s["AREA_CODE"]),
                    "Yes" if _decom(op) else "No",
                ]
            )
        t = _tbl(["Operator", "Records", "Primary Service", "Top Area", "Decom"], rows)
        return {"title": "Operator & Client Intelligence", "content": t, "charts": ch}

    def _s5(self) -> dict:
        ch = []
        idf = _islice(self._df, 2020, 2025)
        if idf.empty:
            return {
                "title": "Equipment & Service Vendors",
                "content": "<p>No data.</p>",
                "charts": [],
            }
        eq = idf.groupby("RIG_NAME").size().sort_values(ascending=True).tail(20)
        f1 = go.Figure(
            go.Bar(
                y=eq.index.tolist(),
                x=eq.values,
                orientation="h",
                marker_color=_CLR_I,
                text=[f"{v:,}" for v in eq.values],
                textposition="outside",
            )
        )
        f1.update_layout(
            title="Top Intervention Equipment Units (2020-2025)",
            xaxis_title="WAR Records",
            height=600,
            margin=dict(l=250),
        )
        ch.append(_fhtml(f1, self._fi))
        self._fi += 1
        top30 = idf.groupby("RIG_NAME").size().sort_values(ascending=False).head(30)
        rows = []
        for rig in top30.index:
            s = idf[idf["RIG_NAME"] == rig]
            rt = _DN.get(_mode(s["RIG_TYPE"]), _mode(s["RIG_TYPE"]))
            to = _mode(s["BUS_ASC_NAME"]) if self._has_bus else "N/A"
            rows.append([rig, rt, f"{len(s):,}", to, _mode(s["AREA_CODE"])])
        t = _tbl(["Equipment", "Type", "Records", "Top Operator", "Top Area"], rows)
        return {"title": "Equipment & Service Vendors", "content": t, "charts": ch}

    def _s6(self) -> dict:
        idf = _islice(self._df, 2020, 2025)
        if not self._has_con or idf.empty:
            return {
                "title": "Contact Intelligence",
                "content": "<p><em>Contact data (CONTACT_NAME) not available.</em></p>",
            }
        cts = idf.groupby("CONTACT_NAME").size().sort_values(ascending=False).head(30)
        rows = []
        for nm in cts.index:
            s = idf[idf["CONTACT_NAME"] == nm]
            po = _mode(s["BUS_ASC_NAME"]) if self._has_bus else "N/A"
            si = s[s["RIG_TYPE"].isin(_IT)]
            ps = (
                _DN.get(_mode(si["RIG_TYPE"]), _mode(si["RIG_TYPE"]))
                if not si.empty
                else "N/A"
            )
            rows.append([nm, f"{len(s):,}", po, ps])
        t = _tbl(
            ["Contact Name", "Records", "Primary Operator", "Primary Service"], rows
        )
        note = "<p><em>Contacts are BSEE-reported field representatives.</em></p>"
        return {"title": "Contact Intelligence", "content": t + note}

    def _s7(self) -> dict:
        ch = []
        idf = _islice(self._df)
        if idf.empty:
            return {
                "title": "Geographic Market Intelligence",
                "content": "<p>No data.</p>",
                "charts": [],
            }
        cnt = idf.groupby("AREA_CODE").size().sort_values(ascending=True).tail(15)
        tot = cnt.sum()
        lb = [
            f"{c} - {_AL.get(c, c)} ({v/tot*100:.1f}%)"
            for c, v in zip(cnt.index, cnt.values)
        ]
        f1 = go.Figure(
            go.Bar(
                y=lb,
                x=cnt.values,
                orientation="h",
                marker_color=(_PAL * 3)[: len(lb)],
                text=[f"{v:,}" for v in cnt.values],
                textposition="outside",
            )
        )
        f1.update_layout(
            title="Intervention Activity by GOM Area (2015-2025)",
            xaxis_title="Intervention Records",
            height=500,
            margin=dict(l=300),
        )
        ch.append(_fhtml(f1, self._fi))
        self._fi += 1
        ref = _tbl(
            ["Code", "Area Name", "Water Depth", "Region"], [list(r) for r in _AREF]
        )
        return {
            "title": "Geographic Market Intelligence",
            "content": "<h3>GOM Area Code Reference</h3>" + ref,
            "charts": ch,
        }

    def _s8(self) -> dict:
        ch, nar = [], ""
        idf = _islice(self._df)
        if idf.empty:
            return {
                "title": "Addressable Market",
                "content": "<p>No data.</p>",
                "charts": [],
            }
        by = idf.groupby("YEAR").agg(
            w=("API_WELL_NUMBER", "nunique"), l=("BOTM_LEASE_NUM", "nunique")
        )
        f1 = go.Figure()
        f1.add_trace(
            go.Scatter(
                x=by.index.tolist(),
                y=by["w"].tolist(),
                mode="lines+markers",
                name="Unique Wells",
                line=dict(color=_CLR_D, width=2),
            )
        )
        f1.add_trace(
            go.Scatter(
                x=by.index.tolist(),
                y=by["l"].tolist(),
                mode="lines+markers",
                name="Unique Leases",
                line=dict(color="#10B981", width=2, dash="dash"),
                yaxis="y2",
            )
        )
        f1.update_layout(
            title="Addressable Market: Wells & Leases Requiring Intervention",
            xaxis_title="Year",
            yaxis=dict(title="Unique Wells"),
            yaxis2=dict(title="Unique Leases", overlaying="y", side="right"),
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        ch.append(_fhtml(f1, self._fi))
        self._fi += 1
        isea = _islice(self._df, 2020, 2025).copy()
        if not isea.empty and "WAR_START_DT" in isea.columns:
            dt = pd.to_datetime(
                isea["WAR_START_DT"], format="mixed", dayfirst=False, errors="coerce"
            )
            isea["MONTH"] = dt.dt.month
            isea = isea[isea["MONTH"].notna()]
            if not isea.empty:
                mo = isea.groupby("MONTH").size().reindex(range(1, 13), fill_value=0)
                avg = mo.mean()
                if avg > 0:
                    ix = mo / avg
                    th = _MO + [_MO[0]]
                    rv = list(ix.values) + [float(ix.values[0])]
                    f2 = go.Figure(
                        go.Scatterpolar(
                            r=rv,
                            theta=th,
                            fill="toself",
                            fillcolor="rgba(59,130,246,0.15)",
                            line=dict(color=_CLR_D, width=2),
                        )
                    )
                    f2.update_layout(
                        title="Seasonal Intervention Activity Index",
                        height=400,
                        polar=dict(radialaxis=dict(tickfont=dict(size=9))),
                    )
                    ch.append(_fhtml(f2, self._fi))
                    self._fi += 1
        aw, al = int(by["w"].mean()), int(by["l"].mean())
        nar = (
            f"<p>On average, <strong>{aw:,}</strong> unique wells across "
            f"<strong>{al:,}</strong> leases require intervention annually.</p>"
        )
        return {"title": "Addressable Market", "content": nar, "charts": ch}

    def _s9(self) -> dict:
        idf, idr = _islice(self._df), _islice(self._df, 2020, 2025)
        ti = len(idf)
        p = []
        # 9.1
        wl = len(idf[idf["RIG_TYPE"] == "wireline_unit"]) if not idf.empty else 0
        wp = wl / ti * 100 if ti else 0
        ww = (
            idf[idf["RIG_TYPE"] == "wireline_unit"]["API_WELL_NUMBER"].nunique()
            if not idf.empty
            else 0
        )
        p.append(
            f"<h3>9.1 Well Intervention Engineering</h3>"
            f"<p>Wireline program design, CT job planning, snubbing engineering. "
            f"Wireline = <strong>{wp:.0f}%</strong> of intervention, "
            f"<strong>{ww:,}</strong> unique wells.</p>"
        )
        # 9.2
        dp = 0.0
        if self._has_bus and not idr.empty:
            dp = idr["BUS_ASC_NAME"].apply(_decom).sum() / len(idr) * 100
        p.append(
            f"<h3>9.2 Decommissioning &amp; P&amp;A Engineering</h3>"
            f"<p>P&amp;A program management, well abandonment engineering. "
            f"Decom operators = <strong>{dp:.1f}%</strong> of recent activity.</p>"
        )
        # 9.3
        mt = {"lift_boat", "support_vessel"}
        mc = len(idf[idf["RIG_TYPE"].isin(mt)]) if not idf.empty else 0
        mp = mc / ti * 100 if ti else 0
        an = []
        if not idf.empty:
            ma = idf[idf["RIG_TYPE"].isin(mt)].groupby("AREA_CODE").size()
            an = [_AL.get(a, a) for a in ma.sort_values(ascending=False).head(3).index]
        p.append(
            f"<h3>9.3 Marine &amp; Logistics Coordination</h3>"
            f"<p>Lift boat + support vessel = <strong>{mp:.0f}%</strong> of "
            f"intervention in <strong>{', '.join(an) if an else 'N/A'}</strong>.</p>"
        )
        # 9.4
        yw = (
            idf.groupby("YEAR")["API_WELL_NUMBER"].nunique().mean()
            if not idf.empty
            else 0
        )
        yl = (
            idf.groupby("YEAR")["BOTM_LEASE_NUM"].nunique().mean()
            if not idf.empty
            else 0
        )
        p.append(
            f"<h3>9.4 Asset Integrity &amp; Well Surveillance</h3>"
            f"<p><strong>{int(yw):,}</strong> wells / <strong>{int(yl):,}</strong> "
            f"leases annually require intervention.</p>"
        )
        # 9.5
        sp = (
            int(self._df["YEAR"].max()) - int(self._df["YEAR"].min()) + 1
            if not self._df.empty
            else 0
        )
        p.append(
            f"<h3>9.5 Data Analytics &amp; Decision Support</h3>"
            f"<p>Dataset: <strong>{sp}</strong> years, <strong>{len(self._df):,}"
            f"</strong> records for trend analysis.</p>"
        )
        return {
            "title": "Engineering Marketing Services Opportunities",
            "content": "\n".join(p),
        }

    def _s10(self, n: int, y0: int, y1: int) -> dict:
        return {
            "title": "Methodology & Data Dictionary",
            "content": "<ul>"
            "<li><strong>Source:</strong> BSEE Well Activity Reports (eWellWARRawData.zip)</li>"
            f"<li><strong>Records:</strong> {n:,} | <strong>Range:</strong> {y0}-{y1}</li>"
            "<li><strong>Classification:</strong> keyword-based rig type from RIG_NAME</li>"
            "<li><strong>Categories:</strong> Drilling (drillship, semi-sub, jack-up, "
            "platform rig, tender, barge, submersible) vs Intervention (wireline, CT, "
            "lift boat, snubbing, support vessel, workover rig, pumping)</li>"
            "<li><strong>Limitations:</strong> generic entries aggregate multiple units; "
            "operator names may vary across filings</li></ul>",
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
            "<title>GOM Intervention Market Intelligence Report</title>"
            '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script><style>'
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
            ".data-table{width:100%;border-collapse:collapse;margin:16px 0;font-size:13px}"
            ".data-table th{background:#1e3a5f;color:#fff;padding:8px 12px;text-align:left}"
            ".data-table td{padding:6px 12px;border-bottom:1px solid #E5E7EB}"
            ".data-table tr:nth-child(even){background:#F9FAFB}"
            ".data-table tr:hover{background:#EFF6FF}"
            ".footer{text-align:center;padding:20px 0;margin-top:40px;"
            "border-top:1px solid #E5E7EB;color:#9CA3AF;font-size:12px}"
            "ul{line-height:1.8}p{line-height:1.7}"
            '</style></head><body><div class="container">'
            '<div class="header">'
            "<h1>GOM Intervention &amp; Workover Services &mdash; Market Intelligence Report</h1>"
            f'<div class="subtitle">Source: BSEE Well Activity Reports | {n:,} records | {y0}-{y1}</div>'  # noqa: E501
            "</div>"
            f'<div class="toc"><h3>Table of Contents</h3><ul>{toc}</ul></div>'
            '<div class="related-reports" style="background:#EFF6FF;border:1px solid #3B82F6;'
            "border-radius:6px;padding:16px 24px;margin:16px 0;display:flex;gap:24px;"
            'align-items:center"><strong style="color:#1e3a5f">Related Reports:</strong>'
            '<a href="drilling_analysis.html" style="color:#3B82F6;text-decoration:none;'
            'font-weight:500">Drilling Analysis Report &rarr;</a>'
            '<a href="intervention_by_service.html" style="color:#EF4444;text-decoration:none;'
            'font-weight:500">Intervention by Service Type &rarr;</a></div>'
            f"{body}"
            f'<div class="footer">Generated {ts} | BSEE WAR Data | worldenergydata pipeline</div>'
            "</div></body></html>"
        )
