"""Render drilling-HSE-patterns JSON sidecar into an interactive Plotly HTML report.

Per docs/HTML_REPORTING_STANDARDS.md: interactive Plotly (CDN), hover/zoom/legend.
Stdlib only — emits self-contained HTML that pulls Plotly from CDN.

Issue: https://github.com/vamseeachanta/worldenergydata/issues/426
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATE_TAG = "2026-06-19"
JSON_PATH = REPO / "reports" / "hse" / f"drilling-hse-patterns-{DATE_TAG}.json"
HTML_PATH = REPO / "reports" / "hse" / f"drilling-hse-patterns-{DATE_TAG}.html"


def main() -> None:
    d = json.loads(JSON_PATH.read_text())

    sub = d["drill_subactivity_distribution"]
    sev = d["drill_severity_proxy"]
    years = d["drill_by_year"]
    areas = d["drill_top_areas"]

    payload = {
        "sub": sub,
        "sev": sev,
        "years": years,
        "areas": areas,
        "drill_total": d["drill_total"],
        "incinv_total": d["incinv_total_records"],
        "drill_pct": d["drill_pct_of_incinv"],
    }

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Drilling-HSE Patterns — BSEE INCINV (DRILL.*) — {DATE_TAG}</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
      max-width:1100px;margin:24px auto;padding:0 18px;color:#1a1a1a;}}
 h1{{font-size:1.5rem;margin-bottom:4px;}}
 .sub{{color:#555;margin-bottom:18px;}}
 .kpis{{display:flex;gap:18px;flex-wrap:wrap;margin:18px 0;}}
 .kpi{{background:#f4f6f8;border-radius:10px;padding:14px 20px;min-width:150px;}}
 .kpi .v{{font-size:1.6rem;font-weight:700;}}
 .kpi .l{{color:#666;font-size:.85rem;}}
 .chart{{margin:26px 0;}}
 .note{{background:#fff8e6;border-left:4px solid #e0b400;padding:10px 14px;
        border-radius:6px;color:#5a4b00;font-size:.9rem;}}
 footer{{margin-top:30px;color:#888;font-size:.8rem;}}
</style></head><body>
<h1>Drilling-HSE Patterns &mdash; BSEE INCINV (DRILL.*)</h1>
<div class="sub">Issue #426 (child of #423, sibling of #416) &middot; Data as of {DATE_TAG}
 &middot; Source: BSEE INCINV accident investigations (1996&ndash;2021)</div>

<div class="note">Drilling-phase incidents are derived by the repo-canonical
 <code>IncidentClassifier</code> cut to <code>activity == "DRILL"</code> over the BSEE
 INCINV records. The assembled <code>hse_incidents.db</code> is not materialized in
 this environment, so this report uses the authoritative raw INCINV source directly.
 Aggregate-only; no operators named. Engineering interpretation, not a regulatory finding.</div>

<div class="kpis">
 <div class="kpi"><div class="v">{payload['drill_total']}</div><div class="l">DRILL.* incidents</div></div>
 <div class="kpi"><div class="v">{payload['incinv_total']}</div><div class="l">INCINV records screened</div></div>
 <div class="kpi"><div class="v">{payload['drill_pct']}%</div><div class="l">of investigated incidents</div></div>
 <div class="kpi"><div class="v">{sub.get('well_control',0)}</div><div class="l">well-control events</div></div>
</div>

<div class="chart" id="c_sub"></div>
<div class="chart" id="c_sev"></div>
<div class="chart" id="c_year"></div>
<div class="chart" id="c_area"></div>

<footer>Generated from <code>reports/hse/drilling-hse-patterns-{DATE_TAG}.json</code>.
 See <code>drilling-hse-patterns-{DATE_TAG}.md</code> for full findings and limitations.</footer>

<script>
const D = {json.dumps(payload)};
const cfg = {{responsive:true, displaylogo:false,
  modeBarButtonsToAdd:['toImage'], toImageButtonOptions:{{format:'png'}}}};

function bar(div,obj,title,xtitle,color,horizontal){{
  const keys=Object.keys(obj), vals=keys.map(k=>obj[k]);
  const trace = horizontal
    ? {{type:'bar',orientation:'h',y:keys,x:vals,marker:{{color:color}},
        hovertemplate:'%{{y}}: %{{x}}<extra></extra>'}}
    : {{type:'bar',x:keys,y:vals,marker:{{color:color}},
        hovertemplate:'%{{x}}: %{{y}}<extra></extra>'}};
  Plotly.newPlot(div,[trace],
    {{title:title,xaxis:{{title:horizontal?xtitle:''}},yaxis:{{title:horizontal?'':xtitle}},
      margin:{{l:horizontal?130:50,t:50,r:20,b:60}}}},cfg);
}}

bar('c_sub',D.sub,'DRILL.* by drilling phase (subactivity)','incidents','#2c7fb8',true);
bar('c_sev',D.sev,'DRILL.* by severity proxy','incidents','#c0392b',true);

// temporal line
const yk=Object.keys(D.years), yv=yk.map(k=>D.years[k]);
Plotly.newPlot('c_year',
  [{{type:'scatter',mode:'lines+markers',x:yk,y:yv,line:{{color:'#16a085'}},
     hovertemplate:'%{{x}}: %{{y}} incidents<extra></extra>'}}],
  {{title:'DRILL.* incidents by year of occurrence',
    xaxis:{{title:'year'}},yaxis:{{title:'incidents'}},margin:{{t:50}}}},cfg);

bar('c_area',D.areas,'DRILL.* top BSEE areas','incidents','#8e44ad',true);
</script>
</body></html>
"""
    HTML_PATH.write_text(html)
    print(f"Wrote {HTML_PATH.relative_to(REPO)} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
