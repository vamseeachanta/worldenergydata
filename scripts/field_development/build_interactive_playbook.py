# ABOUTME: Render the self-contained interactive field-development playbook HTML.
# ABOUTME: Issue #644 (epic #567) — embeds precomputed grids + per-concept SVGs.
"""
Build the interactive field-development playbook (issue #644).

Produces a **single static HTML file** with no server and no CDN: the
recommendation engine is run offline over a parameter mesh (one grid per
region/fluid), and per-concept block + plan-view schematics are pre-rendered in
Python. All of it is embedded inline; client-side JS snaps the user's slider
values to the nearest grid point and shows the precomputed recommendation and
the matching schematics.

Run:
    .venv/bin/python scripts/field_development/build_interactive_playbook.py

Determinism: rebuilds are byte-identical except the footer build date. Set
``SOURCE_DATE_EPOCH`` (unix seconds) to pin the date for reproducible output.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
from pathlib import Path

from worldenergydata.field_development.block import render_block_diagram
from worldenergydata.field_development.enums import ConceptType, FluidType
from worldenergydata.field_development.interactive_grid import (
    build_recommendation_grid,
    grid_to_dict,
)
from worldenergydata.field_development.layout import render_layout
from worldenergydata.field_development.models import FieldConcept

OUT = (
    Path(__file__).parents[2]
    / "reports"
    / "field_development"
    / "interactive"
    / "playbook.html"
)

# Region dropdown: (label, region string fed to the basin prior). "" -> unknown.
REGIONS: list[tuple[str, str]] = [
    ("Gulf of Mexico", "us"),
    ("Brazil (Campos/Santos)", "brazil"),
    ("West Africa", "angola"),
    ("North Sea", "norway"),
    ("Australia / SE Asia", "australia"),
    ("Other / Unknown", ""),
]

FLUIDS: list[tuple[str, FluidType]] = [
    ("Oil", FluidType.OIL),
    ("Gas", FluidType.GAS),
    ("Condensate", FluidType.CONDENSATE),
    ("Gas-condensate", FluidType.GAS_CONDENSATE),
]

# Dry-tree (surface-tree) concepts attach wellheads to the host; the rest route
# subsea trees through a manifold. Canonical schematics use a single manifold.
_WET = {
    ConceptType.FPSO,
    ConceptType.FLNG,
    ConceptType.SEMISUB_FPS,
    ConceptType.SUBSEA_TIEBACK,
    ConceptType.SUBSEA_TO_SHORE,
}


def _canonical_concept(ct: ConceptType) -> FieldConcept:
    """A representative concept per type, for the pre-rendered schematics.

    The schematics are illustrative of the *concept's architecture*, not redrawn
    per slider value — a deliberate v1 scope choice (see the issue). Six wells
    and one manifold give a clean, legible diagram.
    """
    kw: dict = {
        "name": ct.value.replace("_", " ").title(),
        "concept_type": ct,
        "num_wells": 6,
    }
    if ct in _WET:
        kw["num_manifolds"] = 1
        kw["tieback_distance_km"] = 12.0 if ct == ConceptType.SUBSEA_TIEBACK else 4.0
    return FieldConcept(**kw)


def _build_svgs() -> dict[str, dict[str, str]]:
    """Pre-render block + plan-view SVGs for every concept type."""
    out: dict[str, dict[str, str]] = {}
    for ct in ConceptType:
        c = _canonical_concept(ct)
        out[ct.value] = {
            "block": render_block_diagram(c),
            "plan": render_layout(c),
        }
    return out


def _build_grids() -> dict[str, dict[str, dict]]:
    """Build one recommendation grid per (region, fluid) combination."""
    grids: dict[str, dict[str, dict]] = {}
    for _, region in REGIONS:
        rkey = region or "_unknown"
        grids[rkey] = {}
        for _, fluid in FLUIDS:
            grid = build_recommendation_grid(region=region or None, fluid=fluid)
            grids[rkey][fluid.value] = grid_to_dict(grid)
    return grids


def _embed(obj: object) -> str:
    """JSON for safe inlining inside a <script type=application/json> block."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).replace(
        "<", "\\u003c"
    )


def _build_date() -> str:
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        return _dt.datetime.utcfromtimestamp(int(epoch)).date().isoformat()
    return _dt.date.today().isoformat()


