"""Build the offline field development module analysis through the public API.

Rebuild from the repository root:
    PYTHONPATH=src uv run --no-project --with pydantic --with pyyaml python \
        docs/reports/modules/wfielddevelopment/build_report.py
Use --output-dir to place an inspection copy outside the repository.
"""

from __future__ import annotations

import argparse
import ast
import json
import math
from dataclasses import asdict
from html import escape
from pathlib import Path

from worldenergydata.field_development import (
    CriteriaWeights,
    Thresholds,
    compute_pixel_positions,
    concept_to_graph,
    recommend,
    render_block_diagram,
    render_layout,
    sanity_check,
    validate_concept,
)
from worldenergydata.field_development.graph import NodeType
from worldenergydata.field_development.layout import TREE_RING_RADIUS_KM

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
EXAMPLE = "tests/modules/field_development/test_recommendation.py"
EXAMPLE_FUNCTION = "test_marginal_near_host_field_recommends_tieback"
SCALE_PX_PER_KM = 50.0  # Explicit presentation input, not an engineering limit.
EVIDENCE = {
    "Input contract": "test_field_concept.py",
    "Recommendation behavior": "test_recommendation.py",
    "Architecture connectivity": "test_graph.py",
    "Drawing scale": "test_layout.py",
    "Logical schematic": "test_block.py",
    "XML round trip": "test_dexpi.py",
    "Missing-data screening": "test_audit_screening.py",
    "Numeric and output regressions": "test_audit_outputs.py",
}
LABELS = {
    "subsea_tieback": "Subsea tieback",
    "subsea_to_shore": "Subsea to shore",
    "tlp": "Tension-leg platform",
    "spar": "Spar platform",
    "fpso": "Floating production, storage and offloading",
    "flng": "Floating liquefied natural gas",
    "semisub_fps": "Semisubmersible production system",
    "fixed_jacket": "Fixed jacket",
    "compliant_tower": "Compliant tower",
    "nui": "Normally unattended installation",
}
CRITERION_LABELS = {
    "capex": "Capital expenditure",
    "opex": "Operating expenditure",
    "schedule": "Schedule",
    "recovery": "Recovery",
    "flexibility": "Flexibility",
    "risk": "Risk favorability",
    "depth_fit": "Depth fit",
    "region_fit": "Regional fit",
}
CHANGES = {
    "revision": "A",
    "date": "2026-10-22",
    "changes": [
        {
            "section": "worked-example",
            "description": "Public near-host screening and schematic outputs are documented with configurable distance boundaries and arithmetic checks.",
            "reason": "Separate concept ranking and drawing behavior from engineering acceptance.",
        }
    ],
}


def example_inputs() -> dict:
    """Read the public example literals; preserve numbers and remove its label."""
    tree = ast.parse((ROOT / EXAMPLE).read_text(encoding="utf-8"))
    function = next(
        n
        for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == EXAMPLE_FUNCTION
    )
    call = next(
        n
        for n in ast.walk(function)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "FieldConcept"
    )
    values = {item.arg: ast.literal_eval(item.value) for item in call.keywords}
    values["name"] = "Illustrative near-host development"
    return values


