# ABOUTME: Build the stakeholder presentation of the cost-basis time-series — least-assumptions first.
# ABOUTME: Issue #1017 — sourced record + pure arithmetic up front; assumptions quarantined as approval items A1–A4.
"""
build_stakeholder_presentation
==============================

Renders ``reports/cost/cost_timeseries_presentation.html`` from the curated
cost CSVs — the page we put in front of the folks involved before any of this
feeds a model.

The organizing rule is LEAST ASSUMPTIONS FIRST:

* Sections 1–4 contain only **sourced figures** and **pure arithmetic on
  sourced figures** (annual means, index rebasing, CAPEX ÷ well count,
  a Pearson correlation). Nothing there depends on a prior, a fitted curve,
  or a spread multiplier.
* Everything that DOES rest on judgement is quarantined in the **Assumptions
  Register** (section 5) as named decisions A1–A4, each awaiting sign-off on
  issue #1017. No figure above the register uses any of them.

Every data access goes through ``worldenergydata.cost.timeseries`` — this
script renders, it does not re-implement filters (see ``series.py`` for why
each filter exists). Charts are hand-rolled inline SVG so the file survives
being emailed. Series colors are CSS variables: the light and dark palettes
were separately validated for lightness band, chroma, CVD separation and
surface contrast — do not swap hexes casually.
"""

from __future__ import annotations

import csv
import html as _html
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from worldenergydata.cost.timeseries.dataset import (  # noqa: E402
    SANCTIONED_CSV,
    TIMESERIES_CSV,
    curated_dir,
    read_sanctioned_csv,
    read_timeseries_csv,
)
from worldenergydata.cost.timeseries.normalization import (  # noqa: E402
    DeflatorBasis,
    build_deflator,
    compare_against_inflation,
)
from worldenergydata.cost.timeseries.schema import (  # noqa: E402
    CostComponent,
    Provenance,
)
from worldenergydata.cost.timeseries.series import annual_means  # noqa: E402

CURATED = curated_dir(PROJECT_ROOT)
OUT = PROJECT_ROOT / "reports" / "cost" / "cost_timeseries_presentation.html"

#: Real-terms basis year for the inflation section (mirrors the main report).
BASIS_YEAR = 2025

_esc = _html.escape

# Series slots s1..s6 — fixed order, entity-stable. The hexes live in CSS
# (light + dark validated separately); SVG marks only ever say var(--sN).
RIG_SERIES = [
    (CostComponent.RIG_DAY_RATE_DRILLSHIP, "Drillship", "var(--s1)"),
    (CostComponent.RIG_DAY_RATE_SEMI, "Semi-sub", "var(--s2)"),
    (CostComponent.RIG_DAY_RATE_JACKUP, "Jackup", "var(--s3)"),
]
VESSEL_SERIES = [
    (CostComponent.VESSEL_DAY_RATE_OSV_PSV, "OSV/PSV", "var(--s4)"),
    (CostComponent.VESSEL_DAY_RATE_AHTS, "AHTS", "var(--s5)"),
]
INDEXED_SERIES = RIG_SERIES + VESSEL_SERIES
VERDICT_COMPONENTS = [c for c, _, _ in INDEXED_SERIES]


# ---------------------------------------------------------------------------
# chart primitives (presentation variants: hover titles + direct end labels)
# ---------------------------------------------------------------------------


def _nice_max(value: float) -> float:
    if value <= 0:
        return 1.0
    mag = 10 ** math.floor(math.log10(value))
    for mult in (1, 2, 2.5, 5, 10):
        if value <= mag * mult:
            return mag * mult
    return mag * 10


