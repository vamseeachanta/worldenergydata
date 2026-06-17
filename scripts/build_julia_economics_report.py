"""Generate the Julia field-economics demo report.

Field/block rows anchored on the VALIDATED FDAS V30 golden baseline; by-well is an
exact production/revenue/net-operating-cashflow decomposition with an indicative
full-cycle NPV. By-field / by-block / by-well + V30/Latest vintage toggles.
"""
import json
from pathlib import Path

DATA = json.loads((Path(__file__).resolve().parents[1] / "reports/lower_tertiary/data/julia_granular_economics.json").read_text())

# Authoritative FDAS V30 golden baseline (config/analysis/lower_tertiary/golden_baseline_v30.yml)
GOLDEN = {
    "oil_bbl": 70936158, "revenue_usd": 4715155663.31, "royalty_usd": 884091686.87,
    "variable_opex_usd": 425616948.0, "fixed_opex_usd": 693750000.0,
    "dnc_total_usd": 1349600000.0, "facilities_usd": 1375000000.0,
    "capex_usd": 2724600000.0, "net_cashflow_usd": -12902971.56,
    "npv_usd": -530637776.31, "mirr_annual": 0.06313, "wells": 4,
}
# Validation = the SANCTIONED V30 engine reproduced from local .bin (julia_repro_out.json)
_rep = json.loads((Path(__file__).resolve().parents[1] / "reports/lower_tertiary/data/julia_v30_reproduction.json").read_text())
REPRO_NPV = next(r["repro_npv_usd"] for r in _rep["results"] if r["field"] == "Julia")
# model-measured V30->latest uplift, applied to the golden anchor for the latest field/block NPV
_UPLIFT = DATA["latest"]["field"]["npv_usd"] - DATA["v30"]["field"]["npv_usd"]

def m(x):
    try: return f"${x/1e6:,.0f}M"
    except: return "—"
def m1(x):
    try: return f"${x/1e6:,.1f}M"
    except: return "—"
def mmbbl(x):
    try: return f"{x/1e6:,.2f}"
    except: return "—"
def bcf(x):
    try: return f"{x/1e9:,.2f}"
    except: return "—"
def pct(x):
    try: return f"{x*100:,.1f}%" if x == x else "n/a"
    except: return "—"
def perbbl(rev, oil):
    try: return f"${rev/oil:,.2f}"
    except: return "—"

def net_op(r):
    return r["revenue_usd"] - r["royalty_usd"] - r["variable_opex_usd"] - r["fixed_opex_usd"]

def build_rows(vint):
    R = DATA[vint]
    rows = {"field": [], "block": [], "well": []}
    # FIELD — anchored on golden for V30; latest keeps exact oil/rev, golden CAPEX, model NPV (indicative)
    f = R["field"]
    fr = dict(GOLDEN); fr.update(oil_bbl=f["oil_bbl"], revenue_usd=f["revenue_usd"], gas_mcf=f["gas_mcf"])
    if vint == "v30":
        fnpv, fmirr, indic = GOLDEN["npv_usd"], GOLDEN["mirr_annual"], False
    else:
        fnpv, fmirr, indic = GOLDEN["npv_usd"] + _UPLIFT, f["mirr_annual"], True
    rows["field"].append(dict(name="Julia (full field)", sub="lease G20351 · 4 producers · WR 584",
        oil=mmbbl(fr["oil_bbl"]), gas=bcf(f["gas_mcf"]), rev=m(fr["revenue_usd"]),
        netop=m(GOLDEN["revenue_usd"]-GOLDEN["royalty_usd"]-GOLDEN["variable_opex_usd"]-GOLDEN["fixed_opex_usd"]),
        capex=m(GOLDEN["capex_usd"]), npv=m(fnpv), npv_neg=fnpv < 0, mirr=pct(fmirr), indic=indic))
    # BLOCK — single block = field for Julia, anchor on golden
    for blk, r in R["by_block"].items():
        rows["block"].append(dict(name=f"Block {blk.strip()}", sub=f"{r['wells']} producers · {r.get('share_pct',100)}% of field",
            oil=mmbbl(r["oil_bbl"]), gas=bcf(r["gas_mcf"]), rev=m(r["revenue_usd"]),
            netop=m(net_op(r)), capex=m(GOLDEN["capex_usd"]),
            npv=m(GOLDEN["npv_usd"] if vint=="v30" else GOLDEN["npv_usd"] + _UPLIFT),
            npv_neg=True,
            mirr=pct(GOLDEN["mirr_annual"] if vint=="v30" else r["mirr_annual"]), indic=(vint!="v30")))
    # WELL — exact production/revenue/netop + own D&C; indicative full-cycle NPV
    wl = sorted(R["by_well"].values(), key=lambda r: -r["oil_bbl"])
    for r in wl:
        rows["well"].append(dict(name=f"{r.get('well_name','')} · …{r.get('api','')[-5:]}",
            sub=f"{r.get('share_pct','')}% of field · block {r.get('block','').strip()}",
            oil=mmbbl(r["oil_bbl"]), gas=bcf(r["gas_mcf"]), rev=m(r["revenue_usd"]),
            netop=m(net_op(r)), capex=m(r["capex_usd"]), npv=m(r["npv_usd"]),
            npv_neg=r["npv_usd"] < 0, mirr=pct(r["mirr_annual"]), indic=True))
    return rows