def calculate() -> dict:
    """Call the module; no ranking or layout formula is duplicated here."""
    concept, input_violations = validate_concept(example_inputs())
    weights = CriteriaWeights()
    thresholds = Thresholds()
    ranked = recommend(concept, weights=weights, thresholds=thresholds)
    first = ranked[0]
    selected = concept.model_copy(
        update={
            "concept_type": first.concept_type,
            "tree_type": first.tree_type,
            "topology": first.topology,
            "tieback_distance_km": concept.distance_to_host_km,
        }
    )
    violations = sanity_check(selected)
    graph = concept_to_graph(selected)
    pixels = compute_pixel_positions(selected, graph, scale_px_per_km=SCALE_PX_PER_KM)
    manifold = next(n for n in graph.nodes if n.type == NodeType.MANIFOLD)
    separation = math.dist(pixels["host"], pixels[manifold.id])
    numbers = {
        "water_depth_m": concept.water_depth_m,
        "reserves_mmboe": concept.recoverable_reserves_mmboe,
        "host_distance_km": concept.distance_to_host_km,
        "wells": concept.num_wells,
        "nodes": len(graph.nodes),
        "edges": len(graph.edges),
        "manifolds": sum(n.type == NodeType.MANIFOLD for n in graph.nodes),
        "trees": sum(n.type == NodeType.TREE for n in graph.nodes),
        "input_violations": len(input_violations),
        "selected_violations": len(violations),
        "candidates": len(ranked),
        "separation_px": separation,
        "scale_px_per_km": SCALE_PX_PER_KM,
        "tree_radius_km": TREE_RING_RADIUS_KM,
        "warning_km": thresholds.flow_assurance_warn_km,
        "attractive_km": thresholds.tieback_max_km,
        "hard_limit_km": thresholds.tieback_hard_max_km,
        "marginal_mmboe": thresholds.tieback_marginal_mmboe,
    }
    for row in ranked:
        numbers[f"score.{row.concept_type.value}"] = round(row.total_score * 100, 2)
    criteria = []
    for key, weight in weights.as_dict().items():
        numbers[f"weight.{key}"] = weight
        numbers[f"criterion.{key}"] = first.scores[key]
        criteria.append({"key": key, "weight": weight, "score": first.scores[key]})
    sensitivity = []
    for distance in range(int(thresholds.tieback_hard_max_km) + 2):
        probe = concept.model_copy(update={"distance_to_host_km": float(distance)})
        tieback = next(
            (
                r
                for r in recommend(probe, weights, thresholds)
                if r.concept_type.value == "subsea_tieback"
            ),
            None,
        )
        sensitivity.append(
            {
                "distance_km": distance,
                "score_points": (
                    None if tieback is None else round(tieback.total_score * 100, 1)
                ),
            }
        )
    inventory = {}
    for label, filename in EVIDENCE.items():
        path = ROOT / "tests/modules/field_development" / filename
        tree = ast.parse(path.read_text(encoding="utf-8"))
        count = sum(
            isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and n.name.startswith("test_")
            for n in ast.walk(tree)
        )
        inventory[label] = {
            "file": path.relative_to(ROOT).as_posix(),
            "functions": count,
        }
    return {
        "numbers": numbers,
        "ranking": [row.concept_type.value for row in ranked],
        "criteria": criteria,
        "sensitivity": sensitivity,
        "inventory": inventory,
        "graph": graph.to_dict(),
        "layout_svg": render_layout(selected, graph, scale_px_per_km=SCALE_PX_PER_KM),
        "block_svg": render_block_diagram(graph),
        "thresholds": asdict(thresholds),
    }


def quantity(data: dict, key: str, precision: int = 1) -> str:
    printed = f'{data["numbers"][key]:,.{precision}f}'
    return (
        f'<span data-number="{key}" data-precision="{precision}" '
        f'data-display="{printed}">{printed}</span>'
    )


def sensitivity_chart(data: dict) -> str:
    hard = data["numbers"]["hard_limit_km"]
    xmax = data["sensitivity"][-1]["distance_km"]
    x = lambda distance: 58 + distance / xmax * 690
    y = lambda score: 242 - score * 2
    parts = [
        '<svg viewBox="0 0 800 310" role="img" aria-labelledby="chart-title chart-desc">',
        '<title id="chart-title">Tieback preference against host distance</title>',
        '<desc id="chart-desc">Module preference points with assumed warning, attractiveness and exclusion boundaries. Focus a point or use the distance control for its result.</desc>',
        '<path d="M58 40 V242 H748" fill="none" stroke="currentColor"/>',
    ]
    for tick in (0, 50, 100):
        parts.append(f'<text x="48" y="{y(tick)+4}" text-anchor="end">{tick}</text>')
    parts.append('<text x="58" y="22">Preference (points; higher is favored)</text>')
    for key, label in (
        ("warning_km", "Warning"),
        ("attractive_km", "Attractiveness"),
        ("hard_limit_km", "Exclusion"),
    ):
        value = data["numbers"][key]
        parts.append(
            f'<line data-limit="{key}" x1="{x(value):.1f}" x2="{x(value):.1f}" y1="40" y2="242" stroke="var(--caution)" stroke-dasharray="5 4"/>'
        )
        parts.append(
            f'<text x="{x(value):.1f}" y="{265 if key != "attractive_km" else 282}" text-anchor="middle">{label} {value:g} km</text>'
        )
    # Step segments expose discontinuities instead of interpolating a physical law.
    points = [p for p in data["sensitivity"] if p["score_points"] is not None]
    step = f'M{x(points[0]["distance_km"]):.1f},{y(points[0]["score_points"]):.1f}'
    for point in points[1:]:
        step += f'H{x(point["distance_km"]):.1f}V{y(point["score_points"]):.1f}'
    parts.append(
        f'<path d="{step}" fill="none" stroke="var(--brand)" stroke-width="2"/>'
    )
    for p in points:
        title = (
            f'Near-host case; component: tieback; demand: {p["distance_km"]} km; '
            f'exclusion limit: {hard:g} km; preference: {p["score_points"]:.1f} points. '
            "The limit is an assumed screening boundary."
        )
        parts.append(
            f'<circle tabindex="0" cx="{x(p["distance_km"]):.1f}" cy="{y(p["score_points"]):.1f}" r="3" fill="var(--brand)" aria-label="{title}"><title>{title}</title></circle>'
        )
    parts.append(
        '<text x="400" y="306" text-anchor="middle">Host distance (km)</text></svg>'
    )
    return "\n".join(parts)