def _line_chart(
    series: list[tuple[str, dict[int, float], str]],
    title: str,
    y_label: str,
    y_fmt: str = "{:,.0f}",
    height: int = 320,
) -> str:
    """Multi-series line chart. Dots mark actual sourced observations and carry
    native tooltips (year + value), so sparse series read as sparse."""
    width = 960
    pad_l, pad_r, pad_t, pad_b = 78, 170, 26, 40
    plot_w, plot_h = width - pad_l - pad_r, height - pad_t - pad_b

    years = sorted({y for _, d, _ in series for y in d})
    values = [v for _, d, _ in series for v in d.values()]
    if not years or not values:
        return f'<p class="mini muted">No sourced data to chart for {_esc(title)}.</p>'
    y_min, y_max = min(years), max(years)
    v_max = _nice_max(max(values) * 1.05)
    x_span = max(1, y_max - y_min)

    px = lambda yr: pad_l + (yr - y_min) / x_span * plot_w  # noqa: E731
    py = lambda v: pad_t + plot_h - v / v_max * plot_h  # noqa: E731

    p = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
        f'aria-label="{_esc(title)}">'
    ]
    for i in range(5):
        v = v_max * i / 4
        p.append(
            f'<line x1="{pad_l}" y1="{py(v):.1f}" x2="{pad_l + plot_w}" '
            f'y2="{py(v):.1f}" stroke="var(--rule)" stroke-width="1"/>'
        )
        p.append(
            f'<text x="{pad_l - 8}" y="{py(v) + 4:.1f}" text-anchor="end" '
            f'class="tick">{y_fmt.format(v)}</text>'
        )
    ticks = {
        y for y in years if y % 5 == 0 and abs(y - y_min) > 1 and abs(y - y_max) > 1
    }
    for yr in sorted(ticks | {y_min, y_max}):
        p.append(
            f'<text x="{px(yr):.1f}" y="{pad_t + plot_h + 18}" '
            f'text-anchor="middle" class="tick">{yr}</text>'
        )
    p.append(
        f'<text x="14" y="{pad_t + plot_h / 2:.1f}" class="tick" '
        f'transform="rotate(-90 14 {pad_t + plot_h / 2:.1f})" '
        f'text-anchor="middle">{_esc(y_label)}</text>'
    )
    for idx, (name, data, color) in enumerate(series):
        if not data:
            continue
        pts = [(px(y), py(v), y, v) for y, v in sorted(data.items())]
        path = " ".join(
            ("M" if i == 0 else "L") + f"{x:.1f},{y:.1f}"
            for i, (x, y, *_) in enumerate(pts)
        )
        p.append(
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2" '
            f'stroke-linejoin="round"/>'
        )
        for x, y, yr, v in pts:
            p.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{color}" '
                f'stroke="var(--card)" stroke-width="1"/>'
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9" fill="transparent">'
                f"<title>{_esc(name)} — {yr}: {y_fmt.format(v)}</title></circle>"
            )
        # direct end label at the last point + legend swatch
        lx, ly = pts[-1][0], pts[-1][1]
        p.append(
            f'<text x="{lx + 7:.1f}" y="{ly + 4:.1f}" class="dlabel" '
            f'fill="{color}">{_esc(name)}</text>'
        )
        leg_y = pad_t + 8 + idx * 19
        p.append(
            f'<rect x="{pad_l + plot_w + 62}" y="{leg_y - 9}" width="11" '
            f'height="11" rx="2" fill="{color}"/>'
            f'<text x="{pad_l + plot_w + 79}" y="{leg_y}" class="leg">'
            f"{_esc(name)}</text>"
        )
    p.append("</svg>")
    return "".join(p)


def _dot_plot_capex_per_well(
    groups: list[tuple[str, list[tuple[str, float]]]],
) -> str:
    """One dot per project: disclosed CAPEX ÷ disclosed well count, grouped by
    country. Pure arithmetic on operators' own numbers."""
    width, row_h = 960, 34
    pad_l, pad_r, pad_t, pad_b = 170, 40, 14, 40
    height = pad_t + pad_b + row_h * len(groups)
    plot_w = width - pad_l - pad_r
    v_max = _nice_max(max(v for _, items in groups for _, v in items) * 1.06)
    px = lambda v: pad_l + v / v_max * plot_w  # noqa: E731

    p = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
        f'aria-label="Disclosed CAPEX per well by country">'
    ]
    for i in range(5):
        v = v_max * i / 4
        p.append(
            f'<line x1="{px(v):.1f}" y1="{pad_t}" x2="{px(v):.1f}" '
            f'y2="{height - pad_b}" stroke="var(--rule)" stroke-width="1"/>'
            f'<text x="{px(v):.1f}" y="{height - pad_b + 18}" '
            f'text-anchor="middle" class="tick">${v:,.0f}MM</text>'
        )
    for gi, (label, items) in enumerate(groups):
        cy = pad_t + row_h * gi + row_h / 2
        p.append(
            f'<text x="{pad_l - 10}" y="{cy + 4:.1f}" text-anchor="end" '
            f'class="leg">{_esc(label)}</text>'
        )
        for name, v in items:
            p.append(
                f'<circle cx="{px(v):.1f}" cy="{cy:.1f}" r="6" '
                f'fill="var(--s1)" fill-opacity="0.75" stroke="var(--card)" '
                f'stroke-width="2"><title>{_esc(name)}: ${v:,.0f}MM per well'
                f"</title></circle>"
            )
        if len(items) == 1:
            name, v = items[0]
            p.append(
                f'<text x="{px(v) + 11:.1f}" y="{cy + 4:.1f}" class="dlabel" '
                f'fill="var(--ink)">{_esc(name)}</text>'
            )
    p.append("</svg>")
    return "".join(p)


