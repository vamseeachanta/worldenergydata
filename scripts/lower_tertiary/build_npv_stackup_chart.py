#!/usr/bin/env python3
"""Build an interactive Plotly waterfall of a field's well-level NPV stackup.

The per-well net NPVs sum exactly to the field NPV, so a waterfall is the
natural picture: start at zero, step by each well's net contribution, land on
the field total. Hover carries the gross/allocated breakdown behind each net
bar.

Like ``build_portfolio_html.py``, this PARSES the already-generated field
markdown report (``reports/lower_tertiary/field_economics_<slug>.md``) rather
than recomputing the model — so it is fast and needs no BSEE data on disk.

Usage::

    uv run --with plotly python scripts/lower_tertiary/build_npv_stackup_chart.py --dev Julia
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports" / "lower_tertiary"

# A data row of the "Well-Level NPV Stackup" table:
# | rank | api | name | oil | gross | allocated | net | pct |
_ROW = re.compile(
    r"^\|\s*\d+\s*\|\s*(?P<api>\d+)\s*\|\s*(?P<name>[^|]+?)\s*\|"
    r"\s*(?P<oil>[-\d,.]+)\s*\|\s*(?P<gross>[-\d,.]+)\s*\|"
    r"\s*(?P<alloc>[-\d,.]+)\s*\|\s*(?P<net>[-\d,.]+)\s*\|"
    r"\s*(?P<pct>[-\d,.]+)%\s*\|\s*$"
)
_FIELD_NPV = re.compile(r"Field NPV = \*\*\$(?P<v>[-\d,.]+) M\*\*")


def _f(s: str) -> float:
    return float(s.replace(",", ""))


def parse_stackup(md_text: str) -> tuple[list[dict], float | None]:
    """Return (wells, field_npv_mm) from the stackup section of a field report."""
    # Restrict to the stackup section so we never grab a different table.
    start = md_text.find("## Well-Level NPV Stackup")
    if start == -1:
        raise ValueError("No '## Well-Level NPV Stackup' section found")
    section = md_text[start : md_text.find("\n## ", start + 1)]

    field_npv = None
    m = _FIELD_NPV.search(section)
    if m:
        field_npv = _f(m.group("v"))

    wells: list[dict] = []
    for line in section.splitlines():
        rm = _ROW.match(line)
        if not rm:
            continue
        wells.append(
            {
                "api": rm.group("api"),
                "name": rm.group("name").strip(),
                "oil": _f(rm.group("oil")),
                "gross": _f(rm.group("gross")),
                "alloc": _f(rm.group("alloc")),
                "net": _f(rm.group("net")),
                "pct": _f(rm.group("pct")),
            }
        )
    if not wells:
        raise ValueError("Stackup section found but no well rows parsed")
    return wells, field_npv


def build_figure(dev_name: str, wells: list[dict], field_npv: float | None) -> go.Figure:
    names = [w["name"] or w["api"] for w in wells]
    net = [w["net"] for w in wells]

    measures = ["relative"] * len(wells) + ["total"]
    x = names + ["Field NPV"]
    y = net + [0.0]

    customdata = [
        [w["api"], w["oil"], w["gross"], w["alloc"], w["net"], w["pct"]] for w in wells
    ]
    # placeholder row for the total bar
    customdata.append(["—", sum(w["oil"] for w in wells), "—", "—",
                       field_npv if field_npv is not None else sum(net), "100"])

    hover = (
        "<b>%{x}</b><br>"
        "API: %{customdata[0]}<br>"
        "Oil: %{customdata[1]:.2f} MMbbl<br>"
        "Gross well NPV: $%{customdata[2]} M<br>"
        "Allocated shared cost: $%{customdata[3]} M<br>"
        "<b>Net well NPV: $%{customdata[4]} M</b><br>"
        "Share of field NPV: %{customdata[5]}%"
        "<extra></extra>"
    )

    fig = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=measures,
            x=x,
            y=y,
            text=[f"${v:,.1f}M" for v in net] + [
                f"${(field_npv if field_npv is not None else sum(net)):,.1f}M"
            ],
            textposition="outside",
            customdata=customdata,
            hovertemplate=hover,
            connector={"line": {"color": "rgba(120,120,120,0.5)"}},
            decreasing={"marker": {"color": "#c0392b"}},
            increasing={"marker": {"color": "#27ae60"}},
            totals={"marker": {"color": "#2c3e50"}},
        )
    )
    fig.update_layout(
        title=(
            f"{dev_name} — Well-Level NPV Stackup<br>"
            "<sub>each producing well's net NPV (production-pro-rata cost "
            "allocation) summing to the field total</sub>"
        ),
        yaxis_title="NPV contribution ($MM)",
        template="plotly_white",
        showlegend=False,
        margin={"t": 90, "l": 70, "r": 30, "b": 60},
    )
    fig.add_hline(y=0, line_width=1, line_color="rgba(0,0,0,0.4)")
    return fig


# A data row of the "NPV Timeline" yearly table:
# | year | net cashflow | cumulative NPV | critical operations (<br>-joined) |
_TL_ROW = re.compile(
    r"^\|\s*(?P<year>\d{4})\s*\|\s*(?P<net>[-\d,.]+)\s*\|"
    r"\s*(?P<cum>[-\d,.]+)\s*\|\s*(?P<ops>.*?)\s*\|\s*$"
)

# Compact event-type labels for annotations.
_EVENT_SHORT = {
    "Drilling (spud)": "spud",
    "Completion": "completion",
    "Well online (first production)": "first production",
    "Workover": "workover",
    "Recompletion": "recompletion",
    "Sidetrack": "sidetrack",
}


def parse_timeline(md_text: str) -> list[dict]:
    """Return the yearly rows of the '## NPV Timeline' table."""
    start = md_text.find("## NPV Timeline")
    if start == -1:
        raise ValueError("No '## NPV Timeline' section found")
    end = md_text.find("### Critical Operations Detail", start)
    section = md_text[start : end if end != -1 else len(md_text)]

    rows: list[dict] = []
    for line in section.splitlines():
        m = _TL_ROW.match(line)
        if not m:
            continue
        ops_raw = m.group("ops").strip()
        markers = [x.strip() for x in ops_raw.split("<br>") if x.strip()]
        rows.append(
            {
                "year": int(m.group("year")),
                "net": _f(m.group("net")),
                "cum": _f(m.group("cum")),
                "markers": markers,
            }
        )
    if not rows:
        raise ValueError("NPV Timeline section found but no year rows parsed")
    return sorted(rows, key=lambda r: r["year"])


def _event_types(markers: list[str]) -> str:
    """Distinct, compacted operation types present in a year's markers."""
    out: list[str] = []
    for mk in markers:
        head = mk.split(":")[0].strip()
        short = _EVENT_SHORT.get(head, head)
        if short not in out:
            out.append(short)
    return ", ".join(out)


