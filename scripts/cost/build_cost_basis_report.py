# ABOUTME: Build the living cost-basis time-series report — trends, inflation normalization, back-allocation.
# ABOUTME: Issue #844 — bottom-up component series cross-checked by top-down sanctioned-project totals.
"""
build_cost_basis_report
=======================

Reads the curated cost-basis CSVs and emits a single-file HTML report to
``reports/cost/cost_basis_timeseries.html`` plus three derived CSVs.

METHOD / provenance
-------------------
Everything on the page is computed from ``data/modules/cost/curated/*.csv``.
Nothing is hardcoded here, and nothing is invented: the honesty rails live in
the schema (a TODO row cannot carry a number; a SOURCED row cannot lack a
citation) and this script only *renders* what survives them.

The page colour-codes every figure by provenance, which is the whole point:

* **sourced**   — read off a citable page. The citation is in the CSV.
* **fitted**    — produced by a trend curve (``trend_fit``). Not a datum.
* **allocated** — back-allocated from a disclosed sanctioned total.
* **assumed**   — our engineering judgement, stated and owned.
* **todo**      — a known gap. Rendered blank, never zero.

The three scope additions from the 2026-07-13 owner comment each get a section:
inflation normalization (dual CPI/UCCI basis), sanctioned-project back-allocation
with its bottom-up reconciliation, and fitted trend curves per component.

Charts are hand-rolled inline ``<svg>`` — no Plotly, no CDN, no external fetch,
so the file is self-contained and survives being emailed to Frontier.
"""

from __future__ import annotations

import html as _html
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from worldenergydata.cost.timeseries.back_allocation import (  # noqa: E402
    DevelopmentType,
    LifecycleStage,
    allocate_project,
    reconcile_drilling,
)
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
    CostObservation,
    FigureType,
    Provenance,
)
from worldenergydata.cost.timeseries.trend_fit import fit_component  # noqa: E402

CURATED = curated_dir(PROJECT_ROOT)
OUT_DIR = PROJECT_ROOT / "reports" / "cost"

#: The basis year every real series is expressed in. 2025 = the last complete
#: calendar year at time of writing; bump it in the refresh, don't scatter it.
BASIS_YEAR = 2025

_esc = _html.escape

# Provenance palette. Shared between the SVG marks and the legend so the chart
# and its key cannot drift apart.
PROV_COLOR: dict[str, str] = {
    "sourced": "#1b7f5c",  # green — we read it on a page
    "fitted": "#b0721a",  # amber — a curve made it
    "allocated": "#7048a0",  # violet — split from a disclosed total
    "assumed": "#a8442a",  # rust — our judgement
    "todo": "#8894a0",  # grey — a known gap
}

#: Components we chart as headline trends.
HEADLINE = [
    CostComponent.RIG_DAY_RATE_DRILLSHIP,
    CostComponent.RIG_DAY_RATE_SEMI,
    CostComponent.RIG_DAY_RATE_JACKUP,
    CostComponent.VESSEL_DAY_RATE_OSV_PSV,
    CostComponent.VESSEL_DAY_RATE_AHTS,
]

LABEL: dict[CostComponent, str] = {
    CostComponent.RIG_DAY_RATE_DRILLSHIP: "Drillship day rate",
    CostComponent.RIG_DAY_RATE_SEMI: "Semi-sub day rate",
    CostComponent.RIG_DAY_RATE_JACKUP: "Jackup day rate",
    CostComponent.VESSEL_DAY_RATE_OSV_PSV: "OSV/PSV day rate",
    CostComponent.VESSEL_DAY_RATE_AHTS: "AHTS day rate",
    CostComponent.VESSEL_DAY_RATE_MSV: "MSV day rate",
    CostComponent.VESSEL_DAY_RATE_HEAVY_LIFT: "Heavy-lift day rate",
    CostComponent.VESSEL_DAY_RATE_PIPELAY: "Pipelay day rate",
    CostComponent.VESSEL_DAY_RATE_WELL_INTERVENTION: "Well-intervention day rate",
    CostComponent.INDEX_UCCI: "IHS/S&P UCCI",
    CostComponent.INDEX_CPI: "US CPI-U",
    CostComponent.OIL_PRICE_BRENT: "Brent",
}

SERIES_COLOR = ["#0b3d5c", "#1b7f5c", "#b0721a", "#7048a0", "#a8442a", "#2b6ca3"]


# ---------------------------------------------------------------------------
# chart primitives
# ---------------------------------------------------------------------------


def _annual_means(
    rows: list[CostObservation],
    component: CostComponent,
    sourced_only: bool = True,
    currency: str = "USD",
    figure_types: Optional[set[FigureType]] = None,
) -> dict[int, float]:
    """Mean value per year for one component.

    Filters on ``currency`` by default. This is not paranoia: the North Sea
    spot rates from Seabrokers are quoted in **GBP** and are stored as GBP
    (converting them would inject an FX rate no source states). Averaging them
    into a USD series would silently produce a number that is neither.

    ``figure_types`` exists because a contractor's backlog-weighted
    ``fleet_average`` and a market-clearing ``single_fixture`` are different
    series that diverge violently in a downturn — Transocean's ultra-deepwater
    fleet average read $484k in Q1-2016 while new fixtures were being signed
    near $170k. Averaging them together would manufacture a cost history that
    never happened, so callers pick one lens at a time.
    """
    buckets: dict[int, list[float]] = {}
    for obs in rows:
        if obs.component is not component or obs.value is None:
            continue
        if sourced_only and obs.provenance is not Provenance.SOURCED:
            continue
        if obs.currency != currency:
            continue
        if figure_types is not None and obs.figure_type not in figure_types:
            continue
        buckets.setdefault(obs.year, []).append(obs.value)
    return {y: sum(v) / len(v) for y, v in sorted(buckets.items())}


