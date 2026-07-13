#!/usr/bin/env python3
"""Build the rig-selector explorer (#998) from the contractor spec database.

Emits ``reports/rig-selector/index.html`` — a single-file, dependency-free
interactive explorer over the vendor-spec fleet: filter row (rig type, owner,
capability floors), sortable table, and a water-depth vs hookload scatter.
Colors follow the validated 3-slot categorical palette (rig type = identity);
identity is never color-alone (legend + tooltips + table view).

Usage:
    python scripts/vessel_fleet/build_rig_selector.py [--out <dir>]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))
sys.path.insert(0, str(_PROJECT_ROOT / "packages/worldenergydata-vessel_fleet/src"))

from worldenergydata.vessel_fleet import selection

_COLUMNS = [
    ("VESSEL_NAME", "Rig"),
    ("OWNER", "Contractor"),
    ("RIG_TYPE", "Type"),
    ("RIG_DESIGN", "Design"),
    ("YEAR_BUILT", "Year"),
    ("WATER_DEPTH_RATING_FT", "Water depth (ft)"),
    ("DRILLING_DEPTH_RATING_FT", "Drilling depth (ft)"),
    ("LOA_M", "LOA (m)"),
    ("BEAM_M", "Beam (m)"),
    ("MOONPOOL_LENGTH_M", "Moonpool L (m)"),
    ("MOONPOOL_WIDTH_M", "Moonpool W (m)"),
    ("LEG_LENGTH_FT", "Legs (ft)"),
    ("CANTILEVER_REACH_FT", "Cantilever (ft)"),
    ("VARIABLE_DECK_LOAD_ST", "VDL (st)"),
    ("HOOKLOAD_RATING_KIPS", "Hookload (kips)"),
    ("DRAWWORKS_HP", "Drawworks (HP)"),
    ("WALKING_SYSTEM", "Walking"),
    ("GENERATION", "Gen"),
    ("MPD_CAPABLE", "MPD"),
    ("DUAL_ACTIVITY", "Dual activity"),
    ("CRANE_MAIN_CAPACITY_T", "Crane (t)"),
    ("QUARTERS_CAPACITY", "Quarters"),
    ("IS_OFFSHORE", "Offshore"),
    ("DATA_SOURCE_URL", "Spec sheet"),
]


def build(out_dir: Path) -> Path:
    fleet = selection.load_spec_fleet()
    records = []
    for _, row in fleet.iterrows():
        rec = {}
        for col, _label in _COLUMNS:
            value = row.get(col)
            rec[col] = None if value is None or value != value else value
        records.append(rec)

    summary = selection.fleet_summary(fleet)
    stats = {
        "rigs": int(len(fleet)),
        "contractors": int(fleet["OWNER"].nunique()),
        "drillships": int((fleet["RIG_TYPE"] == "drillship").sum()),
        "semis": int((fleet["RIG_TYPE"] == "semi_submersible").sum()),
        "jackups": int((fleet["RIG_TYPE"] == "jack_up").sum()),
        "land": int((fleet["RIG_TYPE"] == "land_rig").sum()),
        "retrieved": "2026-07-13",
        "owners": summary.index.dropna().tolist(),
    }

    html = _TEMPLATE.replace("__DATA__", json.dumps(records)).replace(
        "__STATS__", json.dumps(stats)
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "index.html"
    out_path.write_text(html)
    print(f"Wrote {out_path} ({len(records)} rigs)")
    return out_path


_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Drilling Rig Selector — vendor spec database</title>
<style>
:root { --surface:#fcfcfa; --panel:#f2f1ec; --ink:#1a1a19; --ink2:#5c5b54; --line:#d8d6cd;
        --ds:#2a78d6; --ss:#1baf7a; --ju:#eda100; --lr:#008300; }
@media (prefers-color-scheme: dark) {
  :root { --surface:#1a1a19; --panel:#242422; --ink:#ffffff; --ink2:#c3c2b7; --line:#3a3936;
          --ds:#3987e5; --ss:#199e70; --ju:#c98500; --lr:#008300; }
}
* { box-sizing:border-box; }
body { margin:0; background:var(--surface); color:var(--ink);
       font:14px/1.45 system-ui, -apple-system, sans-serif; }
main { max-width:1280px; margin:0 auto; padding:20px; }
h1 { font-size:20px; margin:0 0 2px; }
.sub { color:var(--ink2); margin:0 0 16px; font-size:13px; }
.tiles { display:flex; gap:12px; flex-wrap:wrap; margin-bottom:16px; }
.tile { background:var(--panel); border:1px solid var(--line); border-radius:8px;
        padding:10px 16px; min-width:110px; }
.tile b { display:block; font-size:22px; }
.tile span { color:var(--ink2); font-size:12px; }
.filters { display:flex; gap:10px; flex-wrap:wrap; align-items:end; margin-bottom:14px;
           background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:12px; }
.filters label { display:flex; flex-direction:column; font-size:12px; color:var(--ink2); gap:3px; }
.filters input, .filters select { padding:5px 8px; border:1px solid var(--line); border-radius:6px;
           background:var(--surface); color:var(--ink); font-size:13px; width:130px; }
.count { font-size:13px; color:var(--ink2); margin-left:auto; align-self:center; }
.legend { display:flex; gap:16px; font-size:12px; color:var(--ink2); margin:6px 0 2px; }
.legend i { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:5px; }
#chartwrap { overflow-x:auto; background:var(--panel); border:1px solid var(--line);
             border-radius:8px; padding:8px; margin-bottom:16px; }
svg text { fill:var(--ink2); font-size:11px; }
svg .axis { stroke:var(--line); stroke-width:1; }
#tip { position:fixed; pointer-events:none; background:var(--ink); color:var(--surface);
       padding:6px 9px; border-radius:6px; font-size:12px; display:none; z-index:9; max-width:280px; }
.tablewrap { overflow-x:auto; border:1px solid var(--line); border-radius:8px; }
table { border-collapse:collapse; width:100%; font-size:12.5px; }
th, td { padding:6px 9px; text-align:left; white-space:nowrap; border-bottom:1px solid var(--line); }
th { background:var(--panel); cursor:pointer; position:sticky; top:0; user-select:none; }
th .dir { color:var(--ink2); font-size:10px; }
td a { color:var(--ds); text-decoration:none; }
tr:hover td { background:var(--panel); }
.type { display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:6px; }
footer { color:var(--ink2); font-size:12px; margin:14px 0; }
</style>
</head>
<body>
<main>
<h1>Drilling Rig Selector</h1>
<p class="sub">Vendor spec-sheet database — every value from the contractor's own published rig
specification (provenance linked per rig). Filter to shortlist; click headers to sort.</p>
<div class="tiles" id="tiles"></div>
<div class="filters">
  <label>Onshore / offshore
    <select id="f-shore"><option value="">All</option><option value="offshore">Offshore</option>
    <option value="onshore">Onshore</option></select>
  </label>
  <label>Rig type
    <select id="f-type"><option value="">All</option><option value="drillship">Drillship</option>
    <option value="semi_submersible">Semisubmersible</option><option value="jack_up">Jackup</option>
    <option value="land_rig">Land rig</option></select>
  </label>
  <label>Contractor <input id="f-owner" type="text" placeholder="contains…"></label>
  <label>Min water depth (ft) <input id="f-wd" type="number" min="0" step="500"></label>
  <label>Min hookload (kips) <input id="f-hook" type="number" min="0" step="100"></label>
  <label>Min moonpool length (m) <input id="f-mp" type="number" min="0" step="1"></label>
  <label>Min leg length (ft) <input id="f-leg" type="number" min="0" step="10"></label>
  <label>Generation
    <select id="f-gen"><option value="">All</option><option value="7th">7th</option>
    <option value="6th">6th</option><option value="5th">5th</option>
    <option value="super-spec">Super-spec (land)</option></select>
  </label>
  <label>Min quarters <input id="f-poB" type="number" min="0" step="10"></label>
  <label style="flex-direction:row;align-items:center;gap:6px">
    <input id="f-mpd" type="checkbox" style="width:auto"> MPD equipped</label>
  <span class="count" id="count"></span>
</div>
<div class="legend">
  <span><i style="background:var(--ds)"></i>Drillship</span>
  <span><i style="background:var(--ss)"></i>Semisubmersible</span>
  <span><i style="background:var(--ju)"></i>Jackup</span>
  <span><i style="background:var(--lr)"></i>Land rig</span>
  <span style="margin-left:auto">Water depth rating vs hookload — rigs whose sheet states both values</span>
</div>
<div id="chartwrap"></div>
<div class="tablewrap"><table id="tbl"><thead></thead><tbody></tbody></table></div>
<footer>Sources: official contractor rig spec sheets (Noble, Transocean, Valaris, Seadrill,
Borr Drilling, Shelf Drilling), retrieved 2026-07-12/13 — sha256-manifested under
<code>_data/raw/spec_pdfs/</code>. Blank cells: value not stated on the vendor sheet.
worldenergydata #998.</footer>
</main>
<div id="tip"></div>
<script>
const DATA = __DATA__;
const STATS = __STATS__;
const COLS = [
 ["VESSEL_NAME","Rig"],["OWNER","Contractor"],["RIG_TYPE","Type"],["RIG_DESIGN","Design"],
 ["YEAR_BUILT","Year"],["WATER_DEPTH_RATING_FT","Water depth (ft)"],
 ["DRILLING_DEPTH_RATING_FT","Drilling depth (ft)"],["LOA_M","LOA (m)"],["BEAM_M","Beam (m)"],
 ["MOONPOOL_LENGTH_M","Moonpool L (m)"],["MOONPOOL_WIDTH_M","Moonpool W (m)"],
 ["LEG_LENGTH_FT","Legs (ft)"],["CANTILEVER_REACH_FT","Cantilever (ft)"],
 ["VARIABLE_DECK_LOAD_ST","VDL (st)"],["HOOKLOAD_RATING_KIPS","Hookload (kips)"],
 ["DRAWWORKS_HP","Drawworks (HP)"],["WALKING_SYSTEM","Walking"],
 ["GENERATION","Gen"],["MPD_CAPABLE","MPD"],["DUAL_ACTIVITY","Dual activity"],
 ["CRANE_MAIN_CAPACITY_T","Crane (t)"],["QUARTERS_CAPACITY","Quarters"],
 ["DATA_SOURCE_URL","Spec sheet"]];
const TYPECOL = {drillship:"var(--ds)", semi_submersible:"var(--ss)", jack_up:"var(--ju)", land_rig:"var(--lr)"};
const TYPELBL = {drillship:"Drillship", semi_submersible:"Semi", jack_up:"Jackup", land_rig:"Land rig"};
let sortKey = "WATER_DEPTH_RATING_FT", sortDir = -1;

document.getElementById("tiles").innerHTML = [
  ["Rigs", STATS.rigs], ["Contractors", STATS.contractors], ["Drillships", STATS.drillships],
  ["Semis", STATS.semis], ["Jackups", STATS.jackups], ["Land classes", STATS.land]
].map(([k,v]) => `<div class="tile"><b>${v}</b><span>${k}</span></div>`).join("");

function filters() {
  const sh = document.getElementById("f-shore").value;
  const t = document.getElementById("f-type").value;
  const o = document.getElementById("f-owner").value.toLowerCase();
  const wd = +document.getElementById("f-wd").value || 0;
  const hk = +document.getElementById("f-hook").value || 0;
  const mp = +document.getElementById("f-mp").value || 0;
  const lg = +document.getElementById("f-leg").value || 0;
  const gen = document.getElementById("f-gen").value;
  const poB = +document.getElementById("f-poB").value || 0;
  const mpd = document.getElementById("f-mpd").checked;
  return DATA.filter(r =>
    (!sh || (sh === "onshore" ? r.IS_OFFSHORE === false : r.IS_OFFSHORE !== false)) &&
    (!t || r.RIG_TYPE === t) &&
    (!o || (r.OWNER||"").toLowerCase().includes(o)) &&
    (!wd || (r.WATER_DEPTH_RATING_FT||0) >= wd) &&
    (!hk || (r.HOOKLOAD_RATING_KIPS||0) >= hk) &&
    (!mp || (r.MOONPOOL_LENGTH_M||0) >= mp) &&
    (!lg || (r.LEG_LENGTH_FT||0) >= lg) &&
    (!gen || r.GENERATION === gen) &&
    (!poB || (r.QUARTERS_CAPACITY||0) >= poB) &&
    (!mpd || r.MPD_CAPABLE === true));
}
function fmt(v, col) {
  if (v === null || v === undefined) return "";
  if (col === "DATA_SOURCE_URL") return `<a href="${v}" target="_blank" rel="noopener">PDF</a>`;
  if (col === "RIG_TYPE") return `<span class="type" style="background:${TYPECOL[v]}"></span>${TYPELBL[v]||v}`;
  if (col === "YEAR_BUILT") return String(Math.round(v));
  if (col === "WALKING_SYSTEM" || col === "MPD_CAPABLE" || col === "DUAL_ACTIVITY")
    return v === true ? "\u2714" : "";
  if (typeof v === "number") return Number.isInteger(v) ? v.toLocaleString() : v.toLocaleString(undefined,{maximumFractionDigits:1});
  return v;
}
function render() {
  const rows = filters().slice().sort((a,b) => {
    const x = a[sortKey], y = b[sortKey];
    if (x == null) return 1; if (y == null) return -1;
    return (x < y ? -1 : x > y ? 1 : 0) * sortDir;
  });
  document.getElementById("count").textContent = `${rows.length} of ${DATA.length} rigs`;
  document.querySelector("#tbl thead").innerHTML = "<tr>" + COLS.map(([k,l]) =>
    `<th data-k="${k}">${l} <span class="dir">${k===sortKey ? (sortDir<0?"▼":"▲") : ""}</span></th>`).join("") + "</tr>";
  document.querySelector("#tbl tbody").innerHTML = rows.map(r =>
    "<tr>" + COLS.map(([k]) => `<td>${fmt(r[k],k)}</td>`).join("") + "</tr>").join("");
  document.querySelectorAll("#tbl th").forEach(th => th.onclick = () => {
    const k = th.dataset.k;
    if (k === sortKey) sortDir = -sortDir; else { sortKey = k; sortDir = -1; }
    render();
  });
  chart(rows);
}
function chart(rows) {
  const pts = rows.filter(r => r.HOOKLOAD_RATING_KIPS && r.WATER_DEPTH_RATING_FT);
  const W = 1200, H = 340, L = 70, B = 40, T = 14, R = 20;
  const xs = pts.map(p => p.WATER_DEPTH_RATING_FT || 0), ys = pts.map(p => p.HOOKLOAD_RATING_KIPS);
  const xmax = Math.max(1000, ...xs) * 1.06, ymax = Math.max(500, ...ys) * 1.08;
  const X = v => L + (v/xmax) * (W-L-R), Y = v => H-B - (v/ymax) * (H-B-T);
  let s = `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Water depth rating vs hookload scatter">`;
  s += `<line class="axis" x1="${L}" y1="${H-B}" x2="${W-R}" y2="${H-B}"/><line class="axis" x1="${L}" y1="${T}" x2="${L}" y2="${H-B}"/>`;
  for (let i = 0; i <= 4; i++) {
    const xv = xmax/1.06 * i/4, yv = ymax/1.08 * i/4;
    s += `<text x="${X(xv)}" y="${H-B+16}" text-anchor="middle">${Math.round(xv).toLocaleString()}</text>`;
    s += `<text x="${L-8}" y="${Y(yv)+4}" text-anchor="end">${Math.round(yv).toLocaleString()}</text>`;
  }
  s += `<text x="${(W+L)/2}" y="${H-6}" text-anchor="middle">Water depth rating (ft)</text>`;
  s += `<text x="14" y="${(H-B+T)/2}" transform="rotate(-90 14 ${(H-B+T)/2})" text-anchor="middle">Hookload (kips)</text>`;
  pts.forEach((p,i) => {
    s += `<circle data-i="${i}" cx="${X(p.WATER_DEPTH_RATING_FT||0)}" cy="${Y(p.HOOKLOAD_RATING_KIPS)}" r="5.5"
      fill="${TYPECOL[p.RIG_TYPE]}" fill-opacity="0.82" stroke="var(--surface)" stroke-width="1.5"/>`;
  });
  s += "</svg>";
  const wrap = document.getElementById("chartwrap");
  wrap.innerHTML = s;
  const tip = document.getElementById("tip");
  wrap.querySelectorAll("circle").forEach(c => {
    c.addEventListener("mousemove", e => {
      const p = pts[+c.dataset.i];
      tip.style.display = "block"; tip.style.left = (e.clientX+14)+"px"; tip.style.top = (e.clientY+10)+"px";
      tip.innerHTML = `<b>${p.VESSEL_NAME}</b> — ${p.OWNER||""}<br>${TYPELBL[p.RIG_TYPE]} · ${p.RIG_DESIGN||""}<br>` +
        `WD ${(p.WATER_DEPTH_RATING_FT||0).toLocaleString()} ft · hookload ${p.HOOKLOAD_RATING_KIPS.toLocaleString()} kips`;
    });
    c.addEventListener("mouseleave", () => tip.style.display = "none");
  });
}
["f-shore","f-type","f-owner","f-wd","f-hook","f-mp","f-leg","f-gen","f-poB","f-mpd"].forEach(id =>
  document.getElementById(id).addEventListener("input", render));
render();
</script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(_PROJECT_ROOT / "reports/rig-selector"))
    args = parser.parse_args()
    build(Path(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