def build_timeline_figure(dev_name: str, rows: list[dict]) -> go.Figure:
    """Over-time NPV bridge: each year's change in cumulative NPV, with the
    most impactful years annotated by the events that drove them."""
    years = [str(r["year"]) for r in rows]
    deltas: list[float] = []
    prev = 0.0
    for r in rows:
        deltas.append(r["cum"] - prev)
        prev = r["cum"]
    terminal = rows[-1]["cum"]

    type_strs = [_event_types(r["markers"]) for r in rows]
    # Plot on explicit numeric indices (not category strings) so the bars and
    # the annotations share one coordinate system; relabel ticks to the years.
    n = len(rows)
    xi = list(range(n))
    measures = ["relative"] * n + ["total"]
    x = xi + [n]
    y = deltas + [0.0]
    customdata = [
        [deltas[i], rows[i]["cum"], type_strs[i] or "production only"]
        for i in range(n)
    ] + [[terminal, terminal, "—"]]

    hover = (
        "<b>%{x}</b><br>"
        "Δ NPV this year: $%{customdata[0]:,.1f} M<br>"
        "Cumulative NPV: $%{customdata[1]:,.1f} M<br>"
        "Events: %{customdata[2]}"
        "<extra></extra>"
    )

    fig = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=measures,
            x=x,
            y=y,
            customdata=customdata,
            hovertemplate=hover,
            connector={"line": {"color": "rgba(120,120,120,0.5)"}},
            decreasing={"marker": {"color": "#c0392b"}},
            increasing={"marker": {"color": "#27ae60"}},
            totals={"marker": {"color": "#2c3e50"}},
        )
    )

    # Annotate the most impactful years (largest |Δ NPV|), but keep at least
    # 3 categories between annotations so adjacent boxes never collide — so a
    # multi-year production ramp gets ONE label, not three overlapping ones.
    order = sorted(range(len(rows)), key=lambda i: abs(deltas[i]), reverse=True)
    chosen: list[int] = []
    for i in order:
        if abs(deltas[i]) < 1.0:
            continue
        if all(abs(i - j) >= 3 for j in chosen):
            chosen.append(i)
        if len(chosen) == 3:
            break
    for i in chosen:
        down = deltas[i] < 0
        label = type_strs[i] if type_strs[i] != "production only" else "production ramp"
        fig.add_annotation(
            x=i,
            y=rows[i]["cum"],
            text=f"<b>{years[i]}: ${deltas[i]:+,.0f}M</b><br>{label}",
            showarrow=True,
            arrowhead=2,
            arrowcolor="rgba(80,80,80,0.8)",
            ax=0,
            ay=70 if down else -70,
            font={"size": 11},
            align="center",
            bgcolor="rgba(255,255,255,0.92)",
            bordercolor="rgba(120,120,120,0.6)",
            borderwidth=1,
        )

    fig.update_layout(
        title=(
            f"{dev_name} — What Moved NPV Over Time<br>"
            "<sub>change in cumulative NPV each year (discounted); the biggest "
            "swings are annotated with the events that drove them</sub>"
        ),
        yaxis_title="Δ cumulative NPV ($MM)",
        xaxis={
            "title": "Year",
            "tickmode": "array",
            "tickvals": xi + [n],
            "ticktext": years + ["Terminal"],
            "tickangle": -45,
        },
        template="plotly_white",
        showlegend=False,
        margin={"t": 90, "l": 70, "r": 30, "b": 60},
    )
    fig.add_hline(y=0, line_width=1, line_color="rgba(0,0,0,0.4)")
    return fig