# ---------------------------------------------------------------------------
# arithmetic on sourced series (no priors, no fits)
# ---------------------------------------------------------------------------


def _rebase_100(data: dict[int, float]) -> dict[int, float]:
    if not data:
        return {}
    first = data[min(data)]
    return {y: v / first * 100.0 for y, v in data.items()} if first else {}


def _pearson_vs_brent(
    rows, component: CostComponent, brent: dict[int, float]
) -> Optional[tuple[float, int]]:
    comp = annual_means(rows, component)
    common = sorted(set(comp) & set(brent))
    if len(common) < 5:
        return None
    xs = [brent[y] for y in common]
    ys = [comp[y] for y in common]
    n = len(common)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / math.sqrt(sxx * syy), n


# ---------------------------------------------------------------------------
# page assembly
# ---------------------------------------------------------------------------


def _stat_tiles(rows, projects) -> str:
    sourced = [r for r in rows if r.provenance is Provenance.SOURCED]
    years = [r.year for r in sourced]
    capex = [
        p.sanctioned_capex_usd_mm
        for p in projects
        if p.sanctioned_capex_usd_mm is not None
    ]
    tiles = [
        (f"{len(sourced):,}", "sourced figures", "each with quote + URL + access date"),
        (
            f"{min(years)}–{max(years)}",
            "years covered",
            "sparse where sources are sparse",
        ),
        (f"{len(projects)}", "sanctioned projects", "operators' own disclosed totals"),
        (f"${sum(capex) / 1000:,.0f}bn", "disclosed CAPEX", "summed sanctioned totals"),
    ]
    cells = "".join(
        f'<div class="tile"><div class="tile-v">{_esc(v)}</div>'
        f'<div class="tile-l">{_esc(l)}</div><div class="tile-s">{_esc(s)}</div></div>'
        for v, l, s in tiles
    )
    return f'<div class="tiles">{cells}</div>'


def _verdict_table(rows) -> str:
    deflator = build_deflator(rows, DeflatorBasis.CPI)
    body = []
    label = dict((c, n) for c, n, _ in INDEXED_SERIES)
    for comp in VERDICT_COMPONENTS:
        v = compare_against_inflation(rows, deflator, comp, BASIS_YEAR)
        if v is None:
            continue
        body.append(
            "<tr>"
            f"<td>{_esc(label[comp])} day rate</td>"
            f"<td>{v.start_year}–{v.end_year}</td>"
            f"<td class='num'>{v.nominal_cagr_pct:+.1f}%</td>"
            f"<td class='num'>{v.deflator_cagr_pct:+.1f}%</td>"
            f"<td class='num'><strong>{v.excess_cagr_pct:+.1f} pp/yr</strong></td>"
            f"<td>{_esc(v.verdict)}</td></tr>"
        )
    return (
        '<div class="tscroll"><table><thead><tr><th>Component</th>'
        "<th>Sourced window</th><th>Nominal CAGR</th><th>CPI CAGR</th>"
        "<th>Excess vs CPI</th><th>Verdict</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table></div>"
    )