INTERACTION = r"""
const reportData = JSON.parse(document.getElementById('module-report-data').textContent);
const changes = JSON.parse(document.getElementById('embedded-changes').textContent);
const distance = document.getElementById('distance');
function showDistance() {
  const point = reportData.sensitivity[Number(distance.value)];
  const n = reportData.numbers;
  const result = point.score_points === null ? 'The tieback is excluded.' : `Preference is ${point.score_points.toFixed(1)} points.`;
  document.getElementById('distance-result').textContent = `Near-host case; component: tieback; demand ${point.distance_km} km; exclusion limit ${n.hard_limit_km} km. ${result} The boundaries are assumed screening settings.`;
}
distance.addEventListener('input', showDistance);
showDistance();
const changeList = document.getElementById('change-list');
for (const entry of changes.changes) {
  const item = document.createElement('li');
  item.textContent = `${entry.description} ${entry.reason}`;
  changeList.append(item);
}
let comments = [];
function renderComments() {
  const list = document.getElementById('comment-list');
  list.replaceChildren();
  for (const item of comments) {
    const li = document.createElement('li');
    li.textContent = `${item.section}: ${item.text}`;
    list.append(li);
  }
}
const message = document.getElementById('comment-message');
document.getElementById('add-comment').addEventListener('click', () => {
  const text = document.getElementById('comment-text').value.trim();
  if (!text) { message.textContent = 'Enter a comment before adding it.'; return; }
  comments.push({section: document.getElementById('comment-section').value, text});
  document.getElementById('comment-text').value = '';
  renderComments();
  message.textContent = 'Comment added in memory. Save comments before closing the document.';
});
function commentFile() { return JSON.stringify({revision: changes.revision, comments}, null, 2) + '\n'; }
document.getElementById('save-comments').addEventListener('click', async () => {
  try {
    if (!window.showDirectoryPicker) {
      message.textContent = 'Folder saving is unavailable. Download comments and place the file beside this report.';
      return;
    }
    const folder = await window.showDirectoryPicker({mode: 'readwrite'});
    const file = await folder.getFileHandle('index.comments.json', {create: true});
    const writable = await file.createWritable();
    await writable.write(commentFile());
    await writable.close();
    message.textContent = 'Comments saved beside the report in the selected folder.';
  } catch (error) {
    message.textContent = 'Saving did not complete. Comments remain in memory; download them before closing.';
  }
});
document.getElementById('download-comments').addEventListener('click', () => {
  const link = document.createElement('a');
  const url = URL.createObjectURL(new Blob([commentFile()], {type: 'application/json'}));
  link.href = url; link.download = 'index.comments.json'; link.click();
  URL.revokeObjectURL(url);
  message.textContent = 'Comments downloaded. Place index.comments.json beside the report.';
});
document.getElementById('load-comments').addEventListener('change', async event => {
  if (!event.target.files.length) return;
  try {
    const record = JSON.parse(await event.target.files[0].text());
    const allowed = new Set(Array.from(document.getElementById('comment-section').options).map(o => o.value));
    if (record.revision !== changes.revision || !Array.isArray(record.comments) ||
        !record.comments.every(c => typeof c.text === 'string' && allowed.has(c.section))) throw new Error('Invalid record');
    comments = record.comments.map(c => ({section: c.section, text: c.text}));
    renderComments(); message.textContent = 'Saved comments loaded.';
  } catch (error) { message.textContent = 'The comment file is invalid or has a different revision. Existing comments remain in memory.'; }
});
"""


