"""Multi-field deep-dive report — pick any of the 10 Lower Tertiary fields and see
its economics (by field/block/well) + drilling timeline / rig-days / depth cross-section /
3D schematic. Data-driven from all_fields_economics.json + all_fields_wells.json.
"""
from __future__ import annotations
import json, math, datetime as dt
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
E = json.loads((REPO / "reports/lower_tertiary/data/all_fields_economics.json").read_text())
W = json.loads((REPO / "reports/lower_tertiary/data/all_fields_wells.json").read_text())
PORT = {r["id"]: r for r in E["portfolio"]}
BYF = E["by_field"]
# order: producing (by NPV desc) then the rest
ORDER = sorted(PORT, key=lambda fid: ((PORT[fid].get("oil_bbl") or 0) > 0, PORT[fid].get("npv_usd") or -9e18), reverse=True)

def m0(x):
    try: return f"${x/1e6:,.0f}M"
    except: return "—"
def b2(x):
    try: return f"${x/1e9:,.2f}B"
    except: return "—"
def mmb(x):
    try: return f"{x/1e6:,.2f}"
    except: return "—"
def pct(x):
    try: return f"{x*100:,.1f}%" if x==x and x is not None else "n/a"
    except: return "—"
def pdate(s): return dt.datetime.strptime(s, "%Y-%m-%d")

# ---------- SVG builders (per field) ----------
def timeline_svg(wells):
    rows = [w for w in wells if w["spud"] and w["td"]]
    if not rows: return "<div class='lead2'>no drilling dates</div>"
    t0 = min(pdate(w["spud"]) for w in rows)
    t1 = max(pdate(w["td"]) for w in rows) + dt.timedelta(days=int(max((w["completion_days"] or 0) for w in rows)) + 40)
    W_, Lx, rowh, top = 1080, 70, max(12, min(24, int(420/len(rows)))), 24
    plotw = W_ - Lx - 16; span = max((t1 - t0).days, 1)
    def X(d): return Lx + (d - t0).days / span * plotw
    H = top + rowh*len(rows) + 26
    o = ['<svg viewBox="0 0 %d %d" width="100%%" style="font:10px system-ui">' % (W_, H)]
    for yr in range(t0.year, t1.year+1):
        x = X(dt.datetime(yr,1,1))
        if x < Lx: continue
        o.append('<line x1="%.0f" y1="%d" x2="%.0f" y2="%d" stroke="#ECEFF1"/>'%(x,top-4,x,H-20))
        o.append('<text x="%.0f" y="%d" fill="#90A4AE" text-anchor="middle">%d</text>'%(x,H-6,yr))
    for i,w in enumerate(rows):
        y=top+i*rowh; xs,xe=X(pdate(w["spud"])),X(pdate(w["td"]))
        xc=xe+(w["completion_days"] or 0)/span*plotw
        col="#1565C0" if w["producing"] else "#B0BEC5"
        o.append('<rect x="%.0f" y="%.0f" width="%.0f" height="%d" rx="2" fill="%s"><title>%s drilling %.0fd</title></rect>'%(xs,y+3,max(xe-xs,2),max(rowh-6,6),col,w["well_name"],w["drilling_days"]))
        o.append('<rect x="%.0f" y="%.0f" width="%.0f" height="%d" rx="2" fill="%s" opacity="0.38"/>'%(xe,y+3,max(xc-xe,1),max(rowh-6,6),col))
        if rowh >= 16:
            o.append('<text x="4" y="%.0f" fill="#37474F">%s%s</text>'%(y+rowh-5,w["well_name"][:8]," ★" if w["producing"] else ""))
    o.append('</svg>'); return "".join(o)

def rigdays_svg(wells):
    rows = wells
    if not rows: return ""
    maxd = max((w["rig_days"] for w in rows), default=1) or 1
    W_, Lx, rowh, top, barmax = 1080, 150, max(11, min(27, int(420/len(rows)))), 8, 680
    H = top + rowh*len(rows) + 6
    o = ['<svg viewBox="0 0 %d %d" width="100%%" style="font:10px system-ui">' % (W_, H)]
    for i,w in enumerate(rows):
        y=top+i*rowh; dw=w["drilling_days"]/maxd*barmax; cw=(w["completion_days"] or 0)/maxd*barmax
        if rowh >= 15:
            o.append('<text x="4" y="%.0f" fill="#37474F">%s%s <tspan fill="#B0BEC5">%s</tspan></text>'%(y+rowh-4,w["well_name"][:8],"★" if w["producing"] else "",(w["spud"] or "")[:7]))
        o.append('<rect x="%d" y="%.0f" width="%.0f" height="%d" fill="#0D47A1"><title>drilling %.0fd</title></rect>'%(Lx,y+3,dw,max(rowh-6,5),w["drilling_days"]))
        o.append('<rect x="%.0f" y="%.0f" width="%.0f" height="%d" fill="#64B5F6"/>'%(Lx+dw,y+3,cw,max(rowh-6,5)))
        if rowh >= 15:
            o.append('<text x="%.0f" y="%.0f" fill="#546E7A">%.0fd</text>'%(Lx+dw+cw+6,y+rowh-4,w["rig_days"]))
    o.append('</svg>'); return "".join(o)