def _sanctioned_table(projects) -> str:
    body = []
    for p in sorted(projects, key=lambda q: (q.fid_year or 0), reverse=True):
        capex = (
            f"${p.sanctioned_capex_usd_mm:,.0f}"
            if p.sanctioned_capex_usd_mm is not None
            else "—"
        )
        boe = f"${p.usd_per_boe:,.1f}" if p.usd_per_boe is not None else "—"
        body.append(
            "<tr>"
            f"<td><a href='{_esc(p.source_url)}' rel='noopener'>{_esc(p.project)}</a></td>"
            f"<td>{_esc(p.operator)}</td><td>{_esc(p.country)}</td>"
            f"<td class='num'>{p.fid_year or '—'}</td>"
            f"<td class='num'>{p.first_oil_year or '—'}</td>"
            f"<td class='num'>{capex}<span class='mini muted'> MM</span></td>"
            f"<td>{_esc(p.capex_basis or '—')}</td>"
            f"<td class='num'>{p.well_count or '—'}</td>"
            f"<td class='num'>{boe}</td>"
            f"<td>{_esc(p.confidence.value)}</td></tr>"
        )
    return (
        '<div class="tscroll"><table><thead><tr><th>Project (source link)</th>'
        "<th>Operator</th><th>Country</th><th>FID</th><th>First oil</th>"
        "<th>Sanctioned CAPEX</th><th>Basis</th><th>Wells</th>"
        "<th>$/boe</th><th>Confidence</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table></div>"
    )


def _capex_per_well_groups(projects) -> list[tuple[str, list[tuple[str, float]]]]:
    by_country: dict[str, list[tuple[str, float]]] = {}
    for p in projects:
        if (
            p.sanctioned_capex_usd_mm is None
            or not p.well_count
            or not p.scope_is_offshore_only
        ):
            continue
        by_country.setdefault(p.country, []).append(
            (p.project, p.sanctioned_capex_usd_mm / p.well_count)
        )
    groups = sorted(
        by_country.items(),
        key=lambda kv: sum(v for _, v in kv[1]) / len(kv[1]),
        reverse=True,
    )
    return [(k, sorted(v, key=lambda t: t[1])) for k, v in groups]


def _outturn_finding() -> str:
    """A finding card: sanctioned vs final cost, from the revision-trails table.

    Pure sourced data — each point is an operator/regulator statement. Shows the
    computable full trails (a sanction and a final in one currency) sorted by
    overrun, so the reader sees directly that a single FID number is not a cost
    basis.
    """
    try:
        with open(
            CURATED / "cost_revision_trails.csv", newline="", encoding="utf-8"
        ) as fh:
            rows = list(csv.DictReader(fh))
    except FileNotFoundError:
        return ""
    # collect sanction + final per (project, currency)
    by_key: dict[tuple[str, str], dict] = {}
    for r in rows:
        try:
            v = float(r["VALUE_MM"])
        except (ValueError, KeyError):
            continue
        key = (r["PROJECT"], r["CURRENCY"])
        d = by_key.setdefault(key, {})
        if r["KIND"] == "sanction_estimate" and "s" not in d:
            d["s"] = v
        elif r["KIND"] in ("final_outturn", "final_forecast"):
            if "f" not in d or r["KIND"] == "final_outturn":
                d["f"] = v
    trails = []
    for (proj, ccy), d in by_key.items():
        if "s" in d and "f" in d and d["s"] > 0:
            trails.append((proj, ccy, d["s"], d["f"], d["f"] / d["s"]))
    if not trails:
        return ""
    trails.sort(key=lambda t: t[4], reverse=True)
    body = "".join(
        f"<tr><td>{_esc(p)}</td><td>{_esc(c)}</td>"
        f"<td class='num'>{s:,.0f}</td><td class='num'>{f:,.0f}</td>"
        f"<td class='num'><strong>{(m - 1) * 100:+.0f}%</strong></td></tr>"
        for p, c, s, f, m in trails
    )
    lo, hi = trails[-1], trails[0]
    return (
        '<div class="card finding"><h3>A single FID number is not a cost basis</h3>'
        "<p>Where operators and regulators disclosed a full trail — sanction "
        "estimate through to final outturn — the projects that finished on their "
        "FID number are the exception. The spread runs from "
        f"<strong>{(lo[4] - 1) * 100:+.0f}%</strong> ({_esc(lo[0])}) to "
        f"<strong>{(hi[4] - 1) * 100:+.0f}%</strong> ({_esc(hi[0])}), and the "
        "direction is not uniform: mid-caps and re-scoped brownfields came in "
        "under, integrated-LNG megaprojects ran over. Every figure below is an "
        "operator or regulator statement (currencies are never mixed).</p>"
        '<div class="tscroll"><table><thead><tr><th>Project</th><th>Ccy</th>'
        "<th>Sanction (MM)</th><th>Final (MM)</th><th>Δ</th></tr></thead>"
        f"<tbody>{body}</tbody></table></div>"
        '<p class="mini muted">Consequence for the deck: it must carry the '
        "outturn <em>distribution</em>, not a point estimate. Full dated trails "
        "with citations: "
        '<a href="https://github.com/vamseeachanta/worldenergydata/blob/main/data/modules/cost/curated/cost_revision_trails.csv" rel="noopener">cost_revision_trails.csv</a>.</p></div>'
    )