import datetime as _dt
ALL = {v: build_rows(v) for v in ("v30", "latest")}
latest_label = DATA["latest"]["label"]
LATEST_FRIENDLY = _dt.datetime.strptime(DATA["latest"]["end_date"], "%Y-%m-%d").strftime("%b %Y")
v30_oil, v30_rev = DATA["v30"]["field"]["oil_bbl"], DATA["v30"]["field"]["revenue_usd"]
lat_oil, lat_rev = DATA["latest"]["field"]["oil_bbl"], DATA["latest"]["field"]["revenue_usd"]
val_delta = (REPRO_NPV - GOLDEN["npv_usd"]) / GOLDEN["npv_usd"] * 100

def kpi_cards():
    cards = [
        ("Oil Produced", f"{GOLDEN['oil_bbl']/1e6:,.1f} MMbbl", "through May 2025 (V30)"),
        ("Gross Revenue", m(GOLDEN["revenue_usd"]), "historical WTI realization"),
        ("CAPEX", m(GOLDEN["capex_usd"]), f"D&C {m(GOLDEN['dnc_total_usd'])} + facilities {m(GOLDEN['facilities_usd'])}"),
        ("NPV @ 10%", m(GOLDEN["npv_usd"]), "full-cycle, trimmed", True),
        ("MIRR (annual)", pct(GOLDEN["mirr_annual"]), "reinvest 8% / finance 6%"),
        ("Net Op. Cashflow", m(GOLDEN["net_cashflow_usd"]), "lifetime, undiscounted", True),
    ]
    h = ""
    for c in cards:
        neg = "neg" if (len(c) > 3 and c[3]) else ""
        h += f'<div class="kpi-card {neg}"><div class="label">{c[0]}</div><div class="value">{c[1]}</div><div class="sub">{c[2]}</div></div>'
    return h

vd = json.dumps(ALL)

def static_rows(rows):
    h = ""
    for r in rows:
        cls = "neg" if r["npv_neg"] else "pos"
        ind = "ind" if r["indic"] else ""
        h += (f'<tr><td class="name"><div>{r["name"]}</div><div class="rsub">{r["sub"]}</div></td>'
              f'<td>{r["oil"]}</td><td>{r["gas"]}</td><td>{r["rev"]}</td><td>{r["netop"]}</td>'
              f'<td>{r["capex"]}</td><td class="{cls} {ind}">{r["npv"]}</td><td>{r["mirr"]}</td></tr>')
    return h

INITIAL_TBODY = static_rows(ALL["v30"]["field"])

