# ABOUTME: Generate an FDP portfolio (per-field plans + index) from research JSON.
# ABOUTME: Issue #567 — consumes the field-dev-portfolio-research workflow output.
"""
Build a portfolio of field development plans for deepwater GoM fields.

Input: a JSON array of researched/validated field profiles (the output of the
``field-dev-portfolio-research`` workflow). Each profile is mapped to a
:class:`FieldConcept`, run through the playbook, and rendered to a standalone
FDP HTML; an ``index.html`` provides a comparison table + links.

Run:
    .venv/bin/python scripts/field_development/build_fdp_portfolio.py <results.json>
"""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

from worldenergydata.field_development import build_fdp_html
from worldenergydata.field_development.enums import (
    ConceptType,
    FluidType,
    MetoceanRegime,
)
from worldenergydata.field_development.models import FieldConcept
from worldenergydata.field_development.recommendation import recommend

OUT_DIR = Path(__file__).parents[2] / "reports" / "field_development" / "portfolio"

_FLUID = {
    "oil": FluidType.OIL,
    "gas": FluidType.GAS,
    "condensate": FluidType.CONDENSATE,
    "gas_condensate": FluidType.GAS_CONDENSATE,
}


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _concept_type(d: dict) -> ConceptType | None:
    v = d.get("verify") or {}
    raw = v.get("corrected_concept_type") or d.get("concept_type")
    try:
        return ConceptType(raw) if raw else None
    except ValueError:
        return None


def to_concept(d: dict) -> FieldConcept:
    """Map a researched profile dict to a FieldConcept."""
    ct = _concept_type(d)
    is_tieback = ct == ConceptType.SUBSEA_TIEBACK
    return FieldConcept(
        name=d["name"],
        operator=d.get("operator_current"),
        region="US Gulf of Mexico",
        water_depth_m=d.get("water_depth_m"),
        fluid_type=_FLUID.get((d.get("fluid") or "").lower()),
        concept_type=ct,
        tieback_distance_km=d.get("tieback_distance_km") if is_tieback else None,
        distance_to_host_km=d.get("tieback_distance_km") if is_tieback else None,
        host_spare_capacity=True if is_tieback else None,
        # Unknown well counts remain unknown rather than becoming layout inputs.
        num_wells=d.get("num_wells"),
        recoverable_reserves_mmboe=d.get("recoverable_reserves_mmboe"),
        plateau_rate_boed=d.get("plateau_boed"),
        year_first_oil=d.get("first_oil_year"),
        metocean_regime=MetoceanRegime.HURRICANE_CYCLONE,
        data_source=(
            "; ".join(s["url"] for s in d["evidence"].values())
            if d.get("evidence")
            else "SubseaIQ + web research (FDP portfolio)"
        ),
    )