def build(output_dir: Path = HERE) -> None:
    data = calculate()
    q = lambda key, precision=1: quantity(data, key, precision)
    sources = json.loads((HERE / "sources.json").read_text(encoding="utf-8"))
    style = (HERE / "house-style.css").read_text(encoding="utf-8").strip()
    inputs = "".join(
        f'<tr><td>{label}</td><td>{q(key, precision)}</td><td>{unit}</td><td><a href="#source-example">Public example</a></td></tr>'
        for key, label, unit, precision in (
            ("water_depth_m", "Water depth", "m", 0),
            (
                "reserves_mmboe",
                "Recoverable reserves",
                "million barrels of oil equivalent",
                0,
            ),
            ("host_distance_km", "Host distance", "km", 0),
            ("wells", "Well count", "wells", 0),
        )
    )
    ranking = "".join(
        f'<tr><td>{escape(LABELS[key])}</td><td>{q("score." + key)}</td><td><a href="#source-scoring">Module output</a></td></tr>'
        for key in data["ranking"]
    )
    criteria = "".join(
        f'<tr><td>{CRITERION_LABELS[row["key"]]}</td><td>{q("weight." + row["key"], 2)}</td><td>{q("criterion." + row["key"], 2)}</td><td><a href="#source-scoring">Assumed scoring inputs</a></td></tr>'
        for row in data["criteria"]
    )
    evidence = "".join(
        f'<tr><td>{label}</td><td>{record["functions"]}</td><td>{escape(record["file"])}</td></tr>'
        for label, record in data["inventory"].items()
    )
    source_rows = [
        (
            "source-example",
            "Public near-host example",
            EXAMPLE + " :: " + EXAMPLE_FUNCTION,
            "Synthetic public software example, using the repository edition accompanying this report; no measured field is represented.",
        ),
        (
            "source-contract",
            "Input contract and sanity checks",
            "src/worldenergydata/field_development/models.py; loader.py; sanity.py",
            "FieldConcept, validate_concept and sanity_check; repository edition accompanying this report. Empty findings do not establish complete input data.",
        ),
        (
            "source-scoring",
            "Recommendation and scoring configuration",
            "src/worldenergydata/field_development/recommendation.py; basin.py",
            "recommend, CriteriaWeights, Thresholds, profiles, depth bands and regional priors; repository edition accompanying this report. All defaults are ASSUMED - to be confirmed for engineering use.",
        ),
        (
            "source-graph",
            "Architecture and drawing implementation",
            "src/worldenergydata/field_development/graph.py; layout.py; block.py; symbols/",
            "concept_to_graph, compute_pixel_positions, render_layout and render_block_diagram; repository edition accompanying this report. Well rings and export offsets are presentation conventions.",
        ),
        (
            "source-evidence",
            "Existing validation evidence",
            "tests/modules/field_development/; src/worldenergydata/field_development/docs/agent-pack.md",
            "The inventory below identifies selected tests. Geometry and XML checks establish software behavior. No measured engineering benchmark is supplied for this example.",
        ),
        (
            "source-calibration",
            "Calibration scope",
            "src/worldenergydata/field_development/calibration.py; recommendation.py; docs/domains/field-development/calibration-v2.md",
            "Depth bands were fitted without a train/test holdout. Historical catalog fit is not an estimate of unseen-field prediction performance; this report does not recalculate the catalog.",
        ),
        (
            "source-integrations",
            "Other public interfaces",
            "src/worldenergydata/field_development/__init__.py; integrations.py; cost_estimator.py; flow_assurance.py; layout_optimization.py",
            "Package exports and supporting interfaces; repository edition accompanying this report. Economics, hazards and optimized routing are outside the worked example.",
        ),
    ]
    references = "".join(
        f'<li id="{key}">{title}. <code>{escape(locator)}</code>. {description}</li>'
        for key, title, locator, description in source_rows
    )
    for key in ("manual", "svg"):
        source = sources[key]
        references += f'<li id="source-{key}"><a href="{source["url"]}">{escape(source["title"])}</a>, {escape(source["edition"])}; {escape(source["sections"])}. {escape(source["use"])}</li>'
    references += '<li id="source-style">House style: established engineering report layout, from the companion calculation documentation; exemplar <code>docs/api/cfd/turbulent-flat-plate-verification.html</code> and shared palette <code>docs/api/_assets/brand.css</code>. The copied stylesheet is supplied beside this report and inlined here. No matching house-style page exists in this repository at the report basis.</li>'
    embedded = {k: v for k, v in data.items() if not k.endswith("_svg")}
    sections = (
        ("summary", "1 Executive Summary"),
        ("introduction", "2 Introduction"),
        ("workflow", "3 Workflow, inputs and outputs"),
        ("basis", "4 Basis and criteria"),
        ("method", "5 Theory and methodology"),
        ("worked-example", "6 Worked example"),
        ("validation", "7 Validation evidence"),
        ("recommendations", "8 Limits and recommendations"),
        ("appendix", "9 Appendices and references"),
        ("comments", "10 Comments and changes"),
    )
    navigation = " · ".join(f'<a href="#{key}">{title}</a>' for key, title in sections)
    options = "".join(
        f'<option value="{key}">{title}</option>' for key, title in sections
    )
    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="light"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Field development module analysis</title>