CONCEPT_LABELS = {ct.value: ct.value.replace("_", " ").title() for ct in ConceptType}

CSS = """
body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:0;color:#1a2330;
background:#f4f6f9}.wrap{max-width:1080px;margin:0 auto;padding:24px}
h1{font-size:24px;margin:0 0 4px}h2{font-size:16px;margin:18px 0 8px}
.sub{color:#5b6b80;margin:0 0 16px;font-size:13px}
.grid2{display:grid;grid-template-columns:340px 1fr;gap:20px}
@media(max-width:760px){.grid2{grid-template-columns:1fr}}
.panel{background:#fff;border:1px solid #dde4ee;border-radius:8px;padding:16px}
.ctrl{margin:0 0 14px}.ctrl label{display:block;font-size:12px;color:#6b7a90;
text-transform:uppercase;letter-spacing:.02em;margin-bottom:4px}
.ctrl .val{float:right;color:#234e78;font-weight:600;text-transform:none}
input[type=range]{width:100%}select{width:100%;padding:6px;border:1px solid #cdd6e2;
border-radius:5px;background:#fff;font-size:13px}
.rec{font-size:22px;font-weight:700;color:#234e78;margin:0 0 2px}
.score{color:#3a8f5a;font-weight:600}
ul{margin:6px 0 0;padding-left:18px;font-size:13px}li{margin:2px 0}
.warn li{color:#a4601a}
table{border-collapse:collapse;width:100%;background:#fff;font-size:13px;margin-top:4px}
th,td{border:1px solid #dde4ee;padding:6px 9px;text-align:left}th{background:#eef2f7}
tr.top td{background:#e8f3ea;font-weight:600}
.viz{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:8px}
@media(max-width:760px){.viz{grid-template-columns:1fr}}
.viz figure{margin:0;background:#fff;border:1px solid #dde4ee;border-radius:8px;
padding:12px;overflow:auto}.viz figcaption{font-size:12px;color:#5b6b80;
margin-top:6px}svg{max-width:100%;height:auto}
.foot{color:#7b8aa0;font-size:11px;margin-top:24px;line-height:1.5}
""".strip()

JS = """
const GRIDS=JSON.parse(document.getElementById('grids').textContent);
const SVGS=JSON.parse(document.getElementById('svgs').textContent);
const LABELS=JSON.parse(document.getElementById('labels').textContent);
function nearest(axis,v){let bi=0,bd=Math.abs(axis[0]-v);
for(let i=1;i<axis.length;i++){const d=Math.abs(axis[i]-v);if(d<bd){bd=d;bi=i;}}return bi;}
function fmtScore(s){return (s*100).toFixed(1);}
function el(id){return document.getElementById(id);}
function update(){
 const region=el('region').value, fluid=el('fluid').value;
 const depth=+el('depth').value, reserves=+el('reserves').value,
       tie=+el('tieback').value, wells=+el('wells').value;
 el('depthv').textContent=depth+' m';el('reservesv').textContent=reserves+' MMboe';
 el('tiebackv').textContent=(tie===0?'none (standalone)':tie+' km');
 el('wellsv').textContent=wells;
 const g=GRIDS[region][fluid];const a=g.axes;
 const di=nearest(a.depth,depth),ri=nearest(a.reserves,reserves),
       ti=nearest(a.tieback,tie),wi=nearest(a.wells,wells);
 const cell=g.cells[g.index[di][ri][ti][wi]];const top=cell.top;
 if(!top.length){el('rec').textContent='No feasible concept';el('rationale').innerHTML='';
  el('warnings').innerHTML='';el('shortlist').innerHTML='';el('viz').style.display='none';return;}
 const best=top[0];
 el('rec').textContent=LABELS[best.concept];
 el('recmeta').innerHTML='Score <span class="score">'+fmtScore(best.score)+
   '</span>/100 &middot; '+best.tree+' trees'+(best.topology?(' &middot; '+best.topology):'')+
   (best.processing.length?(' &middot; '+best.processing.join(', ')):'');
 el('rationale').innerHTML=best.rationale.map(t=>'<li></li>').join('');
 [...el('rationale').children].forEach((li,i)=>li.textContent=best.rationale[i]);
 el('warnings').innerHTML=best.warnings.map(()=>'<li></li>').join('');
 [...el('warnings').children].forEach((li,i)=>li.textContent=best.warnings[i]);
 el('warnbox').style.display=best.warnings.length?'block':'none';
 let rows='<tr><th>#</th><th>Concept</th><th>Score</th></tr>';
 top.forEach((c,i)=>{rows+='<tr class="'+(i===0?'top':'')+'"><td>'+(i+1)+
   '</td><td>'+LABELS[c.concept]+'</td><td>'+fmtScore(c.score)+'</td></tr>';});
 el('shortlist').innerHTML=rows;
 const sv=SVGS[best.concept];el('viz').style.display='grid';
 el('block').innerHTML=sv.block;el('plan').innerHTML=sv.plan;
}
['region','fluid','depth','reserves','tieback','wells'].forEach(id=>
 el(id).addEventListener('input',update));
update();
""".strip()