ASSUMPTIONS = [
    (
        "A1",
        "Stage-share priors",
        "How a sanctioned total splits across drill / complete / SURF / host / "
        "install / hookup. Engineering judgement, banded ±8–10 points, flagged "
        "by the authoring run itself as the dataset's weak point.",
        "Splitting project totals into per-stage costs (the stage_allocations "
        "table and everything downstream of it).",
        "Now has evidence: the contract-award reconciliation tests every prior "
        "it can. No sourced award exceeds its stage's band; the full-scope SURF "
        "anchors land in-band (Suriname) or just below (Guyana). The priors are "
        "corroborated where testable and contradicted nowhere — see the "
        '<a href="https://raw.githack.com/vamseeachanta/worldenergydata/main/reports/cost/a1_evidence_pack.html" rel="noopener">A1 evidence pack</a>.',
    ),
    (
        "A2",
        "Deflator policy",
        "Which yardstick is the default 'real' basis — general CPI or the "
        "sector index UCCI. This page shows CPI; UCCI is computed and available.",
        "Every real-terms number and every OUTPACED/LAGGED verdict.",
        None,
    ),
    (
        "A3",
        "Gap-fill method",
        "Years with no source are filled by oil-price-linked fitted curves — "
        "never by drawing a line across a blackout (the UCCI 2014–18 gap stays "
        "open until this is approved).",
        "Any figure for a year without a direct source.",
        None,
    ),
    (
        "A4",
        "Per-region drilling durations",
        "The disclosed totals imply very different well costs by region "
        "(section 3). Turning that into the model means region-specific "
        "days-per-well instead of one global constant.",
        "The FDAS time-varying deck (#651) — the first consumer of this dataset.",
        "Corroborated independently: the award reconciliation found SURF share "
        "also varies by region (Guyana below band, Suriname in-band) — the same "
        "regional signal, from a different measurement.",
    ),
]


def _assumption_cards() -> str:
    cards = []
    for code, name, what, touches, evidence in ASSUMPTIONS:
        ev = (
            f'<p class="mini aevid"><strong>Evidence:</strong> {evidence}</p>'
            if evidence
            else ""
        )
        cards.append(
            f'<div class="acard"><div class="acode">{code}</div>'
            f"<h3>{_esc(name)}</h3><p>{_esc(what)}</p>"
            f'<p class="mini"><strong>What it would touch:</strong> {_esc(touches)}</p>'
            f"{ev}"
            f'<p class="astat">⏳ awaiting approval — decision recorded on '
            f'<a href="https://github.com/vamseeachanta/worldenergydata/issues/1017" '
            f'rel="noopener">issue #1017</a></p></div>'
        )
    return f'<div class="acards">{"".join(cards)}</div>'