<style>{style}</style>
<style>
svg{{max-width:100%;height:auto}} figure{{overflow:auto}} svg text{{font:12px sans-serif}}
.chart{{border:1px solid var(--edge);border-radius:6px;padding:10px}} input[type=range]{{width:100%}}
textarea{{display:block;width:100%;min-height:90px}} button,select,input{{font:inherit;margin:5px 0}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere}} td{{vertical-align:top}} .refs code{{overflow-wrap:anywhere}}
</style></head><body class="hs-doc"><main class="wrap">
<header><div class="kicker">Engineering module analysis</div>
<h1>Field development module analysis</h1>
<p class="sub">Concept screening, architecture connectivity and schematic scale</p>
<p>Draft for maintainer review</p></header>
<nav aria-label="Report sections">{navigation}</nav>

<h2 id="summary">1 Executive Summary</h2>
<p>The field development module is a deterministic offshore concept-screening and schematic tool. Analysis is performed to determine a concept shortlist and its schematic outputs; key results are summarized below.</p>
<ul><li>The public near-host example is ranked as a subsea tieback.
<ul><li>A preference of {q('score.subsea_tieback')} points is returned for a host distance of {q('host_distance_km', 0)} km. The configured distance exclusion is {q('hard_limit_km', 0)} km; no engineering acceptance threshold is defined for the preference score. <a href="#source-example">Example</a>; <a href="#source-scoring">scoring basis</a>.</li>
<li>The returned architecture contains {q('nodes', 0)} nodes and {q('edges', 0)} directed connections. These counts establish schematic connectivity, with no pressure, thermal, structural or capacity acceptance implied. <a href="#source-graph">Architecture basis</a>.</li></ul></li>
<li>A concept shortlist is available for engineering discussion.
<ul><li>Engineering selection is withheld until host capacity, fluid properties, route data and preference settings are supplied and assessed. The boundaries used here are ASSUMED - to be confirmed. <a href="#basis">Basis</a>; <a href="#recommendations">recommendations</a>.</li></ul></li></ul>
<h3>Revision history</h3>
<table><thead><tr><th>Revision</th><th>Date</th><th>Change and reason</th></tr></thead><tbody>
<tr><td>A</td><td>{CHANGES['date']}</td><td>Document public screening and schematic behavior to distinguish arithmetic evidence from engineering acceptance.</td></tr></tbody></table>

<h2 id="introduction">2 Introduction</h2>
<p>The offshore screening workflow is examined from concept input to ranked alternatives and schematic output. A synthetic example already published in the repository is used; no operating development or installation is represented. <a href="#source-example">Example record</a>; <a href="#source-integrations">module scope</a>.</p>
<p>The main workflow is covered in full for the stated input set. A documented public class, public functions and existing tests are present, so a worked calculation is presented rather than a readiness-only assessment. <a href="#source-contract">Public entry points</a>; <a href="#source-evidence">test evidence</a>.</p>
<h3>Not covered</h3>
<p>Catalog joins, analog matching, historical calibration, terrain acquisition, production economics, equipment geometry, installation suitability, optimized routing and text-assisted concept completion are outside this calculation. Their availability in the package does not establish their qualification for engineering selection. <a href="#source-integrations">Interface inventory</a>; <a href="#source-calibration">calibration limits</a>.</p>

<h2 id="workflow">3 Workflow, inputs and outputs</h2>
<p>Field data are represented by the public concept model, and single-field validation is followed by cross-field checks. Ranking and schematic generation are separate calls; a ranked result is explicitly transferred into a concept before the drawings are generated. <a href="#source-contract">Input contract</a>; <a href="#source-scoring">ranking</a>; <a href="#source-graph">rendering</a>.</p>
<p>The reader supplies depth in metres, distance in kilometres, reserves in million barrels of oil equivalent, integer well counts and an explicit host-capacity statement. Only a name is mandatory in the model, so a successfully constructed sparse object is not a complete design basis. <a href="#source-contract">Model fields and checks</a>.</p>
<p>The outputs are a descending concept shortlist with criterion scores, rationale and warnings; cross-field violation records; a graph of typed equipment and connections; and vector schematics. The drawing coordinates are synthetic. The example input register and all ranked outputs are given in the appendix. <a href="#source-scoring">Ranking contract</a>; <a href="#source-graph">schematic contract</a>.</p>

