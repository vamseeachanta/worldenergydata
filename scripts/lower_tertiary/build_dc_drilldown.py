#!/usr/bin/env python3
"""Build the D&C drill-down explorer: Field or Block -> bores -> bore data.

The holistic drill-down surface for the D&C QA/QC family. Two entry axes into
ONE tree (every block belongs to exactly one field): browse by Field (11) or by
Block/lease (23), drill to the bores, then to a single bore's full record, then
out to that field's engineering pages (lifecycle, economics, assets, explorer).

Self-contained single file: inline CSS tokens (light+dark), inline SVG, an
embedded JSON payload, and a hash router (#/field/<id>, #/block/<id>,
#/bore/<api12>) so any level is deep-linkable. No external assets, no build-time
network, no timestamps (deterministic output).

Source of truth: the same committed extractor output the listing and the HF
tables use -- this script re-projects, it never recomputes.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SOURCE_CSV = (
    REPO
    / "docs/modules/bsee/analysis/production/FDAS_V30"
    / "drilling_and_completion_days_v21_kc.csv"
)
BENCHMARK_CSV = (
    REPO / "reports/lower_tertiary/lt_well_benchmark_lower_tertiary_2010_latest.csv"
)
VINTAGE_CSV = REPO / "reports/lower_tertiary/data/dc_vintage_diff.csv"
OUT_HTML = REPO / "reports/lower_tertiary/dc-drilldown.html"

DEV_OF_LEASE = {
    "Cascade": "Cascade Chinook",
    "Chinook": "Cascade Chinook",
    "Jack": "Jack St Malo",
    "St Malo": "Jack St Malo",
}

SLUG = {
    "Anchor": "anchor",
    "Big Foot": "big_foot",
    "Buckskin": "buckskin",
    "Cascade Chinook": "cascade_chinook",
    "Jack St Malo": "jack_st_malo",
    "Julia": "julia",
    "Kaskida": "kaskida",
    "North Platte": "north_platte",
    "Shenandoah": "shenandoah",
    "Stones": "stones",
    "Tiber": "tiber",
}

# Verified live 2026-07-26 -- absent pages are rendered as honest gaps, never
# as dead links. (buckskin has no lifecycle poster; kaskida/north_platte/tiber
# are pre-production so carry no economics page; only stones has an asset page.)
NO_LIFECYCLE = {"buckskin"}
NO_ECONOMICS = {"kaskida", "north_platte", "tiber"}
HAS_ASSETS = {"stones"}

# Per-development reconciliation status vs the World Oil April 2026 Table 1.
STATUS = {
    "Anchor": ("exact", "ok"),
    "Big Foot": ("WED-only — excluded from the article", "idx"),
    "Buckskin": ("recovered — +52 days, bore missing from the article", "idx"),
    "Cascade Chinook": ("exact", "ok"),
    "Jack St Malo": ("open — +119 days, #846 completion boundary", "warn"),
    "Julia": ("exact", "ok"),
    "Kaskida": ("exact", "ok"),
    "North Platte": ("days exact; +3 zero-day sidetracks", "ok"),
    "Shenandoah": ("resolved — +24 recompletion-accounting days", "idx"),
    "Stones": ("exact; +20 post-cutoff servicing days", "ok"),
    "Tiber": ("exact", "ok"),
}

VINTAGE_LABEL = {
    "unchanged": "unchanged across vintages",
    "late_data": "late data — zero-day placeholder in frozen V30",
    "servicing_accrual": "post-TD servicing accrued (drilling unchanged)",
    "wed_only": "present only in the current extract",
}


def _int(raw: str) -> int:
    raw = (raw or "").strip()
    return int(float(raw)) if raw else 0


def _iso(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    m, d, y = raw.split("/")
    return f"{y}-{m}-{d}"


def load_payload() -> dict:
    producers = {
        row["api12"].strip()
        for row in csv.DictReader(BENCHMARK_CSV.open(encoding="utf-8"))
    }
    vintage = {
        row["api12"]: row for row in csv.DictReader(VINTAGE_CSV.open(encoding="utf-8"))
    }

    bores: list[dict] = []
    for row in csv.DictReader(SOURCE_CSV.open(encoding="utf-8")):
        api12 = row["API_WELL_NUMBER"].strip()
        field = DEV_OF_LEASE.get(row["LEASE_NAME"].strip(), row["LEASE_NAME"].strip())
        v = vintage.get(api12, {})
        bores.append(
            {
                "api": api12,
                "name": row["WELL_NAME"].strip() or api12[-4:],
                "field": field,
                "block": row["SURF_LEASE_NUM"].strip(),
                "wd": _int(row["WATER_DEPTH"]),
                "spud": _iso(row["WELL_SPUD_DATE"]),
                "td": _iso(row["TOTAL_DEPTH_DATE"]),
                "drill": _int(row["DRILLING_DAYS"]),
                "compl": _int(row["COMPLETION_DAYS"]),
                "md": _int(row["MAX_BH_TOTAL_MD"]),
                "tvd": _int(row["MAX_WELL_BORE_TVD"]),
                "ppg": (row["MAX_DRILL_FLUID_WGT"] or "").strip(),
                "st": api12[-2:] != "00",
                "prod": api12 in producers,
                "vin": v.get("category", "unchanged"),
            }
        )
    bores.sort(key=lambda b: (b["field"], b["block"], b["spud"] or "9999", b["api"]))

    fields: dict[str, dict] = {}
    blocks: dict[str, dict] = {}
    for b in bores:
        f = fields.setdefault(
            b["field"],
            {
                "name": b["field"],
                "slug": SLUG[b["field"]],
                "bores": 0,
                "drill": 0,
                "compl": 0,
                "prod": 0,
                "blocks": [],
                "wd": b["wd"],
                "status": STATUS[b["field"]][0],
                "badge": STATUS[b["field"]][1],
            },
        )
        f["bores"] += 1
        f["drill"] += b["drill"]
        f["compl"] += b["compl"]
        f["prod"] += 1 if b["prod"] else 0
        if b["block"] not in f["blocks"]:
            f["blocks"].append(b["block"])

        k = blocks.setdefault(
            b["block"],
            {
                "id": b["block"],
                "field": b["field"],
                "bores": 0,
                "drill": 0,
                "compl": 0,
                "prod": 0,
                "wd": b["wd"],
            },
        )
        k["bores"] += 1
        k["drill"] += b["drill"]
        k["compl"] += b["compl"]
        k["prod"] += 1 if b["prod"] else 0

    return {
        "bores": bores,
        "fields": sorted(fields.values(), key=lambda f: -f["bores"]),
        "blocks": sorted(blocks.values(), key=lambda k: -k["bores"]),
        "links": {
            slug: {
                "lifecycle": (
                    None if slug in NO_LIFECYCLE else f"lifecycle/{slug}_lifecycle.html"
                ),
                "economics": None if slug in NO_ECONOMICS else f"economics-{slug}.html",
                "assets": (
                    f"lifecycle/assets/{slug}_assets.html"
                    if slug in HAS_ASSETS
                    else None
                ),
            }
            for slug in SLUG.values()
        },
        "vintage_label": VINTAGE_LABEL,
    }


CSS = """
:root{--bg:#eaeff2;--surface:#fff;--surface-2:#f3f7f9;--ink:#0e2733;--ink-soft:#48606b;
--ink-faint:#7c929c;--line:#d8e3e8;--line-strong:#c3d3da;--accent:#0e7c8b;--accent-strong:#0a5f6c;
--accent-wash:#e2f0f2;--ok:#2e8b6f;--ok-wash:#e2f1ec;--warn:#b3781a;--warn-wash:#f6ecdb;
--hold:#647680;--hold-wash:#eaeef0;--shadow:0 1px 2px rgba(14,39,51,.06),0 8px 24px -12px rgba(14,39,51,.18);
--radius:14px;--sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
--mono:ui-monospace,"SF Mono","Cascadia Code","Roboto Mono",Menlo,Consolas,monospace}
@media (prefers-color-scheme:dark){:root{--bg:#081820;--surface:#0e2732;--surface-2:#12303c;
--ink:#e6eef1;--ink-soft:#9fb4bd;--ink-faint:#6b8290;--line:#1e3a47;--line-strong:#274653;
--accent:#3fbfd0;--accent-strong:#6fd4e2;--accent-wash:#10323d;--ok:#4fc79f;--ok-wash:#10322a;
--warn:#e0a94a;--warn-wash:#33280f;--hold:#8ea4ae;--hold-wash:#17272f;
--shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px -14px rgba(0,0,0,.6)}}
:root[data-theme="light"]{--bg:#eaeff2;--surface:#fff;--surface-2:#f3f7f9;--ink:#0e2733;
--ink-soft:#48606b;--ink-faint:#7c929c;--line:#d8e3e8;--line-strong:#c3d3da;--accent:#0e7c8b;
--accent-strong:#0a5f6c;--accent-wash:#e2f0f2;--ok:#2e8b6f;--ok-wash:#e2f1ec;--warn:#b3781a;
--warn-wash:#f6ecdb;--hold:#647680;--hold-wash:#eaeef0}
:root[data-theme="dark"]{--bg:#081820;--surface:#0e2732;--surface-2:#12303c;--ink:#e6eef1;
--ink-soft:#9fb4bd;--ink-faint:#6b8290;--line:#1e3a47;--line-strong:#274653;--accent:#3fbfd0;
--accent-strong:#6fd4e2;--accent-wash:#10323d;--ok:#4fc79f;--ok-wash:#10322a;--warn:#e0a94a;
--warn-wash:#33280f;--hold:#8ea4ae;--hold-wash:#17272f}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);line-height:1.6;
-webkit-font-smoothing:antialiased}
a{color:inherit}
.wrap{max-width:1140px;margin:0 auto;padding:0 24px}
.eyebrow{font-family:var(--mono);font-size:.7rem;letter-spacing:.16em;text-transform:uppercase;
color:var(--ink-faint);margin:0}
header.site{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--surface) 88%,transparent);
backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.site-inner{display:flex;align-items:center;gap:20px;height:60px}
.wordmark{display:flex;align-items:center;gap:10px;font-weight:600;letter-spacing:-.01em;white-space:nowrap}
.wordmark .glyph{width:22px;height:22px;flex:none}
nav.capability{margin-left:auto;display:flex;gap:2px;flex-wrap:wrap;align-items:center}
nav.capability a{font-family:var(--mono);font-size:.78rem;text-decoration:none;color:var(--ink-soft);
padding:6px 10px;border-radius:8px;white-space:nowrap}
nav.capability a:hover{background:var(--surface-2);color:var(--ink)}
nav.capability a.active{background:var(--accent-wash);color:var(--accent-strong);font-weight:600}
nav.capability a.ext::after{content:" ↗";color:var(--ink-faint)}
a:focus-visible,button:focus-visible,tr:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.crumb{font-family:var(--mono);font-size:.74rem;color:var(--ink-faint);padding:18px 0 0;
display:flex;flex-wrap:wrap;align-items:center;gap:0}
.crumb a{text-decoration:none;cursor:pointer}
.crumb a:hover{color:var(--accent)}
.crumb .sep{padding:0 8px;opacity:.6}
.crumb .here{color:var(--ink)}
.hero{padding:18px 0 22px}
.hero h1{font-size:clamp(1.9rem,4.4vw,2.7rem);line-height:1.06;letter-spacing:-.025em;
margin:10px 0 12px;text-wrap:balance;font-weight:700}
.hero .lede{font-size:1.08rem;color:var(--ink-soft);max-width:62ch;margin:0 0 18px}
.disposition{display:inline-flex;align-items:center;gap:10px;background:var(--warn-wash);color:var(--warn);
border:1px solid color-mix(in srgb,var(--warn) 32%,transparent);border-radius:999px;padding:7px 15px 7px 12px;
font-family:var(--mono);font-size:.78rem;font-weight:600}
.disposition .dot{width:8px;height:8px;border-radius:50%;background:currentColor;
box-shadow:0 0 0 4px color-mix(in srgb,var(--warn) 20%,transparent)}
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:20px 0 8px}
.tile{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:14px 16px 12px;
box-shadow:var(--shadow)}
.tile .k{font-family:var(--mono);font-size:.64rem;letter-spacing:.12em;text-transform:uppercase;color:var(--ink-faint)}
.tile .v{font-size:1.6rem;font-weight:700;letter-spacing:-.02em;margin-top:4px;font-variant-numeric:tabular-nums}
.tile .v small{font-size:.85rem;font-weight:600;color:var(--ink-soft);margin-left:2px}
.tile .sub{font-size:.76rem;color:var(--ink-soft)}
.tile .v.ok{color:var(--ok)}.tile .v.accent{color:var(--accent)}.tile .v.warn{color:var(--warn)}
.controls{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:30px 0 16px}
.axis{display:inline-flex;background:var(--surface-2);border:1px solid var(--line);border-radius:10px;padding:3px}
.axis button{font-family:var(--mono);font-size:.8rem;font-weight:600;border:0;background:transparent;
color:var(--ink-soft);padding:7px 16px;border-radius:8px;cursor:pointer}
.axis button[aria-pressed="true"]{background:var(--accent-wash);color:var(--accent-strong)}
.search{flex:1;min-width:220px;display:flex;align-items:center;gap:8px;background:var(--surface);
border:1px solid var(--line);border-radius:10px;padding:8px 12px}
.search input{flex:1;border:0;background:transparent;color:var(--ink);font-family:var(--sans);
font-size:.92rem;outline:none;min-width:0}
.count{font-family:var(--mono);font-size:.76rem;color:var(--ink-faint);white-space:nowrap}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(248px,1fr));gap:14px}
.node{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:16px 18px;
box-shadow:var(--shadow);cursor:pointer;text-align:left;font:inherit;color:inherit;display:flex;
flex-direction:column;gap:8px;transition:transform .16s ease,border-color .16s ease}
.node:hover{transform:translateY(-3px);border-color:var(--accent)}
.node .top{display:flex;align-items:baseline;justify-content:space-between;gap:10px}
.node h3{margin:0;font-size:1.06rem;letter-spacing:-.02em}
.node .meta{font-family:var(--mono);font-size:.7rem;color:var(--ink-faint)}
.node .nums{display:flex;gap:14px;font-variant-numeric:tabular-nums}
.node .nums div{font-size:.78rem;color:var(--ink-soft)}
.node .nums b{display:block;font-size:1.02rem;color:var(--ink);font-weight:700}
.bar{height:6px;border-radius:3px;background:var(--surface-2);overflow:hidden;display:flex}
.bar i{display:block;height:100%}
.bar .d{background:var(--accent)}.bar .c{background:color-mix(in srgb,var(--accent) 38%,transparent)}
.badge{font-family:var(--mono);font-size:.64rem;letter-spacing:.06em;text-transform:uppercase;padding:3px 8px;
border-radius:999px;font-weight:600;white-space:nowrap;border:1px solid transparent;display:inline-flex;
align-items:center;gap:5px}
.badge.ok{color:var(--ok);background:var(--ok-wash);border-color:color-mix(in srgb,var(--ok) 26%,transparent)}
.badge.warn{color:var(--warn);background:var(--warn-wash);border-color:color-mix(in srgb,var(--warn) 26%,transparent)}
.badge.idx{color:var(--accent-strong);background:var(--accent-wash);border-color:color-mix(in srgb,var(--accent) 26%,transparent)}
.badge.hold{color:var(--hold);background:var(--hold-wash);border-color:color-mix(in srgb,var(--hold) 26%,transparent)}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
box-shadow:var(--shadow);padding:20px 22px;margin-top:4px}
.panel h2{margin:0 0 4px;font-size:1.4rem;letter-spacing:-.02em}
.panel .sub{color:var(--ink-soft);font-size:.92rem;margin:0 0 16px}
.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:.86rem}
th,td{padding:9px 12px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}
th{font-family:var(--mono);font-size:.66rem;letter-spacing:.1em;text-transform:uppercase;
color:var(--ink-faint);background:var(--surface-2);position:sticky;top:0}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
tbody tr{cursor:pointer}
tbody tr:hover{background:var(--accent-wash)}
tbody tr:last-child td{border-bottom:0}
.mono{font-family:var(--mono);font-size:.82rem}
.dl{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin:0 0 18px}
.dl div{background:var(--surface-2);border:1px solid var(--line);border-radius:10px;padding:11px 13px}
.dl dt{font-family:var(--mono);font-size:.63rem;letter-spacing:.1em;text-transform:uppercase;
color:var(--ink-faint);margin:0}
.dl dd{margin:3px 0 0;font-size:1.04rem;font-weight:600;font-variant-numeric:tabular-nums}
.dl dd small{font-size:.8rem;font-weight:500;color:var(--ink-soft)}
.links{display:flex;flex-wrap:wrap;gap:10px;margin-top:16px}
.links a,.links span{font-family:var(--mono);font-size:.78rem;text-decoration:none;padding:8px 13px;
border-radius:9px;border:1px solid var(--line);background:var(--surface-2)}
.links a:hover{border-color:var(--accent);color:var(--accent-strong)}
.links span{color:var(--ink-faint);border-style:dashed}
.empty{padding:28px;text-align:center;color:var(--ink-faint);font-family:var(--mono);font-size:.84rem}
.legend{display:flex;flex-wrap:wrap;gap:10px 18px;margin:20px 0 0;padding:14px 18px;background:var(--surface-2);
border:1px solid var(--line);border-radius:12px}
.legend .item{display:flex;align-items:center;gap:8px;font-size:.8rem;color:var(--ink-soft)}
.legend .sw{width:10px;height:10px;border-radius:3px}
footer.site{margin:48px 0 40px;padding-top:22px;border-top:1px solid var(--line);color:var(--ink-soft);font-size:.84rem}
footer.site .row{display:flex;flex-wrap:wrap;gap:6px 20px;align-items:center;justify-content:space-between}
footer.site a{color:var(--accent);text-decoration:none}
.note{margin-top:12px;font-size:.77rem;color:var(--ink-faint);font-family:var(--mono)}
@media (max-width:860px){.tiles{grid-template-columns:repeat(2,1fr)}nav.capability{display:none}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
"""

JS = """
const $=s=>document.querySelector(s);
const fmt=n=>n.toLocaleString('en-US');
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let axis='field', q='';

function boresFor(kind,id){
  return DATA.bores.filter(b=>kind==='field'?b.field===id:b.block===id);
}
function matches(text){return !q||String(text).toLowerCase().includes(q);}

function crumb(parts){
  $('#crumb').innerHTML=parts.map((p,i)=>{
    const sep=i?'<span class="sep">▸</span>':'';
    return sep+(p.href?`<a href="${p.href}">${esc(p.label)}</a>`:`<span class="here">${esc(p.label)}</span>`);
  }).join('');
}

function bar(d,c){
  const t=d+c||1;
  return `<span class="bar"><i class="d" style="width:${(d/t*100).toFixed(1)}%"></i><i class="c" style="width:${(c/t*100).toFixed(1)}%"></i></span>`;
}

function renderIndex(){
  const isField=axis==='field';
  const items=(isField?DATA.fields:DATA.blocks).filter(n=>
    matches(isField?n.name:n.id+' '+n.field));
  crumb([{label:isField?'Fields':'Blocks'}]);
  $('#count').textContent=`${items.length} of ${(isField?DATA.fields:DATA.blocks).length} ${isField?'fields':'blocks'}`;
  $('#detail').innerHTML='';
  $('#index').innerHTML=items.length?items.map(n=>{
    const id=isField?n.name:n.id;
    const title=isField?n.name:n.id;
    const meta=isField?`${n.blocks.length} block${n.blocks.length>1?'s':''} · ${fmt(n.wd)} ft`:n.field;
    const badge=isField?`<span class="badge ${n.badge}">${esc(n.status.split(' —')[0])}</span>`:
      `<span class="badge hold">${n.prod||0} producer${n.prod===1?'':'s'}</span>`;
    return `<button class="node" data-kind="${isField?'field':'block'}" data-id="${esc(id)}">
      <span class="top"><h3>${esc(title)}</h3>${badge}</span>
      <span class="meta">${esc(meta)}</span>
      <span class="nums"><div>bores<b>${n.bores}</b></div><div>drilling<b>${fmt(n.drill)}</b></div>
      <div>completion<b>${fmt(n.compl)}</b></div></span>
      ${bar(n.drill,n.compl)}</button>`;
  }).join(''):'<div class="empty">No match. Clear the search to see all.</div>';
}

function renderNode(kind,id){
  const list=boresFor(kind,id).filter(b=>matches(b.api+' '+b.name+' '+b.block+' '+b.field));
  if(!list.length&&!boresFor(kind,id).length){location.hash='#/';return;}
  const all=boresFor(kind,id);
  const drill=all.reduce((s,b)=>s+b.drill,0), compl=all.reduce((s,b)=>s+b.compl,0);
  const prod=all.filter(b=>b.prod).length, st=all.filter(b=>b.st).length;
  const field=kind==='field'?DATA.fields.find(f=>f.name===id):DATA.fields.find(f=>f.name===all[0].field);
  crumb([{label:kind==='field'?'Fields':'Blocks',href:'#/'},{label:id}]);
  $('#count').textContent=`${list.length} of ${all.length} bores`;
  $('#index').innerHTML='';
  const blocks=kind==='field'?field.blocks.map(b=>
    `<a href="#/block/${encodeURIComponent(b)}">${esc(b)}</a>`).join(' '):'';
  $('#detail').innerHTML=`<div class="panel">
    <h2>${esc(id)}</h2>
    <p class="sub">${kind==='field'?esc(field.status):'Block of '+esc(all[0].field)} · ${fmt(all[0].wd)} ft water depth</p>
    <div class="dl">
      <div><dt>Bores</dt><dd>${all.length}</dd></div>
      <div><dt>Drilling days</dt><dd>${fmt(drill)}</dd></div>
      <div><dt>Completion days</dt><dd>${fmt(compl)}</dd></div>
      <div><dt>D&amp;C days</dt><dd>${fmt(drill+compl)}</dd></div>
      <div><dt>Producers</dt><dd>${prod||'—'}<small>${prod?' of '+all.length:''}</small></dd></div>
      <div><dt>Sidetracks</dt><dd>${st}</dd></div>
    </div>
    ${kind==='field'?`<div class="links"><span>Blocks:</span>${blocks}</div>`:''}
    ${links(field.slug)}
    <div class="table-wrap" style="margin-top:18px">${boreTable(list,kind==='field')}</div>
  </div>`;
}

function boreTable(list,showBlock){
  if(!list.length)return '<div class="empty">No bores match the search.</div>';
  return `<table><thead><tr><th>API12</th><th>Bore</th>${showBlock?'<th>Block</th>':''}
    <th>Spud</th><th>TD</th><th class="num">Drill</th><th class="num">Compl</th>
    <th class="num">D&amp;C</th><th>Flags</th></tr></thead><tbody>
    ${list.map(b=>`<tr tabindex="0" data-api="${b.api}">
      <td class="mono">${b.api}</td><td>${esc(b.name)}</td>${showBlock?`<td class="mono">${esc(b.block)}</td>`:''}
      <td class="mono">${b.spud||'—'}</td><td class="mono">${b.td||'—'}</td>
      <td class="num">${b.drill}</td><td class="num">${b.compl}</td><td class="num">${b.drill+b.compl}</td>
      <td>${b.prod?'<span class="badge ok">producer</span> ':''}${b.st?'<span class="badge hold">ST</span>':''}</td>
    </tr>`).join('')}</tbody></table>`;
}

function links(slug){
  const L=DATA.links[slug]||{};
  const item=(href,label,gap)=>href?`<a href="${href}">${label} →</a>`:`<span>${label} — ${gap}</span>`;
  return `<div class="links">
    ${item(L.lifecycle,'Life-cycle','no poster')}
    ${item(L.economics,'Economics','pre-production')}
    ${item(L.assets,'Assets &amp; engineering','not yet built')}
    <a href="field-atlas/">Field atlas →</a>
    <a href="wo-april-2026-per-well-dc.html">Full listing →</a></div>`;
}

function renderBore(api){
  const b=DATA.bores.find(x=>x.api===api);
  if(!b){location.hash='#/';return;}
  const field=DATA.fields.find(f=>f.name===b.field);
  crumb([{label:'Fields',href:'#/'},{label:b.field,href:'#/field/'+encodeURIComponent(b.field)},
    {label:b.block,href:'#/block/'+encodeURIComponent(b.block)},{label:b.api}]);
  $('#count').textContent='1 bore';
  $('#index').innerHTML='';
  const vin=DATA.vintage_label[b.vin]||b.vin;
  const vinBadge=b.vin==='unchanged'?'ok':(b.vin==='late_data'?'idx':'warn');
  $('#detail').innerHTML=`<div class="panel">
    <h2>${esc(b.name)} <span class="mono" style="color:var(--ink-faint);font-size:1rem">${b.api}</span></h2>
    <p class="sub">${esc(b.field)} · block ${esc(b.block)} · ${fmt(b.wd)} ft water depth
      ${b.prod?' · <span class="badge ok">producer</span>':''}${b.st?' · <span class="badge hold">sidetrack</span>':''}</p>
    <div class="dl">
      <div><dt>Spud</dt><dd>${b.spud||'—'}</dd></div>
      <div><dt>Total depth</dt><dd>${b.td||'—'}</dd></div>
      <div><dt>Drilling days</dt><dd>${b.drill}</dd></div>
      <div><dt>Completion days</dt><dd>${b.compl}</dd></div>
      <div><dt>D&amp;C days</dt><dd>${b.drill+b.compl}</dd></div>
      <div><dt>Measured depth</dt><dd>${b.md?fmt(b.md):'—'}<small> ft</small></dd></div>
      <div><dt>True vertical</dt><dd>${b.tvd?fmt(b.tvd):'—'}<small> ft</small></dd></div>
      <div><dt>Max mud weight</dt><dd>${b.ppg||'—'}<small> ppg</small></dd></div>
    </div>
    <p class="sub"><span class="badge ${vinBadge}">vintage</span> ${esc(vin)}.
      Completion days count all post-TD rig time, including later servicing
      (<a href="https://github.com/vamseeachanta/worldenergydata/issues/846">#846</a>).</p>
    ${links(field.slug)}</div>`;
}

function route(){
  const h=decodeURIComponent(location.hash.replace(/^#\\/?/,''));
  const [kind,id]=h.split('/');
  if(kind==='bore'&&id)return renderBore(id);
  if(kind==='field'&&id){axis='field';syncAxis();return renderNode('field',id);}
  if(kind==='block'&&id){axis='block';syncAxis();return renderNode('block',id);}
  renderIndex();
}
function syncAxis(){
  document.querySelectorAll('.axis button').forEach(btn=>
    btn.setAttribute('aria-pressed',String(btn.dataset.axis===axis)));
}
document.addEventListener('click',e=>{
  const node=e.target.closest('.node');
  if(node){location.hash=`#/${node.dataset.kind}/${encodeURIComponent(node.dataset.id)}`;return;}
  const row=e.target.closest('tr[data-api]');
  if(row){location.hash=`#/bore/${row.dataset.api}`;return;}
  const btn=e.target.closest('.axis button');
  if(btn){axis=btn.dataset.axis;syncAxis();location.hash='#/';renderIndex();}
});
document.addEventListener('keydown',e=>{
  if(e.key==='Enter'){const row=e.target.closest&&e.target.closest('tr[data-api]');
    if(row)location.hash=`#/bore/${row.dataset.api}`;}
});
$('#q').addEventListener('input',e=>{q=e.target.value.trim().toLowerCase();route();});
window.addEventListener('hashchange',route);
route();
"""


def build_html(payload: dict) -> str:
    b = payload["bores"]
    drill = sum(x["drill"] for x in b)
    compl = sum(x["compl"] for x in b)
    data_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    # Guard: the payload is inlined in a <script>, so it must not carry a
    # closing-tag sequence. json.dumps escapes newlines; escape the slash too.
    data_json = data_json.replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>D&amp;C Drill-Down — Field ▸ Block ▸ Bore</title>
<style>{CSS}</style>
</head>
<body>
<header class="site">
  <div class="wrap site-inner">
    <span class="wordmark">
      <svg class="glyph" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <rect x="1.5" y="1.5" width="21" height="21" rx="4" stroke="var(--accent)" stroke-width="1.6"/>
        <path d="M2 14c2.6 0 2.6-3 5.2-3s2.6 3 5.2 3 2.6-3 5.2-3 2.6 3 4.2 3" stroke="var(--accent)"
          stroke-width="1.6" fill="none" stroke-linecap="round"/>
        <path d="M2 18c2.6 0 2.6-2 5.2-2s2.6 2 5.2 2 2.6-2 5.2-2 2.6 2 4.2 2" stroke="var(--accent)"
          stroke-width="1.2" fill="none" stroke-linecap="round" opacity=".5"/>
      </svg>
      AceEngineer
    </span>
    <nav class="capability" aria-label="D&amp;C QA/QC navigation">
      <a href="wo-april-2026-qaqc-hub.html">Hub</a>
      <a href="#/" class="active">Drill-down</a>
      <a href="wo-april-2026-validation.html">Matrix</a>
      <a href="wo-april-2026-per-well-dc.html">Full listing</a>
      <a href="field-atlas/">Atlas</a>
      <a href="https://huggingface.co/datasets/aceengineer/worldenergydata-explorer" class="ext">Data</a>
    </nav>
  </div>
</header>

<div class="wrap">
  <div class="crumb" id="crumb"></div>

  <section class="hero">
    <p class="eyebrow">BSEE WAR rig-days · Lower Tertiary · Gulf of Mexico</p>
    <h1>D&amp;C Drill-Down</h1>
    <p class="lede">Start from a field or a block, drill to its bores, then to a single
      wellbore's full record — and on to that field's life-cycle, economics, and
      engineering pages. Every level is deep-linkable.</p>
    <span class="disposition"><span class="dot"></span>Reconciled to the article —
      completion-boundary rule (#846) open</span>
    <div class="tiles">
      <div class="tile"><div class="k">Fields</div><div class="v accent">{len(payload['fields'])}</div>
        <div class="sub">developments</div></div>
      <div class="tile"><div class="k">Blocks</div><div class="v">{len(payload['blocks'])}</div>
        <div class="sub">OCS leases</div></div>
      <div class="tile"><div class="k">Bores</div><div class="v">{len(b)}</div>
        <div class="sub">incl. sidetracks</div></div>
      <div class="tile"><div class="k">D&amp;C days</div><div class="v">{drill + compl:,}</div>
        <div class="sub">{drill:,} drilling · {compl:,} completion</div></div>
    </div>
  </section>

  <div class="controls">
    <div class="axis" role="group" aria-label="Browse axis">
      <button data-axis="field" aria-pressed="true">By field</button>
      <button data-axis="block" aria-pressed="false">By block</button>
    </div>
    <label class="search">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="11" cy="11" r="7" stroke="var(--ink-faint)" stroke-width="2"/>
        <path d="M16.5 16.5 21 21" stroke="var(--ink-faint)" stroke-width="2" stroke-linecap="round"/>
      </svg>
      <input id="q" type="search" placeholder="Search field, block, API12, or bore name">
    </label>
    <span class="count" id="count"></span>
  </div>

  <div class="grid" id="index"></div>
  <div id="detail"></div>

  <div class="legend" aria-label="Legend">
    <span class="eyebrow" style="align-self:center">Reading the data</span>
    <span class="item"><span class="sw" style="background:var(--accent)"></span>Drilling days (spud → TD)</span>
    <span class="item"><span class="sw" style="background:color-mix(in srgb,var(--accent) 38%,transparent)"></span>Completion days (all post-TD rig time)</span>
    <span class="item"><span class="sw" style="background:var(--ok)"></span>Reconciled / producer</span>
    <span class="item"><span class="sw" style="background:var(--warn)"></span>Open accounting question</span>
  </div>

  <footer class="site">
    <div class="row">
      <span>D&amp;C drill-down — World Oil April 2026 QA/QC · Field ▸ Block ▸ Bore</span>
      <a href="https://huggingface.co/datasets/aceengineer/worldenergydata-explorer">Data &amp; provenance ↗</a>
    </div>
    <p class="note">// self-contained: no external assets. Rows come verbatim from the
      canonical extractor output (BSEE WAR vintage 2026-02-19). Drilling days mix calendar
      spans (≤250 d) with WAR-union rig-days beyond, so batch-drilled wells undercount —
      disclosed, not corrected.</p>
  </footer>
</div>

<script>const DATA={data_json};{JS}</script>
</body>
</html>
"""


def main() -> None:
    payload = load_payload()
    OUT_HTML.write_text(build_html(payload), encoding="utf-8")
    print(
        f"wrote {OUT_HTML} — {len(payload['fields'])} fields / "
        f"{len(payload['blocks'])} blocks / {len(payload['bores'])} bores"
    )


if __name__ == "__main__":
    main()