CSS = """
:root{--paper:#f5f7f7;--card:#ffffff;--ink:#0d2230;--muted:#5f7684;
--rule:#e2e8ea;--brand:#0b3d5c;--brand-ink:#eaf2f2;
--s1:#1a6fae;--s2:#1b7f5c;--s3:#b0721a;--s4:#7048a0;--s5:#a8442a;--s6:#2bb2a6;
--sourced:#1b7f5c;--assumed:#a8442a;--todo:#8894a0;}
@media (prefers-color-scheme: dark){:root{--paper:#0e1a22;--card:#152430;
--ink:#e5edf2;--muted:#93a7b3;--rule:#24363f;--brand:#0b2c42;--brand-ink:#dcebf2;
--s1:#3f8fd2;--s2:#2f9d77;--s3:#c08118;--s4:#9878d0;--s5:#c9664a;--s6:#2aa99a;
--sourced:#2f9d77;--assumed:#c9664a;}}
*{box-sizing:border-box;margin:0}
body{font:15px/1.55 -apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
background:var(--paper);color:var(--ink);padding:0 0 64px}
header{background:var(--brand);color:var(--brand-ink);padding:34px 24px 26px}
header h1{font-size:25px;line-height:1.25;max-width:980px;margin:0 auto}
header p{max-width:980px;margin:10px auto 0;opacity:.85}
main{max-width:980px;margin:0 auto;padding:0 16px}
nav.toc{background:var(--card);border:1px solid var(--rule);border-radius:10px;
padding:14px 18px;margin:22px 0}
nav.toc a{color:var(--s1);text-decoration:none;margin-right:16px;white-space:nowrap}
section{margin:34px 0}
h2{font-size:20px;margin-bottom:6px}
h3{font-size:15.5px;margin:14px 0 6px}
p{margin:8px 0}
.kicker{font-size:12px;letter-spacing:.09em;text-transform:uppercase;color:var(--muted)}
.card{background:var(--card);border:1px solid var(--rule);border-radius:10px;
padding:16px 18px;margin:12px 0}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
gap:12px;margin:18px 0}
.tile{background:var(--card);border:1px solid var(--rule);border-radius:10px;
padding:14px 16px}
.tile-v{font-size:26px;font-weight:700}
.tile-l{font-size:13px;font-weight:600;margin-top:2px}
.tile-s{font-size:12px;color:var(--muted)}
.tscroll{overflow-x:auto;border:1px solid var(--rule);border-radius:10px;
background:var(--card)}
table{border-collapse:collapse;width:100%;font-size:13.5px;min-width:720px}
th,td{padding:7px 10px;text-align:left;border-bottom:1px solid var(--rule);
vertical-align:top}
th{font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}
td.num{text-align:right;font-variant-numeric:tabular-nums}
td a{color:var(--s1)}
.tick{font-size:11px;fill:var(--muted)}
.leg{font-size:11.5px;fill:var(--ink)}
.dlabel{font-size:11.5px;font-weight:600}
.mini{font-size:12.5px}.muted{color:var(--muted)}
.prov{display:inline-block;padding:1px 9px;border-radius:99px;font-size:12px;
font-weight:600;color:#fff}
.formula{background:var(--card);border:1px solid var(--rule);border-left:4px solid
 var(--s1);border-radius:8px;padding:12px 16px;margin:10px 0;
font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13.5px;
overflow-x:auto;white-space:nowrap}
.finding{border-left:4px solid var(--sourced)}
.acards{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}
.acard{background:var(--card);border:1px solid var(--rule);border-top:4px solid
 var(--assumed);border-radius:10px;padding:14px 16px}
.acode{font-size:12px;font-weight:700;color:var(--assumed);letter-spacing:.06em}
.astat{font-size:12.5px;color:var(--muted)}
.aevid{border-left:3px solid var(--sourced);padding-left:9px;margin-top:8px}
.aevid a{color:var(--s1)}
.acard a{color:var(--s1)}
ol.seq{margin:8px 0 0 22px}
ol.seq li{margin:5px 0}
footer{max-width:980px;margin:40px auto 0;padding:14px 16px;color:var(--muted);
font-size:12.5px;border-top:1px solid var(--rule)}
"""