<h2 id="basis">4 Basis and criteria</h2>
<p>The calculation basis is restricted to the public near-host example and the repository's default screening configuration. The weighted-average method is supported by the cited manual; the chosen preference weights and field-development boundaries are assumptions, with no physical acceptance inferred from that manual. <a href="#source-manual">Method source</a>; <a href="#source-scoring">configuration source</a>.</p>
<p>The example water depth is {q('water_depth_m', 0)} m, recoverable reserves are {q('reserves_mmboe', 0)} million barrels of oil equivalent and host spare capacity is explicitly present. A well count of {q('wells', 0)} is supplied. These are synthetic inputs, not measurements. <a href="#source-example">Public example</a>.</p>
<p>The configured warning distance is {q('warning_km', 0)} km, the attractiveness boundary is {q('attractive_km', 0)} km and the tieback exclusion distance is {q('hard_limit_km', 0)} km. The marginal-reserve boundary is {q('marginal_mmboe', 0)} million barrels of oil equivalent. Each default is ASSUMED - to be confirmed; these values are screening settings rather than hydraulic or thermal operating limits. <a href="#source-scoring">Threshold definitions</a>.</p>
<p>A positive weight sum and consistently oriented criterion scales are required for interpretation of the weighted average. Mutual preference independence is required by the cited method and has not been established for the repository profiles. Host-capacity feasibility remains a supplied statement. <a href="#source-manual">Method conditions</a>; <a href="#source-scoring">implementation</a>.</p>

<h2 id="method">5 Theory and methodology</h2>
<p>Candidate concepts are filtered by configured depth envelopes and host reachability, then ordered by a normalized weighted sum. Preference scores are used for comparison within this configuration; they are neither probabilities nor financial returns. <a href="#source-scoring">Filtering and scoring</a>.</p>
<div class="eq">Sᵢ = Σⱼ(wⱼ sᵢⱼ) / Σⱼwⱼ</div>
<p>Here Sᵢ is the normalized preference for candidate i, sᵢⱼ is its dimensionless score on criterion j, and wⱼ is that criterion's dimensionless weight. The appendix provides the weights and leading candidate scores at their calculation precision. The displayed preference in points is the normalized value expressed on a percentage scale, without a probability interpretation. <a href="#source-manual">January 2009 manual, overall weighted scores</a>; <a href="#source-scoring">module implementation</a>.</p>
<p>Graph connectivity is assembled by routing each wet tree through a manifold to the host, with control connections in the opposite direction and a separate export connection. This is architecture bookkeeping rather than a pipe-network solution. <a href="#source-graph">Connectivity rules</a>.</p>
<div class="eq">X = s x; Y = −s y; D = s d</div>
<p>Here x and y are schematic coordinates in kilometres, positive north along y; X and Y are drawing coordinates in pixels; s is the presentation scale in pixels per kilometre; d is the axis-aligned host offset in kilometres; and D is its drawing separation in pixels. The sign reversal matches the downward drawing axis. Translation for the drawing margin does not change separation. <a href="#source-svg">Coordinate and transform standard</a>; <a href="#source-graph">implemented mapping</a>.</p>
<p>The chosen drawing scale is {q('scale_px_per_km', 0)} pixels per kilometre, an explicit presentation input. The default well-ring radius is {q('tree_radius_km')} km, ASSUMED - to be confirmed as a presentation convention. No well coordinates, route geometry, mesh or physical boundary conditions are solved. <a href="#source-graph">Drawing conventions</a>.</p>

<h2 id="worked-example">6 Worked example</h2>
<p>The public example is calculated by calling the concept validation, ranking, graph and rendering interfaces. The leading candidate's architecture and the supplied host distance are transferred into the selected concept, followed by another sanity check. <a href="#source-example">Example</a>; <a href="#source-contract">validation</a>; <a href="#source-graph">architecture</a>.</p>
<p>The module returns {q('candidates', 0)} ranked candidates. The leading subsea tieback preference is {q('score.subsea_tieback')} points. The input and selected concept produce {q('input_violations', 0)} and {q('selected_violations', 0)} cross-field findings respectively; missing engineering data remain unresolved. <a href="#source-scoring">Ranking output</a>; <a href="#source-contract">sanity rules</a>.</p>
<p>The returned schematic contains {q('trees', 0)} subsea trees and {q('manifolds', 0)} routing manifold, with {q('nodes', 0)} total nodes and {q('edges', 0)} directed connections. The host-to-manifold drawing separation is {q('separation_px', 0)} pixels at the stated scale. The manifold count is a drawing default, not an engineered equipment selection. <a href="#source-graph">Graph and scale output</a>.</p>
<figure>{data['layout_svg']}<figcaption>Plan-view symbol schematic returned by the module. Host offset is scaled; well positions, north orientation and export offset are schematic. No surveyed route, depth profile or seabed clearance is represented. <a href="#source-graph">Geometry source</a>.</figcaption></figure>
<details><summary>Logical production and control connections</summary><figure>{data['block_svg']}<figcaption>Logical connectivity returned by the module; the boxes represent equipment functions, with no physical dimensions. Solid production, dashed control and export connections are distinguished by the renderer. <a href="#source-graph">Connectivity source</a>.</figcaption></figure></details>
<div class="chart">{sensitivity_chart(data)}
<label for="distance">Select a calculated host distance</label>
<input id="distance" type="range" min="0" max="{len(data['sensitivity'])-1}" value="{int(data['numbers']['host_distance_km'])}" step="1">
<p id="distance-result" aria-live="polite"></p></div>
<p>Only host distance is changed in the sensitivity chart; depth, reserves, host-capacity statement, weights and all other example data are held fixed. The warning is applied above its boundary, attractiveness changes above its boundary, and exclusion is applied above the configured maximum. The line is drawn as steps because the calculation is heuristic. The zero-distance endpoint exposes ranking behavior only; a selected tieback without positive distance is rejected by the separate sanity gate. No engineering acceptance line is defined for preference points. <a href="#source-scoring">Boundary comparisons</a>.</p>