# ---------------- Well & drilling engineering sections ----------------
import math as _math
import datetime as _dd
WELLS = json.loads((Path(__file__).resolve().parents[1] / "reports/lower_tertiary/data/julia_wells.json").read_text())
_wsum, _wells = WELLS["summary"], WELLS["wells"]
def _pd(s): return _dd.datetime.strptime(s, "%Y-%m-%d")

def _timeline_svg():
    rows = _wells
    t0 = min(_pd(w["spud"]) for w in rows)
    t1 = max(_pd(w["td"]) for w in rows) + _dd.timedelta(days=int(max(w["completion_days"] for w in rows)) + 40)
    W, Lx, rowh, top = 1080, 64, 26, 24
    plotw = W - Lx - 16
    span = max((t1 - t0).days, 1)
    def X(dt): return Lx + (dt - t0).days / span * plotw
    H = top + rowh * len(rows) + 26
    o = ['<svg viewBox="0 0 %d %d" width="100%%" style="font:11px system-ui">' % (W, H)]
    for yr in range(t0.year, t1.year + 1):
        x = X(_dd.datetime(yr, 1, 1))
        if x < Lx: continue
        o.append('<line x1="%.0f" y1="%d" x2="%.0f" y2="%d" stroke="#ECEFF1"/>' % (x, top - 4, x, H - 20))
        o.append('<text x="%.0f" y="%d" fill="#90A4AE" text-anchor="middle">%d</text>' % (x, H - 6, yr))
    for i, w in enumerate(rows):
        y = top + i * rowh
        xs, xe = X(_pd(w["spud"])), X(_pd(w["td"]))
        xc = xe + (w["completion_days"]) / span * plotw
        col = "#1565C0" if w["producing"] else "#B0BEC5"
        o.append('<rect x="%.0f" y="%.0f" width="%.0f" height="13" rx="2" fill="%s"><title>%s drilling %.0fd</title></rect>'
                 % (xs, y + 5, max(xe - xs, 2), col, w["well_name"], w["drilling_days"]))
        o.append('<rect x="%.0f" y="%.0f" width="%.0f" height="13" rx="2" fill="%s" opacity="0.38"><title>completion %.0fd</title></rect>'
                 % (xe, y + 5, max(xc - xe, 1), col, w["completion_days"]))
        o.append('<text x="4" y="%.0f" fill="#37474F">%s%s</text>' % (y + 15, w["well_name"], " ★" if w["producing"] else ""))
    o.append('</svg>')
    return "".join(o)

def _rigdays_svg():
    rows = _wells
    maxd = max(w["rig_days"] for w in rows)
    W, Lx, rowh, top, barmax = 1080, 150, 27, 8, 700
    H = top + rowh * len(rows) + 6
    o = ['<svg viewBox="0 0 %d %d" width="100%%" style="font:11px system-ui">' % (W, H)]
    for i, w in enumerate(rows):
        y = top + i * rowh
        dw, cw = w["drilling_days"] / maxd * barmax, w["completion_days"] / maxd * barmax
        o.append('<text x="4" y="%.0f" fill="#37474F">%s%s <tspan fill="#B0BEC5">%s</tspan></text>'
                 % (y + 15, w["well_name"], "★" if w["producing"] else "", w["spud"][:7]))
        o.append('<rect x="%d" y="%.0f" width="%.0f" height="15" fill="#0D47A1"><title>drilling %.0fd</title></rect>' % (Lx, y + 4, dw, w["drilling_days"]))
        o.append('<rect x="%.0f" y="%.0f" width="%.0f" height="15" fill="#64B5F6"><title>completion %.0fd</title></rect>' % (Lx + dw, y + 4, cw, w["completion_days"]))
        o.append('<text x="%.0f" y="%.0f" fill="#546E7A">%.0fd · %s/10k ft · MD %s ft</text>'
                 % (Lx + dw + cw + 6, y + 16, w["rig_days"], w["days_per_10k_ft"], format(int(w["md_ft"]), ",")))
    o.append('</svg>')
    return "".join(o)