def main() -> int:
    rows = read_timeseries_csv(CURATED / TIMESERIES_CSV)
    projects = read_sanctioned_csv(CURATED / SANCTIONED_CSV)
    outturn_finding = _outturn_finding()

    rig_chart = _line_chart(
        [(n, annual_means(rows, c), col) for c, n, col in RIG_SERIES],
        "Offshore rig day rates — sourced annual means",
        "USD/day",
    )
    vessel_chart = _line_chart(
        [(n, annual_means(rows, c), col) for c, n, col in VESSEL_SERIES],
        "Marine support vessel day rates — sourced annual means",
        "USD/day",
    )
    indexed = [
        (n, _rebase_100(annual_means(rows, c)), col) for c, n, col in INDEXED_SERIES
    ]
    indexed.append(
        (
            "US CPI-U",
            _rebase_100(annual_means(rows, CostComponent.INDEX_CPI, region="US")),
            "var(--todo)",
        )
    )
    indexed_chart = _line_chart(
        [s for s in indexed if s[1]],
        "Each series indexed to 100 at its first sourced year",
        "index (first sourced year = 100)",
        y_fmt="{:,.0f}",
        height=360,
    )
    groups = _capex_per_well_groups(projects)
    capex_chart = _dot_plot_capex_per_well(groups) if groups else ""

    brent = annual_means(rows, CostComponent.OIL_PRICE_BRENT, region="global")
    corr_lines = []
    for comp, name, _ in INDEXED_SERIES:
        r = _pearson_vs_brent(rows, comp, brent)
        if r:
            corr_lines.append(
                f"<tr><td>{_esc(name)} day rate</td>"
                f"<td class='num'>{r[0]:+.2f}</td>"
                f"<td class='num'>{r[1]}</td></tr>"
            )
    corr_table = (
        '<div class="tscroll"><table><thead><tr><th>Component</th>'
        "<th>Pearson r vs Brent (same-year)</th><th>Overlapping years</th>"
        f"</tr></thead><tbody>{''.join(corr_lines)}</tbody></table></div>"
        if corr_lines
        else ""
    )

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
    repo = "https://github.com/vamseeachanta/worldenergydata"

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Field-development cost basis — the sourced record</title>
<style>{CSS}</style></head><body>
<header>
<div class="kicker" style="max-width:980px;margin:0 auto;opacity:.75">AceEngineer · worldenergydata · issue #1017</div>
<h1>Field-development cost basis — the sourced record</h1>
<p>What offshore rigs, vessels and sanctioned projects actually cost, year by
year, from citable sources — presented with the fewest possible assumptions.
Everything in sections 1–4 is a sourced figure or plain arithmetic on sourced
figures. Every judgement call is quarantined in section 5, awaiting approval.</p>
</header>
<main>
<nav class="toc"><strong class="mini">Contents</strong><br>
<a href="#read">How to read this</a> <a href="#rates">1 · Day rates</a>
<a href="#inflation">2 · Against inflation</a>
<a href="#sanctioned">3 · Sanctioned projects</a>
<a href="#findings">4 · What the data says</a>
<a href="#assumptions">5 · Assumptions awaiting approval</a>
<a href="#sequence">6 · The sequence</a></nav>

{_stat_tiles(rows, projects)}

<section id="read"><h2>How to read this</h2>
<div class="card"><p>Every figure in the underlying dataset carries a
provenance tag. This page uses only the first kind above the register:</p>
<p><span class="prov" style="background:var(--sourced)">sourced</span>
&nbsp;read off a citable page — the quote, URL and access date are in the
dataset&nbsp;·&nbsp;
<span class="prov" style="background:var(--assumed)">assumed</span>
&nbsp;engineering judgement — appears ONLY in section 5, never in a chart
here&nbsp;·&nbsp;
<span class="prov" style="background:var(--todo)">todo</span>
&nbsp;a known gap — rendered blank, never zero.</p>
<p class="mini muted">Dots on the charts are actual observations; a line
through three dots is three facts, not a dense series. Hover any dot for its
value. Full citations: <a href="{repo}/blob/main/data/modules/cost/curated/">curated CSVs</a>.</p></div>
</section>

<section id="rates"><h2>1 · The sourced day-rate record</h2>
<p>Nominal USD per day, annual means of sourced observations only — no fits,
no interpolation. Where a series is blank, we found no citable figure
(heavy-lift and pipelay rates are not publicly quoted at all — that gap is
declared, not modelled).</p>
<div class="card">{rig_chart}</div>
<div class="card">{vessel_chart}</div>
</section>

<section id="inflation"><h2>2 · How each component fared against inflation</h2>
<p>Rebasing every series to 100 at its first sourced year makes the slopes
comparable: components that outran the general price level separate visibly
from CPI.</p>
<div class="card">{indexed_chart}</div>
<h3>Verdicts (CPI basis, sourced endpoints only)</h3>
{_verdict_table(rows)}
<div class="formula">real(y) = nominal(y) × CPI({BASIS_YEAR}) / CPI(y)
&nbsp;&nbsp;·&nbsp;&nbsp; index(y) = value(y) / value(first sourced year) × 100
&nbsp;&nbsp;·&nbsp;&nbsp; excess = nominal CAGR − CPI CAGR</div>
<p class="mini muted">The window is each component's first and last
<em>sourced</em> year — a verdict is never anchored on a fitted value. Which
deflator (CPI vs the UCCI sector index) becomes the default basis is decision
<strong>A2</strong> in section 5.</p>
</section>