def _options(pairs: list[tuple[str, str]]) -> str:
    return "".join(f'<option value="{v}">{lbl}</option>' for lbl, v in pairs)


def render_html() -> str:
    """Assemble the complete self-contained playbook HTML string."""
    grids = _build_grids()
    svgs = _build_svgs()
    region_opts = _options([(lbl, v or "_unknown") for lbl, v in REGIONS])
    fluid_opts = _options([(lbl, f.value) for lbl, f in FLUIDS])
    date = _build_date()
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Field Development Concept Playbook</title><style>{CSS}</style></head>
<body><div class="wrap">
<h1>Offshore Field Development Concept Playbook</h1>
<p class="sub">Adjust the field parameters; the ranked concept recommendation,
rationale and schematics update live. Concept-Select / FEL-1 fidelity, not a
sanctioned design. Epic #567.</p>
<div class="grid2">
<div class="panel">
<h2>Field parameters</h2>
<div class="ctrl"><label>Region</label><select id="region">{region_opts}</select></div>
<div class="ctrl"><label>Fluid</label><select id="fluid">{fluid_opts}</select></div>
<div class="ctrl"><label>Water depth <span class="val" id="depthv"></span></label>
<input type="range" id="depth" min="0" max="3000" step="50" value="1300"></div>
<div class="ctrl"><label>Recoverable reserves <span class="val" id="reservesv"></span></label>
<input type="range" id="reserves" min="0" max="1000" step="10" value="150"></div>
<div class="ctrl"><label>Tieback distance to host <span class="val" id="tiebackv"></span></label>
<input type="range" id="tieback" min="0" max="200" step="5" value="0"></div>
<div class="ctrl"><label>Number of wells <span class="val" id="wellsv"></span></label>
<input type="range" id="wells" min="1" max="40" step="1" value="8"></div>
</div>
<div class="panel">
<h2>Recommended concept</h2>
<div class="rec" id="rec"></div><div class="sub" id="recmeta"></div>
<h2>Why</h2><ul id="rationale"></ul>
<div id="warnbox"><h2>Watch-outs</h2><ul class="warn" id="warnings"></ul></div>
<h2>Shortlist (top 3)</h2><table id="shortlist"></table>
</div></div>
<div class="viz" id="viz">
<figure><div id="block"></div><figcaption>Architecture block diagram</figcaption></figure>
<figure><div id="plan"></div><figcaption>Plan view (to scale)</figcaption></figure>
</div>
<p class="foot">Built {date}. Recommendations are precomputed offline by
<code>worldenergydata.field_development.recommend()</code> over a parameter mesh;
the browser snaps inputs to the nearest grid point — no engine code runs
client-side, so the result matches the Python engine exactly. Schematics are
representative per concept (6 wells, single manifold), not redrawn per slider.</p>
</div>
<script type="application/json" id="grids">{_embed(grids)}</script>
<script type="application/json" id="svgs">{_embed(svgs)}</script>
<script type="application/json" id="labels">{_embed(CONCEPT_LABELS)}</script>
<script>{JS}</script>
</body></html>"""


def main() -> Path:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render_html(), encoding="utf-8")
    return OUT


if __name__ == "__main__":
    path = main()
    print(f"wrote {path} ({path.stat().st_size / 1024:.0f} KB)")
