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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dev", default="Julia", help="Field display name")
    ap.add_argument(
        "--slug",
        default=None,
        help="Override file slug (defaults to dev name lowercased)",
    )
    args = ap.parse_args(argv)

    slug = args.slug or args.dev.lower().replace("/", "_").replace(" ", "_")
    md_path = REPORTS / f"field_economics_{slug}.md"
    if not md_path.exists():
        print(f"ERROR: report not found: {md_path}")
        return 1

    wells, field_npv = parse_stackup(md_path.read_text())
    fig = build_figure(args.dev, wells, field_npv)
    out = REPORTS / f"{slug}_npv_stackup.html"
    fig.write_html(out, include_plotlyjs="cdn", full_html=True)
    print(f"Parsed {len(wells)} wells; field NPV ${field_npv:,.1f}M")
    print(f"Wrote {out} ({out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
