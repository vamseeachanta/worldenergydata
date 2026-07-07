#!/usr/bin/env python3
"""ABOUTME: Generate the GoM field-atlas browse page (Country→Domain→Region→Play→Field).
ABOUTME: Reads _roster.json (120 concept-matched fields) → interactive filter page (epic #764, issue #766).

The atlas is the browse funnel / front-of-house: it scales the flat capabilities list
into a filterable field catalog with honest density tiers (rich = has a life-cycle hub;
sample = concept data only; roadmap = name/block only). Rich fields link straight to
their life-cycle poster. The long tail (the full 1,390-field GoM atlas) is noted, not
rendered as links.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
import site_nav  # noqa: E402  (nav-spine helper, issue #850)

# Field identity resolves through THE canonical registry (config/fields.yml via
# worldenergydata.common.fields_registry) — no local name→id map lives here (#755).
from worldenergydata.common.fields_registry import load_fields  # noqa: E402

HERE = Path(__file__).resolve().parents[2] / "reports/field-atlas"
ROSTER = HERE / "_roster.json"


def build() -> str:
    fields = json.loads(ROSTER.read_text())
    registry = load_fields()
    for f in fields:
        f["lifecycle_id"] = (
            registry.resolve(f["name"]) if f.get("has_lifecycle") else None
        )
    roster_json = json.dumps(fields, ensure_ascii=False)
    return site_nav.inject_for(
        TEMPLATE.replace("__ROSTER_JSON__", roster_json), "atlas"
    )


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GoM Field Atlas — worldenergydata</title>
<style>
  :root{--navy:#0B3D91;--teal:#0f8a7e;--bg:#eef3fa;--panel:#fff;--ink:#13233f;--muted:#5b6b86;
        --line:#dbe4f0;--soft:#f4f8fc;--rich:#1f9d57;--sample:#b7791f;--roadmap:#8a97ab}
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,"Segoe UI",Roboto,Arial,sans-serif;background:var(--bg);color:var(--ink);line-height:1.5}
  a{color:inherit;text-decoration:none}
  .wrap{max-width:1180px;margin:0 auto;padding:36px 22px 80px}
  .eyebrow{font-family:ui-monospace,monospace;font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
  h1{font-size:30px;font-weight:800;letter-spacing:-.4px;color:var(--navy);margin:6px 0 8px}
  .lede{color:var(--muted);font-size:16px;max-width:760px}
  .story{display:inline-block;margin-top:14px;background:#fff;border:1px solid var(--line);border-left:4px solid var(--teal);
         border-radius:10px;padding:10px 16px;font-size:14px}
  .story b{color:var(--navy)}
  .funnel{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:26px 0 6px;
          background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px 16px}
  .funnel label{font-family:ui-monospace,monospace;font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);display:block;margin-bottom:3px}
  .funnel select,.funnel input{font:inherit;font-size:14px;padding:7px 10px;border:1px solid var(--line);border-radius:9px;background:var(--soft);color:var(--ink)}
  .funnel .grp{display:flex;flex-direction:column}
  .funnel .arrow{color:var(--muted);align-self:end;padding-bottom:8px}
  .funnel input[type=search]{min-width:190px}
  .tiers{display:flex;gap:8px;margin:14px 0 4px;flex-wrap:wrap}
  .tierbtn{font-family:ui-monospace,monospace;font-size:12px;font-weight:700;padding:6px 12px;border-radius:20px;border:1px solid var(--line);background:#fff;color:var(--muted);cursor:pointer}
  .tierbtn.on{background:var(--navy);color:#fff;border-color:var(--navy)}
  .count{font-family:ui-monospace,monospace;font-size:13px;color:var(--muted);margin:10px 2px}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:15px 17px;display:flex;flex-direction:column;
        box-shadow:0 1px 2px rgba(16,40,80,.04);transition:transform .12s,border-color .12s,box-shadow .12s}
  .card:hover{transform:translateY(-2px);border-color:#b9cbe6;box-shadow:0 8px 20px rgba(16,40,80,.09)}
  .card h3{font-size:15.5px;font-weight:700;color:var(--ink);display:flex;align-items:center;gap:8px;justify-content:space-between}
  .badge{font-family:ui-monospace,monospace;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;padding:3px 8px;border-radius:20px;white-space:nowrap}
  .badge.rich{color:var(--rich);background:color-mix(in srgb,var(--rich) 12%,#fff);border:1px solid color-mix(in srgb,var(--rich) 35%,#fff)}
  .badge.sample{color:var(--sample);background:color-mix(in srgb,var(--sample) 12%,#fff);border:1px solid color-mix(in srgb,var(--sample) 35%,#fff)}
  .badge.roadmap{color:var(--roadmap);background:#f2f5f9;border:1px solid var(--line)}
  .card .meta{font-size:12.5px;color:var(--muted);margin-top:5px}
  .card .meta b{color:var(--ink);font-weight:600}
  .card .concept{font-size:12.5px;color:var(--teal);font-weight:600;margin-top:6px}
  .card .go{margin-top:12px}
  .card .go a{font-size:13px;font-weight:700;color:#fff;background:linear-gradient(135deg,var(--teal),var(--navy));padding:6px 12px;border-radius:9px;display:inline-block}
  .card .go span{font-size:12px;color:var(--muted);font-family:ui-monospace,monospace}
  .note{margin-top:26px;font-size:13px;color:var(--muted);background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 18px}
  .note b{color:var(--navy)}
  @media (prefers-color-scheme:dark){
    :root{--bg:#0a141f;--panel:#10202f;--ink:#e8eef4;--muted:#8ca0b3;--line:#24384b;--soft:#0d1b28;--navy:#5b9de0;--teal:#3fb99b}
    .badge.roadmap{background:#182636}.card .go a{color:#08131f}
  }
</style>
</head>
<body>
<div class="wrap">
  <p class="eyebrow">worldenergydata · browse the field atlas</p>
  <h1>Gulf of Mexico Field Atlas</h1>
  <p class="lede">Browse deepwater fields top-down — Country → onshore/offshore → Region → geological play → field.
     Fields with a full life-cycle analysis link straight to their stage-gate hub.</p>
  <div class="story">The <b>Lower Tertiary (Wilcox)</b> play is ~8% of GoM fields but holds <b>~36% of the oil</b> — start there.</div>

  <div class="funnel">
    <div class="grp"><label>Country</label><select id="f-country"></select></div>
    <span class="arrow">→</span>
    <div class="grp"><label>Domain</label><select id="f-domain"></select></div>
    <span class="arrow">→</span>
    <div class="grp"><label>Region</label><select id="f-region"></select></div>
    <span class="arrow">→</span>
    <div class="grp"><label>Play</label><select id="f-play"></select></div>
    <div class="grp" style="margin-left:auto"><label>Search</label><input id="f-search" type="search" placeholder="field or block…"></div>
  </div>
  <div class="tiers" id="f-tiers"></div>
  <div class="count" id="f-count"></div>
  <div class="grid" id="f-grid"></div>

  <div class="note">Showing the <b>120 concept-matched</b> Gulf of Mexico fields. The full GoM atlas holds
     <b>1,390 fields</b> (Lower Tertiary = 111 fields, ~36% of GoM oil); the long tail is a searchable catalog, not shown here.
     Density: <b style="color:var(--rich)">rich</b> = life-cycle hub + economics · <b style="color:var(--sample)">sample</b> = concept data · <b style="color:var(--roadmap)">roadmap</b> = name/block only.</div>
</div>

<script>
const ROSTER = __ROSTER_JSON__;
const TIER_ORDER = {rich:0, sample:1, roadmap:2};
const $ = id => document.getElementById(id);
let tierFilter = "all";

function uniq(key){ return [...new Set(ROSTER.map(f=>f[key]).filter(Boolean))].sort(); }
function fillSelect(el, vals, allLabel){
  el.innerHTML = `<option value="">${allLabel}</option>` + vals.map(v=>`<option>${v}</option>`).join("");
}
fillSelect($("f-country"), uniq("country"), "All countries");
fillSelect($("f-domain"), uniq("domain"), "All");
fillSelect($("f-region"), uniq("region"), "All regions");
fillSelect($("f-play"), uniq("play"), "All plays");
// sensible defaults: US · offshore · GoM
$("f-country").value = "USA"; $("f-domain").value = "offshore"; $("f-region").value = "US Gulf of Mexico";

const tiers = ["all","rich","sample","roadmap"];
$("f-tiers").innerHTML = tiers.map(t=>`<button class="tierbtn${t==="all"?" on":""}" data-t="${t}">${t==="all"?"All tiers":t}</button>`).join("");
$("f-tiers").onclick = e => { if(!e.target.dataset.t) return;
  tierFilter = e.target.dataset.t;
  [...$("f-tiers").children].forEach(b=>b.classList.toggle("on", b.dataset.t===tierFilter));
  render(); };

["f-country","f-domain","f-region","f-play","f-search"].forEach(id=>$(id).addEventListener("input", render));

function render(){
  const c=$("f-country").value, d=$("f-domain").value, r=$("f-region").value, p=$("f-play").value,
        q=$("f-search").value.trim().toLowerCase();
  let rows = ROSTER.filter(f =>
    (!c||f.country===c) && (!d||f.domain===d) && (!r||f.region===r) && (!p||f.play===p) &&
    (tierFilter==="all"||f.density_tier===tierFilter) &&
    (!q || (f.name+" "+(f.block||"")+" "+(f.operator||"")).toLowerCase().includes(q)));
  rows.sort((a,b)=> (TIER_ORDER[a.density_tier]-TIER_ORDER[b.density_tier]) || a.name.localeCompare(b.name));
  $("f-count").textContent = `${rows.length} field${rows.length===1?"":"s"}`;
  $("f-grid").innerHTML = rows.map(f=>{
    const go = f.lifecycle_id
      ? `<div class="go"><a href="../lifecycle/${f.lifecycle_id}_lifecycle.html">Life-cycle →</a></div>`
      : (f.concept ? `<div class="go"><span>concept: ${f.concept}</span></div>` : "");
    const meta = [f.operator, f.block].filter(Boolean).map(x=>`<b>${x}</b>`).join(" · ");
    const play = f.play ? `<div class="concept">${f.play}</div>` : "";
    return `<div class="card"><h3>${f.name}<span class="badge ${f.density_tier}">${f.density_tier}</span></h3>
      ${meta?`<div class="meta">${meta}</div>`:""}${play}${go}</div>`;
  }).join("");
}
render();
</script>
</body>
</html>
"""


def main():
    HERE.mkdir(parents=True, exist_ok=True)
    (HERE / "index.html").write_text(build())
    print(
        f"  wrote {HERE / 'index.html'}  ({len(json.loads(ROSTER.read_text()))} fields)"
    )


if __name__ == "__main__":
    main()
