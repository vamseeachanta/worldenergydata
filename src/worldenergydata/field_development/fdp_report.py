# ABOUTME: Assemble a self-contained HTML field development plan for a concept.
# ABOUTME: Issue #567 — capstone that composes engine + renderers + enrichment.
"""
worldenergydata.field_development.fdp_report
============================================

Composes a single self-contained **field development plan (FDP)** HTML page for a
:class:`FieldConcept`, pulling together everything the playbook produces:

* the input parameters,
* the ranked, scored concept shortlist (:func:`recommend`),
* the subsea-architecture **block diagram** and the to-scale **plan-view layout**
  (the renderers), and
* economics + vessel feasibility + hardware picks (:func:`enrich`).

The output is a standalone HTML string (inline SVG + CSS, no external assets) so
it can be written to ``reports/`` and opened directly. Pass ``actuals`` to show
known real figures (CAPEX, production, what was actually built) beside the
engine's recommendation.
"""

from __future__ import annotations

from typing import Optional

from worldenergydata.field_development.block import render_block_diagram
from worldenergydata.field_development.cost_estimator import (
    estimate_field_cost_portfolio,
)
from worldenergydata.field_development.enums import ConceptType
from worldenergydata.field_development.integrations import enrich
from worldenergydata.field_development.layout import render_layout
from worldenergydata.field_development.models import FieldConcept
from worldenergydata.field_development.recommendation import recommend

_CSS = """
body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:0;color:#1a2330;
background:#f4f6f9}
.wrap{max-width:1100px;margin:0 auto;padding:24px}
h1{font-size:24px;margin:0 0 4px}h2{font-size:17px;margin:28px 0 10px;
border-bottom:2px solid #d8e0ea;padding-bottom:4px}
.sub{color:#5b6b80;margin:0 0 16px}
.cards{display:flex;flex-wrap:wrap;gap:10px}
.card{background:#fff;border:1px solid #dde4ee;border-radius:8px;padding:10px 14px;
min-width:120px}
.card .k{font-size:11px;color:#6b7a90;text-transform:uppercase}
.card .v{font-size:18px;font-weight:600}
table{border-collapse:collapse;width:100%;background:#fff;font-size:13px}
th,td{border:1px solid #dde4ee;padding:6px 9px;text-align:left}
th{background:#eef2f7}
.viz{display:flex;flex-wrap:wrap;gap:20px;align-items:flex-start}
.viz figure{margin:0;background:#fff;border:1px solid #dde4ee;border-radius:8px;
padding:12px}.viz figcaption{font-size:12px;color:#5b6b80;margin-top:6px}
.pick{background:#e8f3ea}.warn{color:#a4601a}
.foot{color:#7b8aa0;font-size:11px;margin-top:24px}
.flex{display:flex;gap:24px;flex-wrap:wrap}.flex>div{flex:1;min-width:300px}
.narr{background:#fff;border-left:4px solid #3a8f5a;padding:12px 16px;
border-radius:0 6px 6px 0;line-height:1.5;font-size:14px}
"""


def _esc(s: object) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _fmt(v: object, suffix: str = "") -> str:
    return f"{v}{suffix}" if v is not None else "—"


def _param_cards(c: FieldConcept) -> str:
    items = [
        ("Water depth", _fmt(c.water_depth_m, " m")),
        ("Concept", c.concept_type.value if c.concept_type else "—"),
        ("Fluid", c.fluid_type.value if c.fluid_type else "—"),
        ("Operator", _fmt(c.operator)),
        ("Wells", _fmt(c.num_wells)),
        ("Plateau", _fmt(c.plateau_rate_boed, " boe/d")),
        ("Tieback", _fmt(c.tieback_distance_km, " km")),
        ("First oil", _fmt(c.year_first_oil)),
    ]
    return "".join(
        f'<div class="card"><div class="k">{_esc(k)}</div>'
        f'<div class="v">{_esc(v)}</div></div>'
        for k, v in items
    )


def _shortlist_table(ranked, actual: Optional[ConceptType]) -> str:
    rows = []
    for sc in ranked:
        is_actual = actual is not None and sc.concept_type == actual
        cls = ' class="pick"' if is_actual else ""
        rationale = "; ".join(sc.rationale[:2]) or "—"
        warn = (
            f'<span class="warn">{_esc("; ".join(sc.warnings[:1]))}</span>'
            if sc.warnings
            else ""
        )
        rows.append(
            f"<tr{cls}><td>{_esc(sc.concept_type.value)}"
            f"{' ★' if is_actual else ''}</td>"
            f"<td>{sc.total_score:.3f}</td>"
            f"<td>{_esc(sc.tree_type.value)}</td>"
            f"<td>{_esc(rationale)} {warn}</td></tr>"
        )
    return (
        "<table><tr><th>Concept</th><th>Score</th><th>Trees</th>"
        "<th>Rationale / flags</th></tr>" + "".join(rows) + "</table>"
    )


