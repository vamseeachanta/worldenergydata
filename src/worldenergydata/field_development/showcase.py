# ABOUTME: Coverage roll-up for the field-development capability showcase.
# ABOUTME: Issue #567 — how many fields the playbook can schematize, by area.
"""
worldenergydata.field_development.showcase
==========================================

Supporting data for the client-facing **capability showcase** (the page that
demonstrates the playbook end-to-end and quantifies its reach).

The schematic pipeline (recommend → graph → block diagram + plan-view layout)
runs on any :class:`FieldConcept`; water depth is the dominant input, so a field
that carries a depth yields a fully depth-resolved schematic. This module rolls
the SubseaIQ catalog up into client-meaningful **areas** and counts, per area,
how many fields are catalogued / carry a water depth / carry a known as-built
concept (a back-testable ground truth).

The country→area grouping is presentation-level domain knowledge, kept here as
data so the showcase and any coverage report share one source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass

from worldenergydata.field_development.block import render_block_diagram
from worldenergydata.field_development.layout import render_layout
from worldenergydata.field_development.models import FieldConcept
from worldenergydata.field_development.recommendation import recommend

# Client-meaningful area → the SubseaIQ ``COUNTRY`` values it groups. Anything
# unmapped falls into "Rest of world". (US is overwhelmingly Gulf of Mexico; a
# handful of Pacific/Alaska US fields are folded in — see basin.py.)
AREA_COUNTRIES: dict[str, list[str]] = {
    "Gulf of Mexico": ["us"],
    "North Sea & NW Europe": [
        "uk",
        "norway",
        "denmark",
        "netherlands",
        "ireland",
        "germany",
    ],
    "Brazil": ["brazil"],
    "West Africa": [
        "angola",
        "nigeria",
        "ghana",
        "gabon",
        "equatorial guinea",
        "congo",
        "congo, the demo. rep. of the",
        "cote d'ivoire",
        "ivory coast",
        "mauritania",
        "cameroon",
    ],
    "Mediterranean & N. Africa": ["egypt", "libya", "israel", "tunisia", "morocco"],
    "Asia-Pacific": [
        "australia",
        "malaysia",
        "indonesia",
        "thailand",
        "viet nam",
        "vietnam",
        "china",
        "philippines",
        "india",
        "new zealand",
        "brunei darussalam",
        "brunei",
        "myanmar",
    ],
}

REST_OF_WORLD = "Rest of world"


@dataclass(frozen=True)
class AreaCoverage:
    """Per-area schematic-coverage counts."""

    area: str
    total: int  # catalogued fields in the area
    with_depth: int  # carry a water depth -> fully depth-resolved schematic
    with_concept: int  # carry a known as-built concept (back-testable)


def _region_index() -> dict[str, str]:
    """Build a normalized country→area lookup from :data:`AREA_COUNTRIES`."""
    idx: dict[str, str] = {}
    for area, countries in AREA_COUNTRIES.items():
        for c in countries:
            idx[c] = area
    return idx


def area_for_region(region: str | None) -> str:
    """Map a SubseaIQ region/country to a showcase area (or ``Rest of world``)."""
    if not region:
        return REST_OF_WORLD
    return _region_index().get(region.strip().lower(), REST_OF_WORLD)


# Display order: the areas with the deepest playbook coverage first, then the
# catch-all last.
_AREA_ORDER = list(AREA_COUNTRIES.keys()) + [REST_OF_WORLD]


def coverage_by_area(fields: list[FieldConcept]) -> list[AreaCoverage]:
    """Roll a list of fields up into per-area schematic-coverage counts.

    Returns areas in display order; empty areas are omitted. The per-area counts
    always sum back to the input totals (every field lands in exactly one area).
    """
    totals: dict[str, list[int]] = {a: [0, 0, 0] for a in _AREA_ORDER}
    for f in fields:
        area = area_for_region(f.region)
        bucket = totals[area]
        bucket[0] += 1
        if f.water_depth_m is not None:
            bucket[1] += 1
        if f.concept_type is not None:
            bucket[2] += 1
    return [
        AreaCoverage(a, t[0], t[1], t[2]) for a in _AREA_ORDER if (t := totals[a])[0]
    ]


def total_coverage(fields: list[FieldConcept]) -> AreaCoverage:
    """Grand-total coverage across all areas (area label = ``"All areas"``)."""
    return AreaCoverage(
        area="All areas",
        total=len(fields),
        with_depth=sum(1 for f in fields if f.water_depth_m is not None),
        with_concept=sum(1 for f in fields if f.concept_type is not None),
    )


# --------------------------------------------------------------------------- #
# HTML rendering for the client showcase page
# --------------------------------------------------------------------------- #

# The playbook pipeline, described for a non-specialist client audience.
PIPELINE_STAGES: list[tuple[str, str]] = [
    (
        "1. Field parameters",
        "Reserves, fluid, water depth, distance-to-host, "
        "metocean — whatever is known about the field.",
    ),
    (
        "2. Concept screening",
        "A scored shortlist of development concepts (FPSO, "
        "spar, semisub, TLP, fixed platform, subsea tieback…) ranked by depth fit, "
        "regional development practice, reserves and risk.",
    ),
    (
        "3. Architecture schematic",
        "A subsea-architecture block diagram — host, "
        "manifolds, trees, flowlines, risers, umbilicals — generated from the concept.",
    ),
    (
        "4. To-scale plan view",
        "A bird's-eye field layout drawn to real scale from " "the well/host geometry.",
    ),
    (
        "5. Economics & vessels",
        "Indicative CAPEX/NPV plus which installation "
        "vessels in the fleet can build it.",
    ),
    (
        "6. Cost comparison",
        "Per-concept CAPEX/OPEX so options compare on lifecycle "
        "cost, not just technical fit.",
    ),
    (
        "7. Flow-assurance screen",
        "Hydrate / wax / slugging / erosion risk flags "
        "with mitigation direction (insulation, heating, inhibitor, boosting).",
    ),
    (
        "8. 3D hardware & export",
        "Parametric 3D models (jumpers, mooring, manifold) "
        "and DEXPI / STEP export for downstream engineering tools.",
    ),
]

_CSS = """
body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:0;color:#16202e;
background:#eef2f7}
.wrap{max-width:1180px;margin:0 auto;padding:28px}
.hero{background:linear-gradient(135deg,#0d2b45,#13507a);color:#fff;border-radius:12px;
padding:30px 34px;margin-bottom:24px}
.hero h1{margin:0 0 8px;font-size:28px}.hero p{margin:0;opacity:.92;max-width:760px;
line-height:1.5}
h2{font-size:19px;margin:30px 0 12px;border-bottom:2px solid #cfd9e6;padding-bottom:5px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px}
.stage{background:#fff;border:1px solid #d7e0ec;border-radius:9px;padding:14px 16px}
.stage .t{font-weight:600;color:#13507a;margin-bottom:5px}
.stage .d{font-size:13px;color:#48586c;line-height:1.45}
table{border-collapse:collapse;width:100%;background:#fff;font-size:13px;
border-radius:8px;overflow:hidden}
th,td{border:1px solid #dde4ee;padding:8px 11px;text-align:left}
th{background:#13507a;color:#fff}tr:nth-child(even) td{background:#f6f9fc}
.tot td{font-weight:700;background:#e8f0f8}
.num{text-align:right;font-variant-numeric:tabular-nums}
.ex{background:#fff;border:1px solid #d7e0ec;border-radius:10px;padding:16px 18px;
margin-bottom:16px}
.ex h3{margin:0 0 2px;font-size:16px}.ex .meta{color:#5b6b80;font-size:12px;margin:0 0 4px}
.ex .blurb{font-size:13px;color:#33465c;margin:6px 0 12px;line-height:1.45}
.viz{display:flex;flex-wrap:wrap;gap:18px;align-items:flex-start}
.viz figure{margin:0}.viz figcaption{font-size:11px;color:#6b7a90;margin-top:4px}
.pill{display:inline-block;background:#e8f3ea;color:#1f6b3a;border-radius:11px;
padding:1px 9px;font-size:11px;font-weight:600}
.pill.miss{background:#fbeede;color:#9a5a18}
.foot{color:#6b7a90;font-size:11px;margin-top:26px;line-height:1.5}
.callout{background:#fff;border-left:4px solid #13507a;padding:12px 16px;
border-radius:0 6px 6px 0;font-size:13px;line-height:1.5;margin:14px 0}
.area-h{color:#13507a;margin:18px 0 8px}
"""


def _esc(s: object) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_exemplar_card(field: FieldConcept, blurb: str) -> str:
    """Render one exemplar card: blind engine pick + real block & plan-view SVGs.

    The engine pick is made on a label-stripped probe (the field's as-built
    ``concept_type``/``operator`` removed), so the match badge is honest.
    """
    ranked = recommend(
        field.model_copy(update={"concept_type": None, "operator": None})
    )
    rec = ranked[0].concept_type if ranked else None
    arch = field
    if arch.concept_type is None and rec is not None:
        arch = arch.model_copy(update={"concept_type": rec})
    if not arch.num_wells:
        arch = arch.model_copy(update={"num_wells": 6})
    block_svg = render_block_diagram(arch)
    layout_svg = render_layout(arch)
    real = field.concept_type.value if field.concept_type else "—"
    recv = rec.value if rec else "—"
    match = field.concept_type is not None and rec == field.concept_type
    pill = (
        '<span class="pill">engine pick matches as-built</span>'
        if match
        else f'<span class="pill miss">as-built {_esc(real)} · '
        f"engine {_esc(recv)}</span>"
    )
    depth = f"{field.water_depth_m:,.0f} m" if field.water_depth_m else "depth n/a"
    return (
        f'<div class="ex"><h3>{_esc(field.name)}</h3>'
        f'<p class="meta">{_esc(field.region or "")} · {_esc(depth)} · '
        f"as-built: {_esc(real)}</p>{pill}"
        f'<p class="blurb">{_esc(blurb)}</p>'
        f'<div class="viz"><figure>{block_svg}'
        f"<figcaption>Subsea architecture block diagram</figcaption></figure>"
        f"<figure>{layout_svg}"
        f"<figcaption>Plan-view layout (to scale)</figcaption></figure></div></div>"
    )


def render_coverage_table(fields: list[FieldConcept]) -> str:
    """Render the by-area coverage table with a grand-total row."""
    rows = []
    for a in coverage_by_area(fields):
        rows.append(
            f"<tr><td>{_esc(a.area)}</td>"
            f'<td class="num">{a.total:,}</td>'
            f'<td class="num">{a.with_depth:,}</td>'
            f'<td class="num">{a.with_concept:,}</td></tr>'
        )
    t = total_coverage(fields)
    rows.append(
        f'<tr class="tot"><td>{_esc(t.area)}</td>'
        f'<td class="num">{t.total:,}</td>'
        f'<td class="num">{t.with_depth:,}</td>'
        f'<td class="num">{t.with_concept:,}</td></tr>'
    )
    return (
        "<table><tr><th>Area</th><th>Fields catalogued</th>"
        "<th>With water depth<br>(depth-resolved schematic)</th>"
        "<th>With known as-built concept</th></tr>" + "".join(rows) + "</table>"
    )


def build_showcase_html(exemplars: list[dict], fields: list[FieldConcept]) -> str:
    """Assemble the full self-contained capability-showcase HTML.

    Args:
        exemplars: ``[{area, field_name, blurb}, ...]`` curated exemplars; each is
            matched (case-insensitively) to a field in ``fields`` and skipped if
            absent.
        fields: the field catalog (drives both exemplar lookup and coverage).
    """
    by_name = {f.name.strip().lower(): f for f in fields}
    cards = []
    for ex in exemplars:
        f = by_name.get(ex["field_name"].strip().lower())
        if f is None:
            continue
        cards.append(
            f'<h3 class="area-h">{_esc(ex["area"])}</h3>'
            + render_exemplar_card(f, ex["blurb"])
        )
    t = total_coverage(fields)
    stages = "".join(
        f'<div class="stage"><div class="t">{_esc(name)}</div>'
        f'<div class="d">{_esc(desc)}</div></div>'
        for name, desc in PIPELINE_STAGES
    )
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Offshore Field-Development Playbook — Capability Showcase</title>
<style>{_CSS}</style></head><body><div class="wrap">
<div class="hero"><h1>Offshore Field-Development Playbook</h1>
<p>From a field's parameters to a ranked development concept, a to-scale subsea
schematic, indicative economics, flow-assurance flags and 3D hardware — generated
deterministically in seconds. This page shows what the engine produces and how
many fields it can do it for today.</p></div>

<h2>What the playbook produces</h2>
<div class="grid">{stages}</div>

<h2>Worked examples — real fields, generated schematics</h2>
<p class="callout">Every diagram below is generated by the engine from the field's
parameters (not drawn by hand). The badge shows whether the engine's blind concept
pick — made with the field's answer hidden — matches what was actually built.</p>
{"".join(cards)}

<h2>How many fields can we schematize today?</h2>
<p class="callout">The schematic pipeline runs on any catalogued field; water depth
is the dominant input, so the middle column counts fields that yield a fully
depth-resolved schematic right now. Coverage spans <b>{t.total:,} fields</b>
across every major offshore region.</p>
{render_coverage_table(fields)}

<p class="foot">Sources: SubseaIQ field catalog (~2014) + BSEE (Gulf of Mexico
production) + curated vessel / subsea hardware catalogs. Concept recommendations
are heuristic (Concept-Select / FEL-1 fidelity), reported in-sample, not a
sanctioned design. Schematics are deterministic and reproducible from the field
concept. Generated by the worldenergydata field-development playbook (epic #567).
</p></div></body></html>"""