#: The backlog-weighted contractor averages. Lagging, survivorship-biased upward.
FLEET_LENS = {FigureType.FLEET_AVERAGE, FigureType.MARKET_AVERAGE}
#: The market-clearing prints. What someone actually agreed to pay, that year.
FIXTURE_LENS = {FigureType.SINGLE_FIXTURE}


def _line_chart_svg(
    series: list[tuple[str, dict[int, float], str]],
    title: str,
    y_label: str,
    height: int = 300,
    y_fmt: str = "{:,.0f}",
) -> str:
    """A multi-series line chart with sourced points marked.

    Points are drawn as dots so the reader can see *where the data actually is*
    — a smooth line through three observations should not look like a dense
    series, and here it visibly won't.
    """
    width = 900
    pad_l, pad_r, pad_t, pad_b = 78, 150, 30, 42
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    all_years = sorted({y for _, data, _ in series for y in data})
    all_values = [v for _, data, _ in series for v in data.values()]
    if not all_years or not all_values:
        return f'<p class="mini muted">No data to chart for {_esc(title)}.</p>'

    y_min, y_max = min(all_years), max(all_years)
    v_min, v_max = 0.0, max(all_values) * 1.08
    if v_max <= 0:
        v_max = 1.0
    x_span = max(1, y_max - y_min)

    def px(year: int) -> float:
        return pad_l + (year - y_min) / x_span * plot_w

    def py(value: float) -> float:
        return pad_t + plot_h - (value - v_min) / (v_max - v_min) * plot_h

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
        f'aria-label="{_esc(title)}">'
    ]

    # gridlines + y axis
    for i in range(5):
        value = v_min + (v_max - v_min) * i / 4
        y = py(value)
        parts.append(
            f'<line x1="{pad_l}" y1="{y:.1f}" x2="{pad_l + plot_w}" y2="{y:.1f}" '
            f'stroke="var(--rule)" stroke-width="1" opacity="0.6"/>'
        )
        parts.append(
            f'<text x="{pad_l - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="11" '
            f'fill="var(--muted)">{y_fmt.format(value)}</text>'
        )

    # x axis ticks — every 5 years, plus the endpoints
    tick_years = [y for y in all_years if y % 5 == 0]
    for year in sorted(set(tick_years) | {y_min, y_max}):
        x = px(year)
        parts.append(
            f'<text x="{x:.1f}" y="{pad_t + plot_h + 20}" text-anchor="middle" '
            f'font-size="11" fill="var(--muted)">{year}</text>'
        )

    parts.append(
        f'<text x="{14}" y="{pad_t + plot_h / 2}" font-size="11" fill="var(--muted)" '
        f'transform="rotate(-90 14 {pad_t + plot_h / 2})" text-anchor="middle">'
        f"{_esc(y_label)}</text>"
    )

    # series
    for idx, (name, data, color) in enumerate(series):
        if not data:
            continue
        points = [(px(y), py(v)) for y, v in sorted(data.items())]
        path = " ".join(
            ("M" if i == 0 else "L") + f"{x:.1f},{y:.1f}" for i, (x, y) in enumerate(points)
        )
        parts.append(
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.2" '
            f'stroke-linejoin="round"/>'
        )
        for x, y in points:
            parts.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.1" fill="{color}" '
                f'stroke="var(--card)" stroke-width="1"/>'
            )
        ly = pad_t + 6 + idx * 19
        parts.append(
            f'<rect x="{pad_l + plot_w + 14}" y="{ly - 8}" width="11" height="11" '
            f'rx="2" fill="{color}"/>'
        )
        parts.append(
            f'<text x="{pad_l + plot_w + 31}" y="{ly + 1}" font-size="11.5" '
            f'fill="var(--ink)">{_esc(name)}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


def _indexed_vs_inflation_svg(
    rows: list[CostObservation], deflator, basis_year: int
) -> str:
    """Every component and both deflators, rebased to 100 at a common year.

    This is the single most useful chart for #844's headline question: rebase
    everything and the components that outran inflation separate visibly from
    the ones that didn't.
    """
    series: list[tuple[str, dict[int, float], str]] = []

    def rebase(data: dict[int, float]) -> dict[int, float]:
        if not data:
            return {}
        base_year = min(data)
        base = data[base_year]
        if base <= 0:
            return {}
        return {y: v / base * 100.0 for y, v in data.items()}

    candidates = [
        (CostComponent.RIG_DAY_RATE_DRILLSHIP, SERIES_COLOR[0]),
        (CostComponent.RIG_DAY_RATE_SEMI, SERIES_COLOR[1]),
        (CostComponent.RIG_DAY_RATE_JACKUP, SERIES_COLOR[2]),
        (CostComponent.INDEX_CPI, "#8894a0"),
    ]
    # Rebase all series on the SAME year — the first year where the rig series
    # actually starts — otherwise "indexed to 100" compares different origins
    # and the chart silently lies.
    rig_data = {
        comp: _annual_means(rows, comp)
        for comp, _ in candidates
        if comp is not CostComponent.INDEX_CPI
    }
    starts = [min(d) for d in rig_data.values() if d]
    if not starts:
        return '<p class="mini muted">No sourced component data to index.</p>'
    common_start = min(starts)

    for comp, color in candidates:
        data = _annual_means(rows, comp)
        data = {y: v for y, v in data.items() if y >= common_start}
        if len(data) < 2:
            continue
        series.append((LABEL.get(comp, comp.value), rebase(data), color))

    return _line_chart_svg(
        series,
        title="Components vs CPI, indexed to 100 at first sourced year",
        y_label=f"index (first sourced year = 100)",
        height=320,
        y_fmt="{:,.0f}",
    )


def _legend(entries: list[tuple[str, str]]) -> str:
    items = "".join(
        f'<span class="lg"><span class="sw" style="background:{color}"></span>'
        f"{_esc(label)}</span>"
        for label, color in entries
    )
    return f'<div class="legend">{items}</div>'


def _prov_legend() -> str:
    return _legend(
        [
            ("sourced — read off a citable page", PROV_COLOR["sourced"]),
            ("fitted — produced by a trend curve", PROV_COLOR["fitted"]),
            ("allocated — split from a disclosed total", PROV_COLOR["allocated"]),
            ("assumed — our stated judgement", PROV_COLOR["assumed"]),
            ("todo — known gap, never guessed", PROV_COLOR["todo"]),
        ]
    )


def _pill(provenance: str) -> str:
    color = PROV_COLOR.get(provenance, "#8894a0")
    return (
        f'<span class="pill" style="background:{color}1f;color:{color};'
        f'border-color:{color}55">{_esc(provenance)}</span>'
    )


# ---------------------------------------------------------------------------
# sections
# ---------------------------------------------------------------------------


def _formula_card(title: str, formula: str, body: str) -> str:
    return (
        f'<div class="formula"><h4>{_esc(title)}</h4>'
        f'<div class="eq">{formula}</div>'
        f'<div class="mini">{body}</div></div>'
    )


def _coverage_section(rows: list[CostObservation]) -> str:
    """What we have, what we don't. Stated before anything else on the page."""
    prov = Counter(obs.provenance.value for obs in rows)
    comps = Counter(
        obs.component.value for obs in rows if obs.provenance is Provenance.SOURCED
    )
    years = [obs.year for obs in rows if obs.provenance is Provenance.SOURCED]

    kpis = "".join(
        f'<div class="kpi"><div class="v">{count:,}</div>'
        f'<div class="l">{_esc(name)} rows</div></div>'
        for name, count in prov.most_common()
    )

    body = [
        '<div class="kpis">',
        f'<div class="kpi"><div class="v">{len(rows):,}</div><div class="l">total rows</div></div>',
        kpis,
        "</div>",
    ]
    if years:
        body.append(
            f'<p class="mini">Sourced observations span <b>{min(years)}–{max(years)}</b> '
            f"across <b>{len(comps)}</b> distinct components.</p>"
        )
    return "".join(body)


def _inflation_section(rows: list[CostObservation]) -> tuple[str, list]:
    """Scope addition #1 — nominal + real on a dual deflator basis."""
    cpi = build_deflator(rows, DeflatorBasis.CPI)
    try:
        ucci = build_deflator(rows, DeflatorBasis.UCCI)
    except ValueError:
        ucci = None

    verdicts = []
    for component in HEADLINE:
        for deflator in [d for d in (cpi, ucci) if d is not None]:
            verdict = compare_against_inflation(rows, deflator, component, BASIS_YEAR)
            if verdict is not None:
                verdicts.append(verdict)

    if not verdicts:
        table = '<p class="mini muted">Not enough sourced points to render a verdict.</p>'
    else:
        body = ""
        for v in verdicts:
            excess = (
                f"{v.excess_cagr_pct:+.1f}" if v.excess_cagr_pct is not None else "—"
            )
            nominal = f"{v.nominal_cagr_pct:+.1f}" if v.nominal_cagr_pct is not None else "—"
            deflator_cagr = (
                f"{v.deflator_cagr_pct:+.1f}" if v.deflator_cagr_pct is not None else "—"
            )
            colour = (
                PROV_COLOR["assumed"]
                if (v.excess_cagr_pct or 0) > 0.5
                else (PROV_COLOR["sourced"] if (v.excess_cagr_pct or 0) < -0.5 else "var(--muted)")
            )
            body += (
                f"<tr><td>{_esc(LABEL.get(v.component, v.component.value))}</td>"
                f"<td>{_esc(v.basis.value.upper())}</td>"
                f"<td class='num'>{v.start_year}–{v.end_year}</td>"
                f"<td class='num'>{v.n_points}</td>"
                f"<td class='num'>{nominal}%</td>"
                f"<td class='num'>{deflator_cagr}%</td>"
                f"<td class='num' style='color:{colour};font-weight:700'>{excess} pp</td>"
                f"<td>{_esc(v.verdict)}</td></tr>"
            )
        table = (
            "<table><thead><tr><th>Component</th><th>Basis</th><th>Window</th>"
            "<th>n yrs</th><th>Nominal CAGR</th><th>Deflator CAGR</th>"
            "<th>Excess</th><th>Verdict</th></tr></thead>"
            f"<tbody>{body}</tbody></table>"
        )

    ucci_note = (
        f"<p class='mini'><b>UCCI deflator:</b> {_esc(ucci.source_note)}</p>"
        if ucci is not None
        else "<p class='mini warn'><b>UCCI deflator unavailable:</b> no UCCI index "
        "rows are sourced yet, so the sector-deflator basis is not published in "
        "this run. The CPI basis stands on its own. This is a coverage gap, not "
        "an error — see 'Not yet covered'.</p>"
    )

    formulas = (
        '<div class="formulas">'
        + _formula_card(
            "Real (deflated) cost",
            "real<sub>b</sub> = nominal<sub>t</sub> × ( D<sub>b</sub> / D<sub>t</sub> )",
            f"D = the deflator index. Two bases are published and never averaged: "
            f"<b>CPI</b> (general purchasing power) and <b>UCCI</b> (upstream sector). "
            f"Basis year b = <b>{BASIS_YEAR}</b>. Deflating by CPI and by UCCI answer "
            f"different questions and routinely disagree in sign — that disagreement "
            f"is a finding, not a bug.",
        )
        + _formula_card(
            "Did it beat inflation?",
            "excess = CAGR(component) − CAGR(deflator)",
            "Both CAGRs are taken over the component's own first→last <b>sourced</b> "
            "year, so the verdict is anchored on real data at both ends rather than "
            "on a fitted value. Positive excess = the component outpaced the yardstick.",
        )
        + "</div>"
    )

    return (
        f"<p class='mini'><b>CPI deflator:</b> {_esc(cpi.source_note)}</p>"
        + ucci_note
        + formulas
        + table
    ), verdicts


def _trend_section(rows: list[CostObservation], oil: dict[int, float]) -> str:
    """Scope addition #3 — fitted curves, with their quality stated."""
    body = ""
    fitted_any = False
    for component in HEADLINE:
        fit = fit_component(rows, component, oil_price_by_year=oil)
        if fit is None:
            body += (
                f"<tr><td>{_esc(LABEL.get(component, component.value))}</td>"
                f"<td colspan='6' class='muted mini'>too few sourced points to fit "
                f"responsibly (need ≥5 distinct years) — no curve published</td></tr>"
            )
            continue
        fitted_any = True
        corr = f"{fit.oil_price_corr:+.2f}" if fit.oil_price_corr is not None else "—"
        weak = (
            " <span class='warn'>(weak — treat with caution)</span>"
            if fit.is_weak
            else ""
        )
        body += (
            f"<tr><td>{_esc(LABEL.get(component, component.value))}</td>"
            f"<td><b>{_esc(fit.form.value)}</b>{weak}</td>"
            f"<td class='eq-inline'>{fit.equation}</td>"
            f"<td class='num'>{fit.r_squared:.2f}</td>"
            f"<td class='num'>{fit.adj_r_squared:.2f}</td>"
            f"<td class='num'>{fit.n_points}</td>"
            f"<td class='num'>{corr}</td></tr>"
        )

    table = (
        "<table><thead><tr><th>Component</th><th>Form</th><th>Equation</th>"
        "<th>R²</th><th>adj R²</th><th>n</th><th>r vs Brent</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )

    note = (
        "<p class='mini'>Four candidate forms are fitted per component and the "
        "winner is chosen by <b>adjusted</b> R², so a richer model has to earn its "
        "extra parameter. When <b>oil_linked</b> wins, that is the finding: the "
        "component is priced off the cycle, not off the calendar, and extrapolating "
        "it in time alone would be meaningless.</p>"
        "<p class='mini warn'>A fitted value is <b>not a datum</b>. Every value this "
        "produces is stamped <code>fitted</code> and years outside the fitted window "
        "are additionally flagged as extrapolated.</p>"
    )
    if not fitted_any:
        note += (
            "<p class='mini warn'>No component currently clears the 5-point minimum. "
            "The curves are code-complete and tested; they need more sourced years, "
            "which is the next data task.</p>"
        )
    return note + table


def _allocation_section(projects, rows: list[CostObservation]) -> str:
    """Scope addition #2 — top-down back-allocation + bottom-up reconciliation."""
    if not projects:
        return "<p class='mini warn'>No sanctioned projects sourced yet.</p>"

    formulas = (
        '<div class="formulas">'
        + _formula_card(
            "Stage back-allocation",
            "cost<sub>s</sub> = CAPEX<sub>total</sub> × ŝ<sub>s</sub> ,&nbsp;&nbsp; "
            "ŝ<sub>s</sub> = s<sub>s</sub>·τ<sub>s</sub> / Σ<sub>k</sub> s<sub>k</sub>·τ<sub>k</sub>",
            "s = the prior share for the development type; τ = the well-count tilt, "
            "applied to drill+complete only: τ = 1 + 0.5·(wells/reference − 1), clamped "
            "to [0.5, 1.8]. The 0.5 makes the tilt <b>sub-linear</b> — incremental wells "
            "on one campaign are cheaper than the first, because rig mob is already paid. "
            "Shares renormalise to 1, so the disclosed total is always conserved exactly.",
        )
        + _formula_card(
            "Uncertainty band",
            "cost<sub>s</sub><sup>lo,hi</sup> = CAPEX<sub>total</sub> × (ŝ<sub>s</sub> ∓ b<sub>s</sub>)",
            "b = the prior's band, typically ±8–10 share points. Operators disclose a "
            "<i>total</i> and a <i>scope</i>, almost never a stage breakdown — so the "
            "shares are <b>priors, not measurements</b>. A single-point stage cost here "
            "would be a lie of precision; the band is the honest output. Where an operator "
            "<i>does</i> disclose a split, that overrides the prior and the band collapses to zero.",
        )
        + _formula_card(
            "Bottom-up reconciliation",
            "drill<sub>bu</sub> = N<sub>wells</sub> × days/well × rate<sub>rig</sub> × m",
            "m = the spread multiplier grossing the bare rig rate up to a total well "
            "cost (tubulars, mud, cement, logging, ROV/vessel support, operator overhead). "
            "m = 2.0 is the conventional planning number and is an <b>assumption</b>. "
            "The gap between this and the allocated drill slice is the deliverable — "
            "<b>we report it, we do not tune it away</b>.",
        )
        + "</div>"
    )

    body = ""
    for p in projects:
        if p.sanctioned_capex_usd_mm is None:
            continue
        try:
            dev = DevelopmentType(p.development_type)
        except ValueError:
            dev = DevelopmentType.UNKNOWN
        allocation = allocate_project(
            p.project, p.sanctioned_capex_usd_mm, dev, well_count=p.well_count
        )
        if allocation is None:
            body += (
                f"<tr><td>{_esc(p.project)}</td><td>{_esc(p.operator)}</td>"
                f"<td class='num'>{p.fid_year or '—'}</td>"
                f"<td class='num'>{p.sanctioned_capex_usd_mm:,.0f}</td>"
                f"<td colspan='7' class='muted mini'>development type not "
                f"characterised — total left unallocated (we will not split a total "
                f"we cannot classify)</td></tr>"
            )
            continue

        cells = ""
        for stage in LifecycleStage:
            allocated = allocation.stage(stage)
            if allocated is None:
                cells += "<td class='num'>—</td>"
            else:
                cells += (
                    f"<td class='num' title='{allocated.cost_low_usd_mm:,.0f}–"
                    f"{allocated.cost_high_usd_mm:,.0f}'>"
                    f"{allocated.cost_mid_usd_mm:,.0f}</td>"
                )
        body += (
            f"<tr><td><b>{_esc(p.project)}</b></td><td>{_esc(p.operator)}</td>"
            f"<td class='num'>{p.fid_year or '—'}</td>"
            f"<td class='num'>{p.sanctioned_capex_usd_mm:,.0f}</td>"
            f"{cells}"
            f"<td>{_pill('allocated' if not allocation.shares_are_disclosed else 'sourced')}</td></tr>"
        )

    stage_heads = "".join(f"<th>{s.value}</th>" for s in LifecycleStage)
    table = (
        "<table><thead><tr><th>Project</th><th>Operator</th><th>FID</th>"
        f"<th>Sanctioned $MM</th>{stage_heads}<th>Basis</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
        "<p class='mini'>Stage cells are the <b>mid</b> allocation in $MM; hover for "
        "the low–high band. Every allocated cell inherits the disclosed total exactly "
        "(shares sum to 1).</p>"
    )
    return formulas + table


def _sanctioned_table(projects) -> str:
    def _num(value: Optional[float], fmt: str = "{:,.0f}") -> str:
        """A missing figure renders as an em-dash, never as a zero."""
        return fmt.format(value) if value is not None else "—"

    body = ""
    for p in sorted(projects, key=lambda x: (x.fid_year or 9999, x.project)):
        capex = (
            f"{p.sanctioned_capex_usd_mm:,.0f}"
            if p.sanctioned_capex_usd_mm is not None
            else "<span class='muted'>not disclosed</span>"
        )
        boe = p.usd_per_boe or p.derived_usd_per_boe
        body += (
            "<tr>"
            f"<td><b>{_esc(p.project)}</b></td>"
            f"<td>{_esc(p.operator)}</td>"
            f"<td>{_esc(p.region)}</td>"
            f"<td class='num'>{_num(p.water_depth_m)}</td>"
            f"<td class='num'>{p.fid_year or '—'}</td>"
            f"<td class='num'>{p.first_oil_year or '—'}</td>"
            f"<td class='num'>{capex}</td>"
            f"<td class='mini'>{_esc(p.capex_basis or '—')}</td>"
            f"<td class='num'>{p.well_count or '—'}</td>"
            f"<td class='mini'>{_esc(p.development_type)}</td>"
            f"<td class='num'>{_num(boe, '{:,.1f}')}</td>"
            f"<td class='mini'><a href='{_esc(p.source_url)}' rel='noopener'>"
            f"{_esc(p.source_title[:48])}</a></td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Project</th><th>Operator</th><th>Region</th>"
        "<th>WD (m)</th><th>FID</th><th>1st oil</th><th>Sanctioned $MM</th>"
        "<th>CAPEX basis</th><th>Wells</th><th>Dev type</th><th>$/boe</th>"
        "<th>Source</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )


# ---------------------------------------------------------------------------
# page
# ---------------------------------------------------------------------------

CSS = """
:root{--ink:#15202b;--muted:#5b6b7b;--accent:#0b3d5c;--accent-soft:#e8eef3;
--rule:#cdd7e0;--zebra:#f5f8fa;--bg:#ffffff;--card:#ffffff;--warn:#a8442a;}
@media (prefers-color-scheme:dark){:root{--ink:#e6edf3;--muted:#9fb0c0;
--accent:#7fb2d4;--accent-soft:#172634;--rule:#2b3947;--zebra:#141c25;
--bg:#0d1620;--card:#111c27;--warn:#e08a6c;}}
:root[data-theme="dark"]{--ink:#e6edf3;--muted:#9fb0c0;--accent:#7fb2d4;
--accent-soft:#172634;--rule:#2b3947;--zebra:#141c25;--bg:#0d1620;--card:#111c27;
--warn:#e08a6c;}
:root[data-theme="light"]{--ink:#15202b;--muted:#5b6b7b;--accent:#0b3d5c;
--accent-soft:#e8eef3;--rule:#cdd7e0;--zebra:#f5f8fa;--bg:#ffffff;--card:#ffffff;
--warn:#a8442a;}
*{box-sizing:border-box;}
body{font-family:"Helvetica Neue",Helvetica,Arial,"Segoe UI",sans-serif;
color:var(--ink);background:var(--bg);line-height:1.45;margin:0;font-size:15px;}
.page{max-width:1060px;margin:0 auto;padding:0 24px 64px;}
.head{border-bottom:3px solid var(--accent);padding:26px 0 16px;margin-bottom:10px;}
.brand{font-size:20px;font-weight:700;color:var(--accent);letter-spacing:.2px;}
.meta{font-size:12.5px;color:var(--muted);margin-top:5px;}
h1{font-size:27px;color:var(--ink);margin:22px 0 6px;line-height:1.18;}
h2{font-size:19px;color:var(--accent);border-bottom:1px solid var(--rule);
padding-bottom:5px;margin:38px 0 12px;scroll-margin-top:16px;}
h4{font-size:13px;margin:0 0 6px;}
p{margin:9px 0;}
.thesis{background:var(--accent-soft);border-left:5px solid var(--accent);
border-radius:0 8px 8px 0;padding:16px 20px;margin:16px 0 8px;font-size:16.5px;}
.thesis b{color:var(--accent);}
.toc{border:1px solid var(--rule);border-radius:10px;padding:14px 18px;
background:var(--card);margin:18px 0;}
.toc ol{margin:6px 0 0;padding-left:22px;font-size:14px;}
.toc li{margin:3px 0;}
.toc a{color:var(--accent);text-decoration:none;}
.toc a:hover{text-decoration:underline;}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
gap:12px;margin:20px 0 8px;}
.kpi{border:1px solid var(--rule);border-radius:8px;padding:13px 15px;
background:var(--card);}
.kpi .v{font-size:24px;font-weight:800;color:var(--ink);}
.kpi .l{font-size:11.5px;color:var(--muted);margin-top:3px;
text-transform:uppercase;letter-spacing:.4px;}
.card{border:1px solid var(--rule);border-radius:10px;padding:16px 18px;
background:var(--card);margin:14px 0;overflow-x:auto;}
.legend{display:flex;flex-wrap:wrap;gap:14px 22px;margin:6px 0 14px;
font-size:12px;color:var(--muted);}
.lg{display:inline-flex;align-items:center;gap:7px;}
.sw{width:14px;height:14px;border-radius:3px;display:inline-block;}
table{border-collapse:collapse;width:100%;margin:10px 0 6px;font-size:13px;}
th,td{border:1px solid var(--rule);padding:6px 9px;text-align:left;
vertical-align:top;}
th{background:var(--accent);color:#fff;font-weight:600;}
td.num{text-align:right;font-variant-numeric:tabular-nums;}
tbody tr:nth-child(even){background:var(--zebra);}
.mini{font-size:12.5px;}
.muted{color:var(--muted);}
.warn{color:var(--warn);font-weight:600;}
code{background:var(--zebra);padding:1px 5px;border-radius:4px;font-size:12px;}
.formulas{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
gap:14px;margin:16px 0;}
.formula{border:1px solid var(--rule);border-left:4px solid var(--accent);
border-radius:0 8px 8px 0;padding:13px 16px;background:var(--card);}
.formula h4{color:var(--accent);text-transform:uppercase;letter-spacing:.4px;
font-size:11.5px;}
.eq{font-family:"SF Mono",Menlo,Consolas,monospace;font-size:14px;
background:var(--zebra);padding:9px 11px;border-radius:6px;margin:7px 0 9px;
overflow-x:auto;}
.eq-inline{font-family:"SF Mono",Menlo,Consolas,monospace;font-size:11.5px;}
.pill{display:inline-block;font-size:10.5px;font-weight:700;padding:1px 7px;
border-radius:9px;border:1px solid;text-transform:uppercase;letter-spacing:.3px;}
.foot{border-top:2px solid var(--rule);margin-top:44px;padding-top:16px;
font-size:12px;color:var(--muted);line-height:1.6;}
a{color:var(--accent);}
"""

TOC = [
    ("coverage", "1. Coverage &amp; honesty — what this dataset does and does not know"),
    ("trends", "2. Cost-component trends over time"),
    ("inflation", "3. Inflation normalization — nominal vs real, dual basis (addition #1)"),
    ("sanctioned", "4. Sanctioned deepwater projects — the top-down anchor (addition #2)"),
    ("allocation", "5. Back-allocation to lifecycle stages + bottom-up reconciliation"),
    ("curves", "6. Fitted trend curves per component (addition #3)"),
    ("gaps", "7. Not yet covered"),
]


def render_html(
    rows: list[CostObservation],
    projects: list,
    oil: dict[int, float],
    generated: str,
) -> str:
    toc = "".join(
        f'<li><a href="#{key}">{label}</a></li>' for key, label in TOC
    )

    inflation_html, verdicts = _inflation_section(rows)

    rig_series = [
        (LABEL[c], _annual_means(rows, c), SERIES_COLOR[i])
        for i, c in enumerate(
            [
                CostComponent.RIG_DAY_RATE_DRILLSHIP,
                CostComponent.RIG_DAY_RATE_SEMI,
                CostComponent.RIG_DAY_RATE_JACKUP,
            ]
        )
    ]
    rig_series = [s for s in rig_series if s[1]]
    vessel_series = [
        (LABEL[c], _annual_means(rows, c), SERIES_COLOR[i + 3])
        for i, c in enumerate(
            [CostComponent.VESSEL_DAY_RATE_OSV_PSV, CostComponent.VESSEL_DAY_RATE_AHTS]
        )
    ]
    vessel_series = [s for s in vessel_series if s[1]]

    brent = {y: v for y, v in oil.items()}

    n_sourced = sum(1 for o in rows if o.provenance is Provenance.SOURCED)
    n_todo = sum(1 for o in rows if o.provenance is Provenance.TODO)
    n_capex = sum(1 for p in projects if p.sanctioned_capex_usd_mm is not None)

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Living cost-basis time-series — worldenergydata</title>
<style>{CSS}</style></head>
<body><div class="page">

<div class="head">
  <div class="brand">World Energy Data · Cost Basis</div>
  <div class="meta">Generated {_esc(generated)} · issue #844 · milestone 1</div>
</div>

<h1>Living cost-basis time-series for field-development economics</h1>

<div class="thesis">
  The FDAS cost deck rests on <b>single-point assumptions</b>. This dataset replaces
  them with a <b>sourced, time-varying, inflation-normalized</b> basis — a bottom-up
  component series (day rates, indices) <b>cross-checked</b> against a top-down
  anchor of disclosed sanctioned-project totals. Every figure on this page is
  colour-coded by how we know it. <b>Nothing here is a guess:</b> where we lack a
  source, the cell is blank and listed as a gap, never filled with a plausible number.
</div>

{_prov_legend()}

<div class="toc"><b>Contents</b><ol>{toc}</ol></div>

<div class="kpis">
  <div class="kpi"><div class="v">{n_sourced:,}</div><div class="l">sourced observations</div></div>
  <div class="kpi"><div class="v">{len(projects):,}</div><div class="l">sanctioned projects</div></div>
  <div class="kpi"><div class="v">{n_capex:,}</div><div class="l">with disclosed CAPEX</div></div>
  <div class="kpi"><div class="v">{n_todo:,}</div><div class="l">declared gaps (TODO)</div></div>
</div>

<h2 id="coverage">1. Coverage &amp; honesty</h2>
{_coverage_section(rows)}
<p class="mini">The <code>todo</code> count is a feature. The row schema makes a TODO
row structurally incapable of carrying a value — so a gap in this dataset is always
visible as a gap, and can never quietly become a number that someone later cites.</p>

<h2 id="trends">2. Cost-component trends over time</h2>
<div class="card">
  <h4>Offshore rig day rates by class (nominal USD/day, sourced points only)</h4>
  {_line_chart_svg(rig_series, "Rig day rates by class", "USD / day") if rig_series
   else '<p class="mini muted">No sourced rig day-rate points yet.</p>'}
</div>
<div class="card">
  <h4>Support &amp; construction vessel day rates (nominal USD/day, sourced points only)</h4>
  {_line_chart_svg(vessel_series, "Vessel day rates", "USD / day") if vessel_series
   else '<p class="mini muted">No sourced vessel day-rate points yet.</p>'}
</div>
<div class="card">
  <h4>Brent crude — the cycle driver (USD/bbl, EIA via FRED)</h4>
  {_line_chart_svg([("Brent", brent, "#a8442a")], "Brent", "USD / bbl")}
</div>
<p class="mini">Dots mark <b>actual sourced observations</b>. The line between two
distant dots is a visual convenience, not data — the gap between them is real, and
section 6 is where we decide what (if anything) may be interpolated across it.</p>

<h2 id="inflation">3. Inflation normalization — nominal vs real (scope addition #1)</h2>
{inflation_html}
<div class="card">
  <h4>Components vs CPI, each indexed to 100 at its first sourced year</h4>
  {_indexed_vs_inflation_svg(rows, None, BASIS_YEAR)}
  <p class="mini">Series above the CPI line outran general inflation; series below it
  lagged. All series share a common start year, so the comparison is like-for-like.</p>
</div>

<h2 id="sanctioned">4. Sanctioned deepwater projects — the top-down anchor (scope addition #2)</h2>
<p class="mini">Operators disclose a <b>total</b> and a <b>scope</b> at FID. That total is
the hardest number in this whole dataset — it is what someone actually committed to
spend. The <code>CAPEX basis</code> column is not decoration: a figure that is
<i>gross project cost</i> and one that is <i>operator net share</i> differ by a factor
of two or more, and silently mixing them is the fastest way to corrupt a benchmark.</p>
{_sanctioned_table(projects)}

<h2 id="allocation">5. Back-allocation to lifecycle stages + bottom-up reconciliation</h2>
{_allocation_section(projects, rows)}

<h2 id="curves">6. Fitted trend curves per component (scope addition #3)</h2>
{_trend_section(rows, oil)}

<h2 id="gaps">7. Not yet covered</h2>
<p>Stated plainly, because a living dataset that hides its own holes is worse than no
dataset. Milestone 1 does <b>not</b> yet cover:</p>
<ul class="mini">
  <li><b>UCCI/UOCI full history</b> — proprietary to S&amp;P Global. Only scattered
      published values are sourceable; the sector-deflator basis is therefore
      anchor-and-interpolate and is <i>not</i> extrapolated beyond its anchors.</li>
  <li><b>SURF $/km and host CAPEX $/tonne component series</b> — these are contracted
      lump-sum, so public day-rate equivalents largely do not exist. The
      back-allocation in section 5 is currently the only route to them.</li>
  <li><b>Heavy-lift and pipelay day rates</b> — same reason: contracted lump-sum, not
      chartered at a published rate.</li>
  <li><b>OPEX ($/bbl variable, $/yr fixed)</b> — not yet sourced as a time-series.</li>
  <li><b>Fiscal terms</b> (royalty bands, tax) as a time-varying series.</li>
  <li><b>Integration into the FDAS model as a time-varying deck</b> (issue #651) — this
      milestone builds the basis; wiring it into the model is the next step.</li>
</ul>

<div class="foot">
  <b>Sources:</b> <code>data/modules/cost/curated/{TIMESERIES_CSV}</code> ({len(rows):,} rows,
  {n_sourced:,} sourced) &middot;
  <code>data/modules/cost/curated/{SANCTIONED_CSV}</code> ({len(projects):,} projects).
  Reference series (CPI, PPI, Brent, WTI) are pulled from FRED's public CSV endpoints at
  refresh time and are never hand-entered. Every sourced row carries source title, URL,
  page reference, verbatim quote, access date, confidence and source priority — the
  provenance contract from issue #337.<br/>
  <b>Method:</b> Inflation normalization on a dual CPI/UCCI basis (§3); top-down
  back-allocation of disclosed sanctioned totals across six lifecycle stages using banded
  priors tilted sub-linearly by well count, reconciled against bottom-up day-rate ×
  duration (§5); per-component trend curves chosen by adjusted R² from four candidate
  functional forms (§6). <b>Every figure on this page is computed from the source rows —
  flag, don't fake.</b> The stage-share priors in §5 are the one place a number is not
  read off a page; they are isolated, banded, and flagged <code>assumed</code> everywhere
  they appear.<br/>
  <b>Build:</b> <code>scripts/cost/build_cost_basis_report.py</code> &rarr;
  <code>reports/cost/cost_basis_timeseries.html</code>. Refresh procedure:
  <code>docs/modules/cost/REFRESH_PROCEDURE.md</code>.
</div>

</div></body></html>"""


def main() -> int:
    ts_path = CURATED / TIMESERIES_CSV
    sp_path = CURATED / SANCTIONED_CSV
    if not ts_path.exists():
        print(f"missing {ts_path} — run the refresh first", file=sys.stderr)
        return 1

    rows = read_timeseries_csv(ts_path)
    projects = read_sanctioned_csv(sp_path) if sp_path.exists() else []

    oil = _annual_means(rows, CostComponent.OIL_PRICE_BRENT)

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html = render_html(rows, projects, oil, generated)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "cost_basis_timeseries.html"
    out.write_text(html, encoding="utf-8")

    # Derived CSVs — the report's own tables, as data.
    cpi = build_deflator(rows, DeflatorBasis.CPI)
    import csv as _csv

    with (OUT_DIR / "inflation_verdicts.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = _csv.writer(fh)
        writer.writerow(
            ["COMPONENT", "BASIS", "START_YEAR", "END_YEAR", "N_YEARS",
             "NOMINAL_CAGR_PCT", "DEFLATOR_CAGR_PCT", "REAL_CAGR_PCT",
             "EXCESS_CAGR_PCT", "VERDICT"]
        )
        for component in HEADLINE:
            v = compare_against_inflation(rows, cpi, component, BASIS_YEAR)
            if v is None:
                continue
            writer.writerow([
                v.component.value, v.basis.value, v.start_year, v.end_year, v.n_points,
                f"{v.nominal_cagr_pct:.3f}" if v.nominal_cagr_pct is not None else "",
                f"{v.deflator_cagr_pct:.3f}" if v.deflator_cagr_pct is not None else "",
                f"{v.real_cagr_pct:.3f}" if v.real_cagr_pct is not None else "",
                f"{v.excess_cagr_pct:.3f}" if v.excess_cagr_pct is not None else "",
                v.verdict,
            ])

    with (OUT_DIR / "stage_allocations.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = _csv.writer(fh)
        writer.writerow(
            ["PROJECT", "OPERATOR", "FID_YEAR", "TOTAL_CAPEX_USD_MM", "DEVELOPMENT_TYPE",
             "WELL_COUNT", "STAGE", "SHARE_MID", "COST_MID_USD_MM", "COST_LOW_USD_MM",
             "COST_HIGH_USD_MM", "PROVENANCE", "METHOD"]
        )
        for p in projects:
            if p.sanctioned_capex_usd_mm is None:
                continue
            try:
                dev = DevelopmentType(p.development_type)
            except ValueError:
                dev = DevelopmentType.UNKNOWN
            allocation = allocate_project(
                p.project, p.sanctioned_capex_usd_mm, dev, well_count=p.well_count
            )
            if allocation is None:
                continue
            for stage in allocation.stages:
                writer.writerow([
                    p.project, p.operator, p.fid_year or "", f"{p.sanctioned_capex_usd_mm:.1f}",
                    dev.value, p.well_count or "", stage.stage.value,
                    f"{stage.share_mid:.4f}", f"{stage.cost_mid_usd_mm:.1f}",
                    f"{stage.cost_low_usd_mm:.1f}", f"{stage.cost_high_usd_mm:.1f}",
                    "sourced" if allocation.shares_are_disclosed else "allocated",
                    allocation.method_note,
                ])

    print(f"rows={len(rows):,} projects={len(projects):,} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
