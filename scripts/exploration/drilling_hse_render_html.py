"""Render drilling-HSE-patterns JSON sidecar into an interactive Plotly HTML report.

Per docs/HTML_REPORTING_STANDARDS.md: interactive Plotly (CDN), hover/zoom/legend.
Stdlib only — emits self-contained HTML that pulls Plotly from CDN.

Issue: https://github.com/vamseeachanta/worldenergydata/issues/426
"""

from __future__ import annotations

import argparse
import html as html_tools
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATE_TAG = "2026-07-05"
JSON_PATH = REPO / "reports" / "hse" / f"drilling-hse-patterns-{DATE_TAG}.json"
HTML_PATH = REPO / "reports" / "hse" / f"drilling-hse-patterns-{DATE_TAG}.html"


def render(json_path: Path, html_path: Path) -> None:
    d = json.loads(json_path.read_text(encoding="utf-8"))
    if d.get("status") != "evaluated":
        reason = html_tools.escape(d.get("reason", "QA did not pass"))
        html_path.write_text(
            '<!DOCTYPE html><html lang="en"><meta charset="utf-8">'
            "<title>HSE analysis not evaluated</title><h1>Not evaluated</h1>"
            f"<p>{reason}</p></html>\n",
            encoding="utf-8",
            newline="\n",
        )
        return
    source = next(e for e in d["source"]["files"] if e["file"] == d["source_file"])
    source_kind = html_tools.escape(d["source"]["source_kind"])
    download_date = html_tools.escape(source["downloaded_at"])
    source_url = html_tools.escape(source["url"], quote=True)
    date_range = " to ".join(d["incinv_date_range"])
    revision_date = source["downloaded_at"][:10]

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
<title>Drilling-HSE Patterns — BSEE INCINV (DRILL.*) — {revision_date}</title>
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
<div class="sub">Dataset: {source_kind} &middot;
 Source: <a href="{source_url}">BSEE INCINV accident investigations</a>
 &middot; Downloaded {download_date} &middot; Occurrence dates {date_range}</div>

<div class="note">Drilling-phase incidents are derived by the repo-canonical
 <code>IncidentClassifier</code> cut to <code>activity == "DRILL"</code> over the BSEE
 INCINV records. Counts describe investigation records, not a complete incident census
 or exposure-normalized risk rates. Severity is a text-derived proxy, not a count of
 fatalities or injuries. Aggregate-only. Engineering interpretation, not a regulatory finding.
 The source endpoint is mutable. Recalculation requires the exact archived input;
 no durable public copy of that input is supplied. Chart CSVs record the published values.</div>

<h2>Revision history</h2>
<table><thead><tr><th>Revision</th><th>Date</th><th>Change and reason</th></tr></thead>
<tbody><tr><td>1</td><td>2026-07-05</td><td>Initial drilling investigation analysis.</td></tr>
<tr><td>2</td><td>{revision_date}</td><td>Refresh from the public source with a sealed manifest,
 input QA and downloadable chart values so the figures can be reproduced.</td></tr>
<tr><td>3</td><td>{revision_date}</td><td>Restore confidence buckets and zero-fill source years.
 Correct earlier reproducibility wording: recalculation requires the exact archived input;
 no durable public archive copy is supplied with this report.</td></tr></tbody></table>

<div class="kpis">
 <div class="kpi"><div class="v">{payload['drill_total']}</div>
  <div class="l">DRILL.* investigation records</div></div>
 <div class="kpi"><div class="v">{payload['incinv_total']}</div>
  <div class="l">INCINV records screened</div></div>
 <div class="kpi"><div class="v">{payload['drill_pct']}%</div>
  <div class="l">of investigation records</div></div>
 <div class="kpi"><div class="v">{sub.get('well_control',0)}</div>
  <div class="l">well-control investigation records</div></div>
</div>

<div class="chart" id="c_sub"></div>
<div class="chart" id="c_sev"></div>
<div class="chart" id="c_year"></div>
<div class="chart" id="c_area"></div>

<footer>Generated from <code>reports/hse/drilling-hse-patterns-{DATE_TAG}.json</code>.
 <a href="incinv-manifest.json">Source manifest</a> &middot;
 <a href="incinv-qa.json">Input QA</a> &middot;
 Chart values (investigation records [count]):
 <a href="drilling-phase-values.csv">phase</a>,
 <a href="drilling-severity-values.csv">severity proxy</a>,
 <a href="drilling-year-values.csv">year</a>,
 <a href="drilling-area-values.csv">area</a>.
 The historical filename is retained; the source download date above identifies this refresh.
 The area chart includes all source area codes. Years without DRILL records are
 zero-filled across the source occurrence window; zero does not establish complete
 incident coverage. The percentage is rounded to one decimal place.
 Confidence buckets remain in the JSON; raw accident-type text is excluded to avoid identities.</footer>

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

bar('c_sub',D.sub,'DRILL.* by drilling phase (subactivity)','investigation records','#2c7fb8',true);
bar('c_sev',D.sev,'DRILL.* by severity proxy','investigation records','#c0392b',true);

// temporal line
const yk=Object.keys(D.years), yv=yk.map(k=>D.years[k]);
Plotly.newPlot('c_year',
  [{{type:'scatter',mode:'lines+markers',x:yk,y:yv,line:{{color:'#16a085'}},
     hovertemplate:'%{{x}}: %{{y}} investigation records<extra></extra>'}}],
  {{title:'DRILL.* incidents by year of occurrence',
    xaxis:{{title:'year'}},yaxis:{{title:'investigation records'}},margin:{{t:50}}}},cfg);

bar('c_area',D.areas,'DRILL.* by BSEE area','investigation records','#8e44ad',true);
</script>
</body></html>
"""
    html_path.write_text(html, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=JSON_PATH)
    parser.add_argument("--output", type=Path, default=HTML_PATH)
    args = parser.parse_args()
    render(args.input, args.output)


if __name__ == "__main__":
    main()