def main(argv: list[str] | None = None) -> int:
    import plotly.io as pio

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dev", default="Julia", help="Field display name")
    ap.add_argument(
        "--slug",
        default=None,
        help="Override file slug (defaults to dev name lowercased)",
    )
    ap.add_argument(
        "--png",
        action="store_true",
        help="Also write static PNG previews (needs kaleido)",
    )
    args = ap.parse_args(argv)

    slug = args.slug or args.dev.lower().replace("/", "_").replace(" ", "_")
    md_path = REPORTS / f"field_economics_{slug}.md"
    if not md_path.exists():
        print(f"ERROR: report not found: {md_path}")
        return 1
    md_text = md_path.read_text()

    wells, field_npv = parse_stackup(md_text)
    rows = parse_timeline(md_text)
    fig_time = build_timeline_figure(args.dev, rows)
    fig_stack = build_figure(args.dev, wells, field_npv)

    # Combine both charts into one self-contained HTML (over-time bridge first).
    out = REPORTS / f"{slug}_npv_stackup.html"
    html_time = pio.to_html(fig_time, include_plotlyjs="cdn", full_html=False)
    html_stack = pio.to_html(fig_stack, include_plotlyjs=False, full_html=False)
    out.write_text(
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{args.dev} — NPV waterfalls</title></head><body>"
        f"{html_time}<hr style='margin:32px 0'>{html_stack}</body></html>"
    )
    print(f"Parsed {len(wells)} wells (field NPV ${field_npv:,.1f}M) "
          f"+ {len(rows)} timeline years")
    print(f"Wrote {out} ({out.stat().st_size:,} bytes)")

    if args.png:
        for name, fig in (("over_time", fig_time), ("stackup", fig_stack)):
            png = REPORTS / f"{slug}_npv_{name}.png"
            fig.write_image(png, width=1100, height=600, scale=2)
            print(f"Wrote {png} ({png.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