<h2 id="validation">7 Validation evidence</h2>
<p>The repository's existing evidence is separated into input checks, heuristic behavior, connectivity, scale arithmetic and serialization. The appendix inventories the selected test functions; function counts are not executed-case counts because parametrization expands some tests. <a href="#source-evidence">Evidence basis</a>.</p>
<p>Existing tests check the expected near-host concept, ranking order, configuration overrides, tree-to-manifold connectivity, distance scaling, drawing structure and an extensible-markup round trip. These are software and arithmetic checks. A published measured benchmark for the public synthetic example is not supplied, and agreement with field performance is NOT_EVALUATED. <a href="#source-evidence">Tests and qualification record</a>.</p>
<p>Historical reference data and a calibration harness are present, but the depth priors were set using the same catalog evaluated by the harness. No held-out engineering prediction claim is made, and historical percentages are not reused as current results. <a href="#source-calibration">Calibration disclosure</a>.</p>
<p>The accompanying report tests contain hand-worked score, node-count, connection-count and distance-scale anchors. The remaining module-to-page comparisons are consistency checks, including every sensitivity point and every tagged displayed number. An exact document rebuild is checked only after numeric arrays and drawing coordinates have been rounded for presentation. <a href="#qa">Quality evidence</a>.</p>

<h2 id="recommendations">8 Limits and recommendations</h2>
<p>Use is limited to early concept discussion and schematic communication under explicit screening assumptions. Engineering acceptance remains NOT_EVALUATED for hydraulic behavior, thermal behavior, structural response, production capacity and economic selection. <a href="#source-integrations">Calculation scope</a>; <a href="#source-evidence">evidence boundary</a>.</p>
<p>Before selecting a tieback, obtain host capacity and receiving-condition data, fluid composition, operating rates and pressures, shutdown and restart requirements, route survey and governing acceptance criteria. Replace the assumed distance settings with criteria established by the appropriate flow, thermal, mechanical and commercial analyses; distance alone does not demonstrate operability. The repository's separate screening interfaces are not a substitute for those analyses. <a href="#source-integrations">Supporting interface limitations</a>.</p>
<p>Before relying on the ranking, agree the criterion scales and weights with the engineering decision team, test for overlapping preferences and perform sensitivity analysis. The cited manual identifies preference independence as a condition for additive scoring. <a href="#source-manual">Method conditions</a>.</p>
<p>The recommended next evidence slice is a public, fully specified tieback benchmark with documented receiving conditions, independently calculated pressure and temperature results, and acceptance criteria. Ranking qualification is then assessed on a held-out catalog with explicit host data. Until that evidence is supplied, release remains restricted to screening and schematic use. <a href="#source-evidence">Current gaps</a>; <a href="#source-calibration">holdout gap</a>.</p>