def build_profile_page(d: dict) -> str:
    """Render documented facts without filling evidence gaps with model priors.

    Legacy profiles retain their original playbook renderer. Documented profiles
    use the same parameter/rationale/architecture/economics outline, but require
    explicit citations and never run ranking, costs or assumed layout geometry.
    """
    if not d.get("evidence"):
        return build_fdp_html(
            to_concept(d),
            actuals=_actuals(d),
            narrative=_narrative(d),
            title=f"Field Development Plan — {d['name']}",
        )
    concept = to_concept(d)
    parameters = {
        "operator_current": ("Operator at source date", concept.operator),
        "concept_type": ("Reported development concept", d.get("concept_type")),
        "host_facility": ("Host", d.get("host_facility")),
        "water_depth_m": ("Water depth (m)", concept.water_depth_m),
        "num_wells": ("Wells (scope stated below)", concept.num_wells),
        "plateau_boed": ("Designed peak capacity (boe/d)", concept.plateau_rate_boed),
        "reported_oil_capacity_bpd": (
            "Reported oil capacity (bbl/d; not a boe/d plateau)",
            d.get("reported_oil_capacity_bpd"),
        ),
        "recoverable_reserves_mmboe": (
            "Recoverable resources (MMboe)",
            concept.recoverable_reserves_mmboe,
        ),
        "first_oil_year": ("Actual first-oil year", concept.year_first_oil),
    }
    rows = []
    for key, (label, value) in parameters.items():
        citation = d["input_sources"].get(key)
        if value is not None and not citation:
            raise ValueError(f"Missing input citation: {key}")
        basis = (
            f'<a href="#{html.escape(citation["source"], quote=True)}">'
            f'{html.escape(citation["source"])}</a>: '
            f'{html.escape(citation["comment"])}'
            if citation
            else "Required input; not established by the cited evidence."
        )
        display = "Unknown" if value is None else _display_value(value)
        rows.append(
            f"<tr><th>{html.escape(label)}</th><td>{html.escape(display)}</td>"
            f"<td>{basis}</td></tr>"
        )
    sources = "".join(
        f'<li id="{html.escape(key, quote=True)}">'
        f'<a href="{html.escape(source["url"], quote=True)}">'
        f'{html.escape(source["title"])}</a> '
        f'({html.escape(source["publication_date"])}; '
        f'{html.escape(source["kind"])}). '
        f'Retrieved {html.escape(source["accessed_at"])}; '
        f'HTTP {source["http_status"]}; SHA-256: {source["sha256"]}.</li>'
        for key, source in d["evidence"].items()
    )
    revisions = "".join(
        f'<tr><td>{html.escape(revision["revision"])}</td>'
        f'<td>{html.escape(revision["date"])}</td>'
        f'<td>{html.escape(revision["change"])}</td></tr>'
        for revision in d.get("revisions", [])
    )
    title = html.escape(f"Field Development Plan — {d['name']}")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><style>