def _economics_block(economics, enriched, actuals: Optional[dict]) -> str:
    e = economics
    out = ['<div><h2>Economics & execution (engine estimate)</h2><div class="cards">']
    out.append(
        f'<div class="card"><div class="k">Dev system</div>'
        f'<div class="v">{_esc(e.dev_system or "—")}</div></div>'
        f'<div class="card"><div class="k">Est. CAPEX</div>'
        f'<div class="v">{_fmt(e.capex_mm, " $MM")}</div></div>'
        f'<div class="card"><div class="k">Est. NPV</div>'
        f'<div class="v">{_fmt(e.npv_mm, " $MM")}</div></div>'
    )
    # Vessel feasibility from the top enriched concept.
    if enriched:
        v = enriched[0].vessel
        out.append(
            f'<div class="card"><div class="k">Install vessels</div>'
            f'<div class="v">{_fmt(v.capable_vessel_count)}</div></div>'
            f'<div class="card"><div class="k">Max crane</div>'
            f'<div class="v">{_fmt(v.max_crane_capacity_t, " t")}</div></div>'
        )
        h = enriched[0].hardware
        if h.rigid_jumper_id or h.mooring_component_id:
            out.append(
                f'<div class="card"><div class="k">Hardware</div>'
                f'<div class="v" style="font-size:13px">'
                f'{_esc(h.rigid_jumper_id or "")} '
                f'{_esc(h.mooring_component_id or "")}</div></div>'
            )
    out.append("</div>")
    if actuals:
        cards = "".join(
            f'<div class="card"><div class="k">{_esc(k)}</div>'
            f'<div class="v">{_esc(val)}</div></div>'
            for k, val in actuals.items()
        )
        out.append(f'<h2>As built (actuals)</h2><div class="cards">{cards}</div>')
    out.append("</div>")
    return "".join(out)


def _cost_comparison_table(concept: FieldConcept, ranked) -> str:
    """Per-concept CAPEX/OPEX comparison (issue #643), cheapest lifecycle first."""
    portfolio = estimate_field_cost_portfolio(concept, ranked)
    rows = []
    for ct, est in portfolio.items():
        is_actual = concept.concept_type is not None and ct == concept.concept_type
        cls = ' class="pick"' if is_actual else ""
        rows.append(
            f"<tr{cls}><td>{_esc(ct.value)}{' ★' if is_actual else ''}</td>"
            f"<td>{_fmt(est.capex_mm, ' $MM')}</td>"
            f"<td>{_fmt(est.annual_opex_mm, ' $MM/yr')}</td>"
            f"<td>{est.capex_adjustment:g}×</td>"
            f"<td>{est.opex_factor:g}×</td>"
            f"<td>{_esc(est.note) if est.note else ''}</td></tr>"
        )
    return (
        "<h2>Per-concept cost comparison (Concept-Select fidelity)</h2>"
        "<table><tr><th>Concept</th><th>Est. CAPEX</th><th>Annual OPEX</th>"
        "<th>CAPEX adj.</th><th>OPEX factor</th><th>Note</th></tr>"
        + "".join(rows)
        + "</table>"
        '<p class="sub" style="font-size:12px">CAPEX layers a concept adjustment '
        "onto the field-level FDAS estimate; OPEX scales the FDAS fixed-OPEX "
        "assumption by concept and reserves. Qualitative priors, not a calibrated "
        "cost model.</p>"
    )


def build_fdp_html(
    concept: FieldConcept,
    top_n: int = 5,
    actuals: Optional[dict] = None,
    title: Optional[str] = None,
    narrative: Optional[str] = None,
) -> str:
    """Build a self-contained FDP HTML page for ``concept``.

    Args:
        concept: The field (with whatever parameters are known).
        top_n: How many concepts to show in the shortlist.
        actuals: Optional ``{label: value}`` of known real figures to display.
        title: Page title; defaults to ``"Field Development Plan — <name>"``.
        narrative: Optional engineering rationale paragraph to render.

    Returns:
        A complete standalone HTML document string.
    """
    ranked = recommend(concept, top_n=top_n)
    economics, enriched = enrich(concept, ranked)
    # Render the architecture for the field's own concept if it has one,
    # else for the engine's top recommendation.
    arch = concept
    if concept.concept_type is None and ranked:
        arch = concept.model_copy(
            update={
                "concept_type": ranked[0].concept_type,
                "tree_type": ranked[0].tree_type,
            }
        )
    if not arch.num_wells:
        arch = arch.model_copy(update={"num_wells": concept.num_wells or 4})
    block_svg = render_block_diagram(arch)
    layout_svg = render_layout(arch)

    narrative_html = (
        f'<h2>Engineering rationale</h2><p class="narr">{_esc(narrative)}</p>'
        if narrative
        else ""
    )
    page_title = title or f"Field Development Plan — {concept.name}"
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>{_esc(page_title)}</title><style>{_CSS}</style></head><body><div class="wrap">
<h1>{_esc(page_title)}</h1>
<p class="sub">Generated by the worldenergydata field-development playbook
(epic #567). Recommendation is heuristic (Concept Select / FEL-1 fidelity),
not a sanctioned design.</p>
{narrative_html}
<h2>Field parameters</h2><div class="cards">{_param_cards(concept)}</div>
<div class="flex">
<div><h2>Recommended concept shortlist</h2>
{_shortlist_table(ranked, concept.concept_type)}
<p class="sub" style="font-size:12px">★ = the concept actually selected for
this field (where known).</p></div>
</div>
{_economics_block(economics, enriched, actuals)}
{_cost_comparison_table(concept, ranked)}
<h2>Architecture &amp; layout ({_esc(arch.concept_type.value if arch.concept_type else "—")})</h2>
<div class="viz">
<figure>{block_svg}<figcaption>Subsea architecture block diagram</figcaption></figure>
<figure>{layout_svg}<figcaption>Plan-view field layout (to scale)</figcaption></figure>
</div>
<p class="foot">Sources: SubseaIQ field catalog (~2014) + BSEE + curated vessel/
subsea catalogs. Schematics are deterministic, generated from the field concept.
</p></div></body></html>"""