<h2 id="appendix">9 Appendices and references</h2>
<p>The data register, source locators and calculation evidence are provided for inspection. Assumptions are stated at the point of use and are not promoted to physical limits.</p>
<h3>9.1 Data register and complete example outputs</h3>
<table><thead><tr><th>Input</th><th>Value</th><th>Unit</th><th>Source</th></tr></thead><tbody>{inputs}</tbody></table>
<table><thead><tr><th>Data item</th><th>Status and treatment</th><th>Source</th></tr></thead><tbody>
<tr><td>Host spare capacity</td><td>True in the synthetic example; no capacity value is supplied.</td><td><a href="#source-example">Example</a></td></tr>
<tr><td>Distance mapping</td><td>The supplied host distance is transferred to tieback distance for drawing; no route length is inferred.</td><td><a href="#source-example">Example</a>; <a href="#source-graph">drawing contract</a></td></tr>
<tr><td>Weights, profiles, depth priors and distance settings</td><td>ASSUMED - to be confirmed; repository defaults are used for screening only.</td><td><a href="#source-scoring">Configuration</a></td></tr>
<tr><td>Drawing manifold and well geometry</td><td>ASSUMED - to be confirmed; default routing and well-ring positions are used for presentation only.</td><td><a href="#source-graph">Drawing defaults</a></td></tr>
<tr><td>Region, fluid, rates, pressures, temperatures and metocean</td><td>Required for engineering selection; absent from the synthetic input. Physical acceptance is NOT_EVALUATED. Regional score is neutral when region is absent.</td><td><a href="#source-contract">Inputs</a>; <a href="#source-scoring">neutral prior</a></td></tr>
<tr><td>Measured benchmark and governing design criteria</td><td>Required for engineering qualification; NOT_EVALUATED here.</td><td><a href="#source-evidence">Evidence boundary</a></td></tr>
</tbody></table>
<table><thead><tr><th>Candidate</th><th>Preference (points)</th><th>Source</th></tr></thead><tbody>{ranking}</tbody></table>
<table><thead><tr><th>Criterion</th><th>Weight (dimensionless)</th><th>Leading score (dimensionless)</th><th>Source</th></tr></thead><tbody>{criteria}</tbody></table>
<h3>9.2 Sources and evidence locators</h3>
<ol class="refs">{references}</ol>
<table><thead><tr><th>Existing evidence group</th><th>Defined test functions</th><th>Source</th></tr></thead><tbody>{evidence}</tbody></table>
<h3 id="qa">9.3 Quality evidence and rebuilding</h3>
<p>The arithmetic anchors check the weighted score, node count, connection count and drawing separation against hand-worked literals. Absolute floating-point tolerance is stated in each test; counts are exact. The displayed criterion inputs are also recombined to the displayed headline precision. No solver or external service is used by the calculation.</p>
<p>The report checks cover offline assets, section and reference integrity, default boundary behavior, every tagged displayed value and document rebuilding. Script behavior is checked with a simulated document, including distance selection and comment-file round trips. Browser execution is not part of this evidence: folder permissions and rendered chart behavior require an interactive review before general distribution.</p>
<p>Rebuild from the repository root using the command below. The module dependencies are Pydantic and the YAML reader; the surrounding environment supplies the package source path.</p>
<pre>PYTHONPATH=src uv run --no-project --with pydantic --with pyyaml python docs/reports/modules/wfielddevelopment/build_report.py</pre>
<p>The module report tests are located in <code>tests/modules/field_development/test_module_report.py</code>. The change record is <code>changes.json</code>, embedded below for offline viewing. Source-access records are provided in <code>sources.json</code>. Text files use UTF-8 encoding and line-feed line endings.</p>

<h2 id="comments">10 Comments and changes</h2>
<p>Section comments are stored separately from the analysis. The engineering change panel describes changes in scope and evidence since the preceding revision.</p>
<details open><summary>Engineering changes in revision {CHANGES['revision']}</summary><ul id="change-list"></ul></details>
<p>Select the folder containing this report to save <code>index.comments.json</code> beside it. Where folder saving is unavailable, download the comments and place that file beside the report. Saved comments are loaded with the file selector. Unsaved comments exist only in memory.</p>
<label for="comment-section">Report section</label><select id="comment-section">{options}</select>
<label for="comment-text">Comment</label><textarea id="comment-text"></textarea>
<button id="add-comment" type="button">Add comment</button>
<button id="save-comments" type="button">Save beside report</button>
<button id="download-comments" type="button">Download comments</button>
<label for="load-comments">Load saved comments</label><input id="load-comments" type="file" accept="application/json">
<p id="comment-message" aria-live="polite"></p><ul id="comment-list"></ul>
<footer>Field development module analysis. Screening and schematic use only; engineering acceptance is not evaluated.</footer>
<script type="application/json" id="module-report-data">{json.dumps(embedded, ensure_ascii=False, sort_keys=True, allow_nan=False)}</script>
<script type="application/json" id="embedded-changes">{json.dumps(CHANGES, ensure_ascii=False, sort_keys=True)}</script>
<script>{INTERACTION}</script>
</main></body></html>
"""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "index.html").write_text(html, encoding="utf-8", newline="\n")
    (output_dir / "changes.json").write_text(
        json.dumps(CHANGES, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=HERE)
    build(parser.parse_args().output_dir)