body{{font-family:system-ui,sans-serif;background:#f4f6f9;color:#1a2330;margin:0}}
main{{max-width:1100px;margin:auto;padding:24px}}h2{{border-bottom:2px solid #d8e0ea}}
table{{border-collapse:collapse;width:100%;background:white}}
th,td{{border:1px solid #dde4ee;padding:8px;text-align:left;vertical-align:top}}
td,li{{overflow-wrap:anywhere}}a{{color:#234e78}}.narr{{line-height:1.6}}
</style></head><body><main>
<nav><a href="index.html">FDP portfolio</a></nav><h1>{title}</h1>
<h2>Summary</h2><p>{html.escape(d['summary'])}</p>
<p>Historical source snapshot, not a current operating-status assertion or a
sanctioned engineering design. Missing inputs are preserved as unknown.</p>
<h2>Revision history</h2>
<table><tr><th>Revision</th><th>Date</th><th>What changed and why</th></tr>
<tr><td>Initial</td><td>{html.escape(d['authored_date'])}</td>
<td>Documented the reported development concept and evidence gaps to provide
a field-level portfolio reference.</td></tr>
{revisions}</table>
<h2>Engineering rationale</h2><p class="narr">{html.escape(d['narrative'])}</p>
<h2>Field parameters</h2>
<table><tr><th>Input</th><th>Value</th><th>Source and scope</th></tr>
{''.join(rows)}</table>
<h2>Architecture</h2><p>{html.escape(d['architecture'])}</p>
<p>Well coordinates, manifold counts and interconnection lengths are required
inputs for a detailed layout. Layout: NOT_EVALUATED; no assumed geometry is drawn.</p>
<h2>Recommended concept shortlist</h2>
<p>NOT_EVALUATED. The reported concept is documented above; a comparative ranking
requires sourced screening limits and criteria weights.</p>
<h2>Economics and execution</h2>
<p>NOT_EVALUATED. No cost or investment return is inferred from facility capacity.
Required inputs include scope-matched capital cost, operating cost, production
profile, prices, discount rate and schedule. Equipment qualification and
installation feasibility also require project-specific design evidence.</p>
<h2>Known limits and way forward</h2><p>{html.escape(d['limitations'])}</p>
<h2>Sources</h2><p>Input citations refer to the source dates below. Capacity,
planned well count and forecast startup are not measured production.</p>
<ul>{sources}</ul>
</main></body></html>
"""


def _actuals(d: dict) -> dict:
    out = {}
    if d.get("host_facility"):
        out["Host"] = d["host_facility"]
    if d.get("reservoir_play"):
        out["Play"] = d["reservoir_play"]
    if d.get("first_oil_year"):
        out["First oil"] = d["first_oil_year"]
    if d.get("recoverable_reserves_mmboe"):
        out["Reserves"] = f"{d['recoverable_reserves_mmboe']:g} MMboe"
    if d.get("bsee_code"):
        out["BSEE code"] = d["bsee_code"]
    out["Confidence"] = d.get("confidence", "—")
    return out


def _narrative(d: dict) -> str:
    n = d.get("narrative", "")
    if d.get("notable"):
        n = f"{n}  Notable: {d['notable']}"
    return n


def _display_value(value) -> str:
    """Remove integer float padding without rounding fractional inputs."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def build_index(profiles: list[dict]) -> str:
    rows = []
    for d in profiles:
        ct = _concept_type(d)
        concept = ct.value if ct else "—"
        if d.get("evidence"):
            match = "NOT_EVALUATED"
        else:
            top = recommend(to_concept(d), top_n=1)
            match = "✓" if top and top[0].concept_type == ct else "✗"
        depth = d.get("water_depth_m")
        rows.append(
            f'<tr><td><a href="{_slug(d["name"])}.html">{html.escape(d["name"])}</a></td>'
            f"<td>{html.escape(concept)}</td>"
            f"<td>{html.escape(_display_value(depth) if depth is not None else '—')}</td>"
            f"<td>{html.escape(str(d.get('operator_current') or '—'))}</td>"
            f"<td>{html.escape(str(d.get('host_facility') or '—'))}</td>"
            f"<td>{html.escape(str(d.get('reservoir_play') or '—'))}</td>"
            f"<td>{html.escape(str(d.get('first_oil_year') or '—'))}</td>"
            f"<td>{match}</td></tr>"
        )
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Field Development Plan Portfolio — Deepwater GoM</title><style>
body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f4f6f9;
color:#1a2330}}.wrap{{max-width:1000px;margin:0 auto;padding:24px}}
h1{{font-size:24px}}table{{border-collapse:collapse;width:100%;background:#fff;
font-size:13px}}th,td{{border:1px solid #dde4ee;padding:7px 10px;text-align:left}}
th{{background:#eef2f7}}a{{color:#234e78}}.sub{{color:#5b6b80}}
</style></head><body><div class="wrap">
<h1>Field Development Plan Portfolio — Deepwater Gulf of Mexico</h1>
<p class="sub">{len(profiles)} fields. Legacy examples use the field-development
playbook (epic #567) for ranked concepts, schematics and illustrative economics.
The ✓/✗ column compares those model recommendations with the reported concept.
Documented profiles preserve cited facts and evidence gaps; their ranking,
schematics and economics are NOT_EVALUATED. Operator and capacity statements
are historical source snapshots.</p>
<table><tr><th>Field</th><th>Concept (reported)</th><th>Water depth (m)</th><th>Operator</th>
<th>Host</th><th>Reservoir play</th><th>First oil</th><th>Engine match</th></tr>
{''.join(rows)}</table>
<p class="sub" style="font-size:11px;margin-top:20px">Facts web-researched +
skeptically verified; schematics deterministic. Concept-Select / FEL-1 fidelity,
not sanctioned designs.</p></div></body></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source", nargs="?", type=Path, default=OUT_DIR / "_research.json"
    )
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--documented-only", action="store_true")
    args = parser.parse_args()
    src = args.source
    profiles = json.loads(Path(src).read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for d in profiles:
        if args.documented_only and not d.get("evidence"):
            continue
        page = build_profile_page(d)
        (args.output_dir / f"{_slug(d['name'])}.html").write_text(
            page, encoding="utf-8", newline="\n"
        )
        count += 1
    (args.output_dir / "index.html").write_text(
        build_index(profiles), encoding="utf-8", newline="\n"
    )
    print(f"wrote {count} FDPs + index")


if __name__ == "__main__":
    main()