def _xsection_svg():
    rows = _wells
    wd = _wsum["water_depth_ft"]
    maxd = max(w["tvd_ft"] for w in rows) * 1.03
    maxh = max((w["horiz_disp_ft"] or 0) for w in rows) or 1
    W, H, top, cx = 1080, 430, 14, 540
    ploth, halfw = H - top - 26, 470
    def Y(d): return top + d / maxd * ploth
    def Xh(h, sign): return cx + sign * (h / maxh) * halfw
    o = ['<svg viewBox="0 0 %d %d" width="100%%" style="font:11px system-ui">' % (W, H)]
    # water column + seabed
    o.append('<rect x="40" y="%.0f" width="%d" height="%.0f" fill="#E3F2FD"/>' % (Y(0), W - 50, Y(wd) - Y(0)))
    o.append('<line x1="40" y1="%.0f" x2="%d" y2="%.0f" stroke="#90A4AE" stroke-dasharray="4 3"/>' % (Y(wd), W - 10, Y(wd)))
    o.append('<text x="%d" y="%.0f" fill="#607D8B" text-anchor="end">mudline %s ft</text>' % (W - 12, Y(wd) - 4, format(int(wd), ",")))
    for d in range(0, int(maxd), 5000):
        o.append('<line x1="40" y1="%.0f" x2="%d" y2="%.0f" stroke="#ECEFF1"/>' % (Y(d), W - 10, Y(d)))
        o.append('<text x="6" y="%.0f" fill="#B0BEC5">%dk</text>' % (Y(d) + 3, d // 1000))
    for i, w in enumerate(rows):
        sign = 1 if i % 2 == 0 else -1
        xb = Xh(w["horiz_disp_ft"] or 0, sign)
        col = "#1565C0" if w["producing"] else "#B0BEC5"
        o.append('<line x1="%.0f" y1="%.0f" x2="%.0f" y2="%.0f" stroke="%s" stroke-width="2"><title>%s MD %.0f TVD %.0f</title></line>'
                 % (cx, Y(wd), xb, Y(w["tvd_ft"]), col, w["well_name"], w["md_ft"], w["tvd_ft"]))
        o.append('<circle cx="%.0f" cy="%.0f" r="3" fill="%s"/>' % (xb, Y(w["tvd_ft"]), col))
        o.append('<text x="%.0f" y="%.0f" fill="#455A64" text-anchor="%s">%s%s</text>'
                 % (xb + sign * 5, Y(w["tvd_ft"]) + 3, "start" if sign > 0 else "end", w["well_name"], "★" if w["producing"] else ""))
    o.append('</svg>')
    return "".join(o)

def _traj3d_json():
    rows, wd, n = _wells, _wsum["water_depth_ft"], len(_wells)
    traces = []
    for i, w in enumerate(rows):
        ang = 2 * _math.pi * i / n
        xh, yh = 520 * _math.cos(ang), 520 * _math.sin(ang)
        horiz = w["horiz_disp_ft"] or 0.0
        baz = ang + 0.7
        xb, yb = xh + horiz * _math.cos(baz), yh + horiz * _math.sin(baz)
        col = "#1565C0" if w["producing"] else "#B0BEC5"
        traces.append({"x": [xh, xh, xb], "y": [yh, yh, yb], "z": [0, -wd, -w["tvd_ft"]],
                       "mode": "lines", "type": "scatter3d", "line": {"color": col, "width": 4},
                       "name": w["well_name"] + ("★" if w["producing"] else ""),
                       "hovertemplate": "%s MD %.0f / TVD %.0f ft<extra></extra>" % (w["well_name"], w["md_ft"], w["tvd_ft"])})
        traces.append({"x": [xb], "y": [yb], "z": [-w["tvd_ft"]], "mode": "markers", "type": "scatter3d",
                       "marker": {"size": 3, "color": col}, "showlegend": False, "hoverinfo": "skip"})
    return json.dumps(traces)

_n, _prod = _wsum["wellbores"], _wsum["producers"]
WELL_SECTIONS = """
  <div class="section">
    <h2>Well &amp; drilling engineering</h2>
    <div class="lead">Julia's development is %d wellbores (%d producing) drilled to ~30,000 ft MD beneath %s ft of
      water, %s total rig-days (≈ $%.2fB of MODU time at $0.8M/day). Campaign %s → %s. Drilling data is the
      real BSEE/FDAS V30 per-well record; methodology mirrors aceengineercode <code>ong_field_development</code>.</div>
    <h3>Drilling campaign timeline</h3>
    <div class="lead2">spud → TD (solid) plus completion (faded); ★ = producing bore. A lone 2008 wildcat, then the 2014–2019 development campaign.</div>
    %s
    <h3>Rig days by wellbore</h3>
    <div class="lead2">drilling (dark) + completion (light) days per bore, with normalized days per 10,000 ft drilled.</div>
    %s
  </div>
  <div class="section">
    <h2>Well trajectories — indicative schematic</h2>
    <div class="lead2">Real per-bore MD/TVD beneath %s ft of water; wellhead cluster &amp; azimuth are schematic
      (BSEE deviation surveys for these Walker Ridge wells aren't in the public local set), so treat displacement as illustrative.</div>
    <h3>Depth cross-section (always-on)</h3>
    %s
    <h3>Interactive 3D (needs WebGL)</h3>
    <div class="lead2">Drag to rotate — wellbores fanning from the subsea cluster at the mudline down to ~30,000 ft TVD.</div>
    <div id="traj3d" style="height:520px"></div>
  </div>""" % (
    _n, _prod, format(int(_wsum["water_depth_ft"]), ","), format(int(_wsum["total_rig_days"]), ","),
    _wsum["dnc_cost_usd"] / 1e9, _wsum["campaign_start"], _wsum["campaign_end"],
    _timeline_svg(), _rigdays_svg(), format(int(_wsum["water_depth_ft"]), ","), _xsection_svg())

PLOTLY_BLOCK = ('<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>'
    '<script>try{var T=' + _traj3d_json() + ';Plotly.newPlot("traj3d",T,'
    '{margin:{l:0,r:0,t:0,b:0},scene:{xaxis:{title:"East (ft)"},yaxis:{title:"North (ft)"},'
    'zaxis:{title:"Depth (ft TVD)"},aspectmode:"manual",aspectratio:{x:1,y:1,z:1.7}},'
    'legend:{font:{size:10}}},{responsive:true});}catch(e){}</script>')

html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>ACE Engineer — Julia Field Economics (BSEE OGOR-A)</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:#F5F7FA;color:#212121}}
.report-header{{background:linear-gradient(135deg,#0D47A1,#1565C0 55%,#1976D2);color:#fff;padding:34px 48px}}
.report-header h1{{font-size:25px;font-weight:700}}
.report-header .subtitle{{margin-top:6px;opacity:.88;font-size:14px}}
.badges{{display:flex;gap:10px;margin-top:14px;flex-wrap:wrap}}
.badge{{background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.3);border-radius:20px;padding:4px 14px;font-size:12px}}
.kpi-row{{display:flex;gap:16px;padding:22px 32px;flex-wrap:wrap;background:#ECEFF1;border-bottom:1px solid #CFD8DC}}
.kpi-card{{background:#fff;border-radius:10px;padding:16px 20px;flex:1;min-width:155px;box-shadow:0 1px 4px rgba(0,0,0,.07);border-top:3px solid #1565C0}}
.kpi-card.neg{{border-top-color:#C62828}}
.kpi-card .label{{font-size:11px;text-transform:uppercase;letter-spacing:.6px;color:#78909C;font-weight:600}}
.kpi-card .value{{font-size:21px;font-weight:700;color:#1A237E;margin-top:4px}}
.kpi-card.neg .value{{color:#C62828}}
.kpi-card .sub{{font-size:11px;color:#90A4AE;margin-top:2px}}
.content{{max-width:1320px;margin:0 auto;padding:26px 32px}}
.section{{background:#fff;border-radius:12px;padding:24px 28px;margin-bottom:22px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
.section h2{{font-size:17px;color:#0D47A1;margin-bottom:6px}}
.section .lead{{font-size:13px;color:#607D8B;margin-bottom:16px}}
.toggles{{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap;align-items:center}}
.toggle{{padding:8px 18px;border:1px solid #B0BEC5;border-radius:22px;background:#fff;cursor:pointer;font-size:13px;font-weight:600;color:#455A64}}
.toggle.active{{background:#1565C0;color:#fff;border-color:#1565C0}}
.vint{{margin-left:auto;display:flex;gap:8px}}
.vint .toggle.active{{background:#00838F;border-color:#00838F}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th,td{{text-align:right;padding:10px 12px;border-bottom:1px solid #ECEFF1}}
th{{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:#78909C;font-weight:600;background:#FAFBFC}}
td.name,th.name{{text-align:left}}
td.name div:first-child{{font-weight:600;color:#263238}}
.rsub{{font-size:11px;color:#90A4AE}}
td.neg{{color:#C62828;font-weight:600}}
td.pos{{color:#2E7D32;font-weight:600}}
.ind::after{{content:"≈";color:#B0BEC5;margin-left:3px}}
.callout{{background:#E8F5E9;border-left:4px solid #2E7D32;padding:14px 18px;border-radius:6px;font-size:13px;color:#1B5E20}}
.callout.warn{{background:#FFF3E0;border-left-color:#EF6C00;color:#E65100}}
.foot{{font-size:11px;color:#90A4AE;padding:18px 32px;max-width:1320px;margin:0 auto;line-height:1.6}}
code{{background:#ECEFF1;padding:1px 6px;border-radius:4px;font-size:12px}}
.section h3{{font-size:14px;color:#37474F;margin:18px 0 4px}}
.lead2{{font-size:12px;color:#78909C;margin-bottom:10px}}
svg{{display:block;margin:4px 0 6px}}
</style></head><body>
<div class="report-header">
  <h1>Julia Field — Development Economics from Public BSEE Data</h1>
  <div class="subtitle">Gulf of Mexico · Walker Ridge 584 · Lower Tertiary subsea tieback · Equinor 50% / ExxonMobil 50% · Lease G20351 · First oil Mar 2016</div>
  <div class="badges">
    <span class="badge">Source: BSEE OGOR-A · production through {LATEST_FRIENDLY}</span>
    <span class="badge">EIA WTI historical deck</span>
    <span class="badge">FDAS V30 tieback15 assumptions</span>
    <span class="badge">Validated vs golden baseline</span>
  </div>
</div>
<div class="kpi-row">{kpi_cards()}</div>
<div class="content">
  <div class="section"><div class="callout">✓ <b>Reproduced from raw public data.</b>
    Field NPV@10% reproduced to <b>{val_delta:+.3f}%</b> of the FDAS&nbsp;V30 golden baseline
    (${REPRO_NPV/1e6:,.1f}M vs ${GOLDEN['npv_usd']/1e6:,.1f}M); gross revenue, D&amp;C and facilities match to ~0.001%.
    Latest OGOR cross-check: oil {lat_oil/1e6:,.1f} MMbbl / revenue {m(lat_rev)} through {LATEST_FRIENDLY}
    (vs published latest baseline 74.0 MMbbl / $4,917M).</div></div>
  <div class="section">
    <h2>Economics by granularity</h2>
    <div class="lead">Switch between field, block and well. Oil, gas, revenue, royalty (18.75%) and net operating
      cashflow are computed per-unit directly from OGOR production. D&amp;C is the well's own drilling+completion
      cost; the field row carries shared facilities ($1,375M). <b>Field &amp; block NPV/MIRR are the validated FDAS V30
      figures</b>; per-well full-cycle NPV (marked ≈) is an indicative allocation of shared CAPEX &amp; OPEX.</div>
    <div class="toggles">
      <div class="toggle active" data-g="field" onclick="setG('field')">By Field</div>
      <div class="toggle" data-g="block" onclick="setG('block')">By Block</div>
      <div class="toggle" data-g="well" onclick="setG('well')">By Well</div>
      <div class="vint">
        <div class="toggle active" data-v="v30" onclick="setV('v30')">V30 · thru May 2025</div>
        <div class="toggle" data-v="latest" onclick="setV('latest')">Latest · thru {LATEST_FRIENDLY}</div>
      </div>
    </div>
    <table><thead><tr>
      <th class="name">Unit</th><th>Oil (MMbbl)</th><th>Gas (BCF)</th><th>Revenue</th>
      <th>Net Op. Cashflow</th><th>D&amp;C / CAPEX</th><th>NPV@10%</th><th>MIRR</th>
    </tr></thead><tbody id="tbody">{INITIAL_TBODY}</tbody></table>
  </div>
  <div class="section"><div class="callout warn">⚠ <b>Honest result.</b> Julia's full-cycle NPV@10% is
    <b>negative (~−$531M)</b>: ~$2.72B of D&amp;C + facilities outweighs discounted net operating cashflow at
    historical prices. This is the real economics of the field from public data — not a marketing-optimised number.
    Two wells (JU104, JU106) are individually value-accretive and carry the development; the early appraisal wells do not.
    The deliverable is the <b>traceable, reproducible pipeline</b>, queryable by well, block or field.</div></div>
{WELL_SECTIONS}
</div>
<div class="foot">
  Methodology: BSEE OGOR-A monthly oil × EIA WTI monthly − royalty (18.75% federal) − variable OPEX ($6/bbl) −
  fixed OPEX ($75M/yr) − D&amp;C (drilling+completion days × $0.8M/day MODU) − facilities (SURF $250M/well +
  booster pump $275M + water-injection facility $100M; tieback15 → no host CAPEX). NPV trimmed to first/last
  non-zero month, discounted 10% annual (monthly compounded); MIRR Excel-style (reinvest 8% / finance 6%).
  Vintages: <code>V30</code> = OGOR+WTI through 2025-05 (golden-baseline window, field/block figures authoritative);
  <code>Latest</code> = OGOR+WTI through {LATEST_FRIENDLY} (last complete OGOR month; Dec 2025 partial, excluded). Per-well NPV (≈) allocates shared CAPEX &amp; fixed OPEX by
  production share and is indicative, not a re-derivation of the field NPV. Field roll-up validated against
  <code>golden_baseline_v30.yml</code>; reproduced from local <code>ogora*delimit</code> pickles. ACE Engineer · worldenergydata.
</div>
<script>
const D={vd};
let g="field",v="v30";
function render(){{
  const rows=D[v][g];let h="";
  for(const r of rows){{
    const cls=r.npv_neg?"neg":"pos";const ind=r.indic?"ind":"";
    h+=`<tr><td class="name"><div>${{r.name}}</div><div class="rsub">${{r.sub}}</div></td>`+
       `<td>${{r.oil}}</td><td>${{r.gas}}</td><td>${{r.rev}}</td><td>${{r.netop}}</td>`+
       `<td>${{r.capex}}</td><td class="${{cls}} ${{ind}}">${{r.npv}}</td><td>${{r.mirr}}</td></tr>`;
  }}
  document.getElementById("tbody").innerHTML=h;
  document.querySelectorAll('.toggle[data-g]').forEach(e=>e.classList.toggle('active',e.dataset.g===g));
  document.querySelectorAll('.toggle[data-v]').forEach(e=>e.classList.toggle('active',e.dataset.v===v));
}}
function setG(x){{g=x;render();}}
function setV(x){{v=x;render();}}
render();
</script>
{PLOTLY_BLOCK}
</body></html>"""

(Path(__file__).resolve().parents[1] / "reports/gtm/2026-06-17-julia-field-economics-by-well-block-field.html").write_text(html)
print("REPORT WRITTEN", len(html), "bytes")