def xsection_svg(wells, wd):
    rows=[w for w in wells if w["tvd_ft"]]
    if not rows: return ""
    maxd=max(w["tvd_ft"] for w in rows)*1.03; maxh=max((w["horiz_disp_ft"] or 0) for w in rows) or 1
    W_,H,top,cx=1080,420,14,540; ploth,halfw=H-top-26,470
    def Y(d): return top+d/maxd*ploth
    o=['<svg viewBox="0 0 %d %d" width="100%%" style="font:10px system-ui">'%(W_,H)]
    o.append('<rect x="40" y="%.0f" width="%d" height="%.0f" fill="#E3F2FD"/>'%(Y(0),W_-50,Y(wd)-Y(0)))
    o.append('<line x1="40" y1="%.0f" x2="%d" y2="%.0f" stroke="#90A4AE" stroke-dasharray="4 3"/>'%(Y(wd),W_-10,Y(wd)))
    o.append('<text x="%d" y="%.0f" fill="#607D8B" text-anchor="end">mudline %s ft</text>'%(W_-12,Y(wd)-4,format(int(wd),",")))
    for d in range(0,int(maxd),5000):
        o.append('<line x1="40" y1="%.0f" x2="%d" y2="%.0f" stroke="#ECEFF1"/>'%(Y(d),W_-10,Y(d)))
        o.append('<text x="6" y="%.0f" fill="#B0BEC5">%dk</text>'%(Y(d)+3,d//1000))
    for i,w in enumerate(rows):
        sign=1 if i%2==0 else -1; xb=cx+sign*((w["horiz_disp_ft"] or 0)/maxh)*halfw
        col="#1565C0" if w["producing"] else "#B0BEC5"
        o.append('<line x1="%.0f" y1="%.0f" x2="%.0f" y2="%.0f" stroke="%s" stroke-width="1.6"><title>%s MD %.0f TVD %.0f</title></line>'%(cx,Y(wd),xb,Y(w["tvd_ft"]),col,w["well_name"],w["md_ft"],w["tvd_ft"]))
        o.append('<circle cx="%.0f" cy="%.0f" r="2.5" fill="%s"/>'%(xb,Y(w["tvd_ft"]),col))
    o.append('</svg>'); return "".join(o)

def traj_traces(wells, wd):
    rows=wells; n=len(rows) or 1; tr=[]
    for i,w in enumerate(rows):
        ang=2*math.pi*i/n; xh,yh=520*math.cos(ang),520*math.sin(ang)
        horiz=w["horiz_disp_ft"] or 0; baz=ang+0.7
        xb,yb=xh+horiz*math.cos(baz),yh+horiz*math.sin(baz)
        col="#1565C0" if w["producing"] else "#B0BEC5"
        tr.append({"x":[xh,xh,xb],"y":[yh,yh,yb],"z":[0,-wd,-w["tvd_ft"]],"mode":"lines","type":"scatter3d",
                   "line":{"color":col,"width":3},"name":w["well_name"][:8]+("★" if w["producing"] else "")})
    return tr

# ---------- economics table per field ----------
def econ_table(fid):
    p = PORT[fid]; bf = BYF.get(fid, {})
    def row(name, sub, oil, rev, cap, npv, mirr, neg=None):
        nn = "neg" if (neg if neg is not None else (npv or 0) < 0) else "pos"
        return (f'<tr><td class="name"><div>{name}</div><div class="rsub">{sub}</div></td>'
                f'<td>{mmb(oil)}</td><td>{m0(rev)}</td><td>{m0(cap)}</td>'
                f'<td class="{nn}">{m0(npv)}</td><td>{pct(mirr)}</td></tr>')
    h = row(p["field"]+" (field)", f'{p.get("dev_system","")} · {p.get("wellbores") or "—"} bores · authoritative',
            p.get("oil_bbl"), p.get("revenue_usd"), p.get("capex_usd"), p.get("npv_usd"), p.get("mirr_annual"))
    for blk, r in sorted(bf.get("by_block", {}).items(), key=lambda kv: -(kv[1].get("oil_bbl") or 0)):
        h += row(f"Block {blk}", f'{r.get("share_pct","")}% of field', r.get("oil_bbl"), r.get("revenue_usd"), r.get("capex_usd"), r.get("npv_usd"), r.get("mirr_annual"))
    for r in sorted(bf.get("by_well", {}).values(), key=lambda w: -(w.get("oil_bbl") or 0)):
        h += row(f'…{r.get("api","")[-6:]}', f'{r.get("share_pct","")}% · well ≈', r.get("oil_bbl"), r.get("revenue_usd"), r.get("capex_usd"), r.get("npv_usd"), r.get("mirr_annual"))
    return h

# ---------- per-field panel ----------
def panel(fid, active):
    p = PORT[fid]; wsum = W.get(fid, {}); wells = wsum.get("wells", [])
    meta = p.get("public_metadata", {})
    has_prod = (p.get("oil_bbl") or 0) > 0
    kpis = [
        ("Oil", f'{(p.get("oil_bbl") or 0)/1e6:,.1f} MMbbl', p.get("status","")),
        ("Revenue", b2(p.get("revenue_usd")), "historical WTI"),
        ("CAPEX", b2(p.get("capex_usd")), f'{p.get("wellbores") or "—"} bores'),
        ("NPV@10%", m0(p.get("npv_usd")), "full-cycle", (p.get("npv_usd") or 0) < 0),
        ("MIRR", pct(p.get("mirr_annual")), "annual"),
        ("Rig days", f'{wsum.get("total_rig_days",0):,.0f}', f'{wsum.get("campaign_start","")}→{wsum.get("campaign_end","")}'),
    ]
    kc = "".join(f'<div class="kpi-card {"neg" if (len(k)>3 and k[3]) else ""}"><div class="label">{k[0]}</div><div class="value">{k[1]}</div><div class="sub">{k[2]}</div></div>' for k in kpis)
    metabar = ""
    if meta:
        metabar = (f'<div class="metabar"><b>{meta.get("operator","")}</b> · {meta.get("partners","")} · '
                   f'{meta.get("facility","")} · {meta.get("play","")}</div>')
    drill = ""
    if wells:
        drill = (f'<h3>Drilling campaign timeline</h3><div class="lead2">spud→TD (solid) + completion (faded); ★ = producing bore.</div>{timeline_svg(wells)}'
                 f'<h3>Rig days by bore</h3>{rigdays_svg(wells)}'
                 f'<h3>Depth cross-section (indicative)</h3>{xsection_svg(wells, wsum.get("water_depth_ft",0))}'
                 f'<h3>3D schematic (WebGL)</h3><div class="traj" data-field="{fid}" style="height:460px"></div>')
    econ_note = ("" if has_prod else '<div class="lead2">No production yet — economics reflect sunk D&amp;C only.</div>')
    return (f'<div class="fieldpanel" data-field="{fid}" {"" if active else "hidden"}>'
            f'{metabar}<div class="kpi-row">{kc}</div>'
            f'<div class="section"><h2>Economics — by field / block / well</h2>{econ_note}'
            f'<table><thead><tr><th class="name">Unit</th><th>Oil (MMbbl)</th><th>Revenue</th><th>CAPEX</th><th>NPV@10%</th><th>MIRR</th></tr></thead>'
            f'<tbody>{econ_table(fid)}</tbody></table></div>'
            f'<div class="section">{drill}</div></div>')

PANELS = "".join(panel(fid, i == 0) for i, fid in enumerate(ORDER))
OPTIONS = "".join(f'<option value="{fid}">{PORT[fid]["field"]} ({"producing" if (PORT[fid].get("oil_bbl") or 0)>0 else PORT[fid].get("status","")})</option>' for fid in ORDER)
TRACES = {fid: traj_traces(W.get(fid, {}).get("wells", []), W.get(fid, {}).get("water_depth_ft", 0)) for fid in ORDER}

html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Lower Tertiary — Field Deep-Dive</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:#F5F7FA;color:#212121}}
.report-header{{background:linear-gradient(135deg,#0D47A1,#1565C0 55%,#1976D2);color:#fff;padding:30px 48px}}
.report-header h1{{font-size:24px;font-weight:700}}
.report-header .subtitle{{margin-top:6px;opacity:.88;font-size:14px}}
.selbar{{padding:16px 32px;background:#ECEFF1;border-bottom:1px solid #CFD8DC;display:flex;gap:12px;align-items:center}}
.selbar label{{font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:#607D8B;font-weight:600}}
.selbar select{{font-size:15px;padding:8px 14px;border:1px solid #B0BEC5;border-radius:8px;background:#fff;font-weight:600;color:#1565C0;min-width:280px}}
.metabar{{max-width:1320px;margin:14px auto 0;padding:10px 32px;font-size:12px;color:#546E7A}}
.kpi-row{{display:flex;gap:14px;padding:14px 32px;flex-wrap:wrap;max-width:1320px;margin:0 auto}}
.kpi-card{{background:#fff;border-radius:10px;padding:14px 18px;flex:1;min-width:140px;box-shadow:0 1px 4px rgba(0,0,0,.07);border-top:3px solid #1565C0}}
.kpi-card.neg{{border-top-color:#C62828}} .kpi-card.neg .value{{color:#C62828}}
.kpi-card .label{{font-size:11px;text-transform:uppercase;letter-spacing:.6px;color:#78909C;font-weight:600}}
.kpi-card .value{{font-size:19px;font-weight:700;color:#1A237E;margin-top:3px}}
.kpi-card .sub{{font-size:10px;color:#90A4AE;margin-top:2px}}
.content,.section-wrap{{max-width:1320px;margin:0 auto;padding:0 32px}}
.section{{background:#fff;border-radius:12px;padding:22px 26px;margin:14px 32px;max-width:1320px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
.section{{margin-left:auto;margin-right:auto}}
.section h2{{font-size:16px;color:#0D47A1;margin-bottom:8px}}
.section h3{{font-size:13px;color:#37474F;margin:16px 0 4px}}
.lead2{{font-size:12px;color:#78909C;margin-bottom:8px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th,td{{text-align:right;padding:8px 10px;border-bottom:1px solid #ECEFF1}}
th{{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:#78909C;font-weight:600;background:#FAFBFC}}
td.name,th.name{{text-align:left}} td.name div:first-child{{font-weight:600;color:#263238}}
.rsub{{font-size:11px;color:#90A4AE}}
td.neg{{color:#C62828;font-weight:600}} td.pos{{color:#2E7D32;font-weight:600}}
svg{{display:block;margin:4px 0 6px}}
.foot{{font-size:11px;color:#90A4AE;padding:18px 32px;max-width:1320px;margin:0 auto;line-height:1.6}}
code{{background:#ECEFF1;padding:1px 6px;border-radius:4px;font-size:12px}}
</style></head><body>
<div class="report-header">
  <h1>Gulf of Mexico Lower Tertiary — Field Deep-Dive</h1>
  <div class="subtitle">Pick a field: economics by field / block / well + drilling timeline, rig days, and well schematics — all from public BSEE data</div>
</div>
<div class="selbar"><label for="fsel">Field</label><select id="fsel" onchange="pick(this.value)">{OPTIONS}</select>
  <span class="rsub">10 fields · field economics validated vs FDAS V30 golden baseline (~0.001%)</span></div>
<div id="panels">{PANELS}</div>
<div class="foot">
  Field economics = sanctioned golden baseline (independently reproduced from local OGOR <code>.bin</code>). Per-well/block =
  indicative decomposition (real production/revenue; shared CAPEX + fixed OPEX allocated by production share). Drilling: real
  FDAS V30 per-bore record; 3D is indicative (real MD/TVD + water depth; schematic wellhead/azimuth — no public deviation survey).
  Vintage OGOR+WTI through 2025-05. Input files: <code>config/ong_field_development/</code>. ACE Engineer · worldenergydata.
</div>
<script>
const TR={json.dumps(TRACES)};
const plotted={{}};
function draw3d(fid){{
  const host=document.querySelector('.fieldpanel[data-field="'+fid+'"] .traj');
  if(!host||plotted[fid])return; plotted[fid]=true;
  try{{Plotly.newPlot(host,TR[fid],{{margin:{{l:0,r:0,t:0,b:0}},scene:{{xaxis:{{title:"East ft"}},yaxis:{{title:"North ft"}},zaxis:{{title:"Depth ft TVD"}},aspectmode:"manual",aspectratio:{{x:1,y:1,z:1.7}}}},legend:{{font:{{size:9}}}}}},{{responsive:true}});}}catch(e){{}}
}}
function pick(fid){{
  document.querySelectorAll('.fieldpanel').forEach(p=>p.hidden = p.dataset.field!==fid);
  draw3d(fid);
}}
draw3d("{ORDER[0]}");
</script>
</body></html>"""

(REPO / "reports/gtm/2026-06-17-lower-tertiary-field-deepdive.html").write_text(html)
print("DEEP-DIVE REPORT WRITTEN", len(html), "bytes;", len(ORDER), "fields")