<section id="sanctioned"><h2>3 · Sanctioned projects — the operators' own numbers</h2>
<p>Deepwater projects with disclosed sanctioned CAPEX. Each row links its
source; the stated basis (gross at FID / net share / phase-only) is kept
because mixing bases silently is how benchmark tables go wrong.</p>
<h3>Disclosed CAPEX per well — pure division, no allocation</h3>
<p class="mini">Only projects that disclose both a CAPEX and a well count,
offshore-only scope. This is <code>CAPEX ÷ wells</code> — the full project
total (SURF, host, install included) spread over its wells, <em>before</em>
any stage split.</p>
<div class="card">{capex_chart}</div>
<div class="formula">CAPEX per well = sanctioned CAPEX (disclosed) / well count (disclosed)</div>
{_sanctioned_table(projects)}
</section>

<section id="findings"><h2>4 · What the data alone says</h2>
<div class="card finding"><h3>Day rates move with the oil price, not the calendar</h3>
<p>Same-year correlation between each sourced day-rate series and sourced
Brent annual means — plain Pearson r, no model:</p>
{corr_table}
<p class="mini muted">Same-year r <em>understates</em> the link where rates
reprice with a delay — deepwater rigs sit on multi-year contracts, so the
drillship figure is low by construction; shorter-cycle jackups and OSVs track
the price almost directly. The lagged analysis lives in the technical report
and is part of decision <strong>A3</strong>. Consequence either way: filling
gap years by extrapolating in time alone would be meaningless.</p></div>
<div class="card finding"><h3>The disclosed totals imply very different well costs by region</h3>
<p>Straight CAPEX-per-well from section 3 already separates regions before any
allocation: batch-drilled Guyana projects sit far below US Gulf of Mexico
20k-psi Paleogene developments. This spread is documented in the trade press
and falls out of the operators' own totals here — two independent routes to
the same fact. Consequence for the model: per-region drilling durations
(decision <strong>A4</strong>), not one global constant.</p></div>
<div class="card finding"><h3>Support vessels outran CPI; rigs mostly tracked it</h3>
<p>From the verdicts table: OSV/PSV and AHTS day rates grew ~4–5&nbsp;pp/yr
faster than CPI over their sourced windows, while semi-sub rates tracked CPI
and drillships sit in between. Cost escalation is not uniform across
components — a single inflation factor would misprice the mix.</p></div>
{outturn_finding}
</section>

<section id="assumptions"><h2>5 · Assumptions register — nothing above uses these</h2>
<p>Four judgement calls stand between the sourced record and a usable cost
deck. Each is a named decision awaiting sign-off; none is silently embedded in
the charts or tables above.</p>
{_assumption_cards()}
</section>

<section id="sequence"><h2>6 · The sequence — one step at a time</h2>
<div class="card"><ol class="seq">
<li>This presentation is reviewed and circulated (issue
<a href="https://github.com/vamseeachanta/worldenergydata/issues/1017">#1017</a>).</li>
<li>Decisions A1–A4 are approved or revised — each recorded as an issue
comment, one at a time.</li>
<li>Only then does the time-varying deck flow into the FDAS field-economics
model (issue <a href="https://github.com/vamseeachanta/worldenergydata/issues/651">#651</a>),
starting with per-region drilling durations.</li>
<li>The dataset stays living: sources are re-pulled on the documented refresh
cadence, and this page regenerates from the CSVs.</li>
</ol></div>
</section>
</main>
<footer>Generated {generated} by <code>scripts/cost/build_stakeholder_presentation.py</code>
from <code>data/modules/cost/curated/*.csv</code> (issues
<a href="https://github.com/vamseeachanta/worldenergydata/issues/844">#844</a> ·
<a href="https://github.com/vamseeachanta/worldenergydata/issues/1017">#1017</a>).
Companion technical report: <code>reports/cost/cost_basis_timeseries.html</code>.
No external fetches; safe to email.</footer>
</body></html>"""

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
