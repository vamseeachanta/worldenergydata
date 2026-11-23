#!/usr/bin/env python3
"""ABOUTME: Generate the Well Pressure Atlas browse page from the committed _pressure.json.
ABOUTME: One axis, two ends — offshore GoM Wilcox over-pressure vs onshore Mid-Continent under-pressure.

Reads the sibling reports/pressure-atlas/_pressure.json and writes a single self-contained
index.html (inline <style> + inline <script>, no external assets, no CDN). Every rendered
number traces to the data file; null / missing values render "—", never borrowed. Mirrors the
navy/teal aesthetic of reports/field-atlas and the click-to-sort <th> idiom of
reports/field_development/bsee_matched, with keyboard-operable, aria-sorted tables.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[2] / "reports/pressure-atlas"
DATA = HERE / "_pressure.json"

TIER_LABEL = {
    "severely_underpressured": "severe",
    "mildly_underpressured": "mild",
    "normal": "normal",
}
TIER_CLASS = {
    "severely_underpressured": "t-severe",
    "mildly_underpressured": "t-mild",
    "normal": "t-normal",
}


def esc(x) -> str:
    return html.escape(str(x), quote=True)


def comma(n) -> str:
    return f"{n:,}"


def fmt_int(v):
    """Integer with thousands separators, or an em-dash for null."""
    if v is None:
        return "—", "-1"
    return comma(int(v)), str(int(v))


def fmt_pressure(psi, qual):
    """Render reservoir pressure with its honesty qualifier (~ / ≥ / up to)."""
    if psi is None:
        return "—", "-1"
    val = comma(int(psi))
    q = (qual or "").strip()
    if q == "up to":
        return f"up to {val}", str(int(psi))
    if q in ("~", "≥"):
        return f"{q}{val}", str(int(psi))
    return val, str(int(psi))


def offshore_rows(fields) -> str:
    out = []
    for i, f in enumerate(fields):
        wd, wd_s = fmt_int(f.get("water_depth_ft"))
        pr, pr_s = fmt_pressure(f.get("pressure_psi"), f.get("pressure_qual"))
        eq, eq_s = fmt_int(f.get("equip_rating_psi"))
        tp, tp_s = fmt_int(f.get("temp_f"))
        tv, tv_s = fmt_int(f.get("tvd_ft"))
        hpht = f.get("hpht_class") or "—"
        hpht_class = ""
        if f.get("hpht_class") == "ultra-HPHT":
            hpht_class = " class='hpht-ultra'"
        elif f.get("hpht_class") == "HPHT":
            hpht_class = " class='hpht'"
        # undisclosed pressure = neutral "—", not an alarming red value
        pr_cls = "num nodata" if f.get("pressure_psi") is None else "num pr"
        cav = ""
        if f.get("pressure_caveat"):
            cav = "<sup class='cav' title='see source note'>&dagger;</sup>"
        note = esc(f.get("source_note", ""))
        name = esc(f["name"])
        out.append(
            f"<tr class='off-row' data-i='{i}'>"
            f"<td class='fld'><button class='disc' aria-label='show source note for {name}' "
            f"aria-expanded='false' title='Click for source'>&#9432;</button>{name}</td>"
            f"<td>{esc(f.get('operator') or '—')}</td>"
            f"<td data-sort='{wd_s}' class='num'>{wd}</td>"
            f"<td data-sort='{pr_s}' class='{pr_cls}'>{pr}{cav}</td>"
            f"<td data-sort='{eq_s}' class='num'>{eq}</td>"
            f"<td data-sort='{tp_s}' class='num'>{tp}</td>"
            f"<td data-sort='{tv_s}' class='num'>{tv}</td>"
            f"<td{hpht_class}>{esc(hpht)}</td>"
            f"</tr>"
            f"<tr class='note-row' data-for='{i}' hidden><td colspan='8'>"
            f"<div class='src'><b>{name} &mdash; source:</b> {note}</div></td></tr>"
        )
    return "\n".join(out)


def onshore_rows(fields) -> str:
    out = []
    for f in fields:
        tier = f.get("field_tier", "")
        tcls = TIER_CLASS.get(tier, "")
        tlbl = TIER_LABEL.get(tier, tier)
        grad = f.get("median_gradient_psi_ft")
        grad_s = f"{grad:.4f}" if grad is not None else "—"
        grad_sort = grad if grad is not None else -1
        pct = f.get("pct_hydrostatic")
        pct_s = f"{pct:.1f}%" if pct is not None else "—"
        pct_sort = str(pct) if pct is not None else "-1"
        wells, wells_s = fmt_int(f.get("well_count"))
        nv = f.get("near_vacuum_wells")
        nv_disp = comma(int(nv)) if nv is not None else "—"
        nv_sort = nv if nv is not None else -1
        nv_flag = ""
        if (nv or 0) > 0:
            nv_flag = (
                " <span class='vac' title='near-vacuum wells present'>&#9888;</span>"
            )
        yr = f.get("earliest_test_year")
        yr_s = str(yr) if yr is not None else "—"
        yr_sort = yr if yr is not None else -1
        out.append(
            f"<tr>"
            f"<td class='fld'>{esc(f.get('field') or '—')}</td>"
            f"<td>{esc(f.get('states') or '—')}</td>"
            f"<td data-sort='{wells_s}' class='num'>{wells}</td>"
            f"<td data-sort='{grad_sort}' class='num'>{grad_s}</td>"
            f"<td data-sort='{pct_sort}' class='num'>{pct_s}</td>"
            f"<td data-sort='{nv_sort}' class='num'>{nv_disp}{nv_flag}</td>"
            f"<td data-sort='{yr_sort}' class='num'>{yr_s}</td>"
            f"<td data-sort='{tier}'><span class='tier {tcls}'>{esc(tlbl)}</span></td>"
            f"</tr>"
        )
    return "\n".join(out)


def build() -> str:
    d = json.loads(DATA.read_text())
    off = d["offshore"]
    on = d["onshore"]
    sc = on["state_counts"]
    href = d.get("hydrostatic_ref_psi_ft", 0.433)

    # ---- stat tiles (all trace to the data file) ----
    disclosed = [
        f["pressure_psi"] for f in off["fields"] if f.get("pressure_psi") is not None
    ]
    off_max = max(disclosed) if disclosed else None
    off_max_obj = next(
        (f for f in off["fields"] if f.get("pressure_psi") == off_max), None
    )
    off_max_field = off_max_obj["name"] if off_max_obj else "—"
    off_max_disp = "—"
    if off_max_obj is not None:
        off_max_disp, _ = fmt_pressure(off_max, off_max_obj.get("pressure_qual"))
    off_disclosed_count = len(disclosed)

    tiles = [
        (
            "Offshore max disclosed",
            f"{off_max_disp} psi" if off_max else "—",
            f"{esc(off_max_field)} (reservoir BHP)",
        ),
        (
            "Onshore wells screened",
            comma(on["wells_screened"]),
            f"{comma(sc['OK'])} OK · {comma(sc['KS'])} KS · {comma(sc['TX'])} TX",
        ),
        (
            "Onshore median",
            f"{on['median_pct_hydrostatic']:.1f}%",
            f"of hydrostatic · {on['median_gradient_psi_ft']:.4f} psi/ft",
        ),
        (
            "Near-vacuum wells",
            comma(on["near_vacuum_wells"]),
            "onshore, at extreme-low BHP",
        ),
    ]
    tiles_html = "\n".join(
        f"<div class='card'><div class='k'>{esc(k)}</div>"
        f"<div class='v'>{v}</div><div class='s'>{esc(s)}</div></div>"
        for k, v, s in tiles
    )

    # ---- onshore state chips + aggregate line ----
    chips = "".join(
        f"<span class='chip'><b>{st}</b> {comma(n)} wells</span>"
        for st, n in sorted(sc.items(), key=lambda kv: -kv[1])
    )
    tc = on["tier_counts"]
    agg = (
        f"Onshore aggregate: <b>{comma(on['wells_screened'])}</b> wells · median BHP gradient "
        f"<b>{on['median_gradient_psi_ft']:.4f} psi/ft</b> "
        f"(&asymp;{on['median_pct_hydrostatic']:.1f}% of hydrostatic) · "
        f"<span class='tier t-severe'>severe</span> {comma(tc['severely_underpressured'])} · "
        f"<span class='tier t-mild'>mild</span> {comma(tc['mildly_underpressured'])} · "
        f"<span class='tier t-normal'>normal</span> {comma(tc['normal'])} · "
        f"<b>{comma(on['near_vacuum_wells'])}</b> near-vacuum · "
        f"{comma(on['fields_ranked'])} fields ranked"
    )

    roadmap = "".join(
        f"<span class='rm'>{esc(r['label'])}</span>"
        for r in d.get("roadmap_regions", [])
    )

    # ---- caveat footnote (e.g. Julia subsea system pressure) ----
    caveats = [f for f in off["fields"] if f.get("pressure_caveat")]
    off_foot = ""
    if caveats:
        items = "; ".join(
            f"{esc(f['name'])} &mdash; {esc(f['pressure_caveat'])}" for f in caveats
        )
        off_foot = f"<p class='foot-note'>&dagger; {items}</p>"

    return TEMPLATE.format(
        title=esc(d["title"]),
        subtitle=esc(d["subtitle"]),
        off_label=esc(off["label"]),
        off_regime=esc(off["regime"]),
        off_play=esc(off["play"]),
        off_count=off["field_count"],
        off_disclosed=off_disclosed_count,
        off_source=esc(off["source"]),
        off_foot=off_foot,
        on_label=esc(on["label"]),
        on_regime=esc(on["regime"]),
        on_source=esc(on["source"]),
        tiles=tiles_html,
        chips=chips,
        agg=agg,
        roadmap=roadmap,
        off_tbody=offshore_rows(off["fields"]),
        on_tbody=onshore_rows(on["top_fields"]),
        on_shown=len(on["top_fields"]),
        fields_ranked=comma(on["fields_ranked"]),
        href=href,
    )


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — worldenergydata</title>
<style>
  :root{{--navy:#0B3D91;--teal:#0f8a7e;--bg:#eef3fa;--panel:#fff;--ink:#13233f;--muted:#5b6b86;
        --line:#dbe4f0;--soft:#f4f8fc;--severe:#c0392b;--mild:#8a5a12;--normal:#177544;--roadmap:#5b6b86}}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:-apple-system,"Segoe UI",Roboto,Arial,sans-serif;background:var(--bg);color:var(--ink);line-height:1.5}}
  a{{color:inherit;text-decoration:none}}
  .wrap{{max-width:1180px;margin:0 auto;padding:26px 22px 80px}}
  .nav{{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:16px;font-family:ui-monospace,monospace;font-size:12.5px}}
  .nav a{{color:var(--teal);font-weight:700}}
  .nav a:hover{{text-decoration:underline}}
  .eyebrow{{font-family:ui-monospace,monospace;font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}}
  h1{{font-size:30px;font-weight:800;letter-spacing:-.4px;color:var(--navy);margin:6px 0 8px}}
  h2.sec{{font-size:19px;font-weight:800;color:var(--navy);letter-spacing:-.2px;margin:20px 0 2px}}
  .lede{{color:var(--muted);font-size:16px;max-width:820px}}
  .story{{display:block;margin-top:14px;background:#fff;border:1px solid var(--line);border-left:4px solid var(--teal);
         border-radius:10px;padding:12px 16px;font-size:14px;max-width:900px}}
  .story b{{color:var(--navy)}}
  .story .over{{color:var(--severe);font-weight:700}}
  .story .under{{color:var(--teal);font-weight:700}}
  .cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin:24px 0 8px}}
  .card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:13px 16px;
        box-shadow:0 1px 2px rgba(16,40,80,.04)}}
  .card .k{{font-family:ui-monospace,monospace;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}}
  .card .v{{font-size:26px;font-weight:800;color:var(--navy);margin:2px 0 1px;letter-spacing:-.5px}}
  .card .s{{font-size:12px;color:var(--muted)}}
  .toggle{{display:inline-flex;gap:4px;margin:22px 0 4px;background:#fff;border:1px solid var(--line);border-radius:24px;padding:4px}}
  .toggle button{{font-family:ui-monospace,monospace;font-size:13px;font-weight:700;padding:8px 18px;border:0;border-radius:20px;background:transparent;color:var(--muted);cursor:pointer}}
  .toggle button.on{{background:var(--navy);color:#fff}}
  .toggle button:focus-visible{{outline:2px solid var(--teal);outline-offset:2px}}
  .view{{display:none}}
  .view.on{{display:block}}
  .ctx{{font-size:13.5px;color:var(--muted);margin:6px 2px 6px;max-width:900px}}
  .ctx b{{color:var(--ink)}}
  .chips{{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 4px}}
  .chip{{font-family:ui-monospace,monospace;font-size:12.5px;color:var(--muted);background:#fff;border:1px solid var(--line);border-radius:20px;padding:5px 12px}}
  .chip b{{color:var(--navy)}}
  .agg{{font-size:13px;color:var(--muted);background:var(--soft);border:1px solid var(--line);border-radius:10px;padding:10px 14px;margin:10px 0;line-height:1.9}}
  .agg b{{color:var(--ink)}}
  .tblwrap{{overflow-x:auto;border:1px solid var(--line);border-radius:12px;margin-top:8px;background:#fff}}
  table{{border-collapse:collapse;width:100%;font-size:13px;min-width:640px}}
  th,td{{border-bottom:1px solid var(--line);padding:9px 12px;text-align:left;white-space:nowrap}}
  th{{background:var(--soft);cursor:pointer;user-select:none;font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);position:sticky;top:0}}
  th:hover{{background:#e7eef7}}
  th:focus-visible{{outline:2px solid var(--teal);outline-offset:-2px}}
  th::after{{content:"\2195";opacity:.35;font-size:10px;margin-left:5px}}
  th[aria-sort="ascending"]::after{{content:"\2191";opacity:.9}}
  th[aria-sort="descending"]::after{{content:"\2193";opacity:.9}}
  td.num{{text-align:right;font-variant-numeric:tabular-nums}}
  td.fld{{font-weight:700;color:var(--ink)}}
  td.pr{{font-weight:700;color:var(--severe)}}
  td.nodata{{text-align:right;color:var(--muted)}}
  tbody tr:hover{{background:var(--soft)}}
  .hpht{{color:var(--mild);font-weight:700}}
  .hpht-ultra{{color:var(--severe);font-weight:700}}
  .cav{{color:var(--teal);font-weight:700;font-size:10px}}
  .disc{{border:0;background:transparent;color:var(--teal);cursor:pointer;font-size:15px;margin-right:6px;padding:0;vertical-align:-1px}}
  .disc:focus-visible{{outline:2px solid var(--teal);outline-offset:2px;border-radius:3px}}
  .note-row td{{background:var(--soft);white-space:normal}}
  .src{{font-size:12.5px;color:var(--muted);line-height:1.5;padding:2px 0}}
  .src b{{color:var(--navy)}}
  .tier{{font-family:ui-monospace,monospace;font-size:11px;font-weight:700;text-transform:uppercase;padding:3px 9px;border-radius:20px;white-space:nowrap}}
  .t-severe{{color:#fff;background:var(--severe)}}
  .t-mild{{color:#fff;background:var(--mild)}}
  .t-normal{{color:#fff;background:var(--normal)}}
  .vac{{color:var(--severe);margin-left:4px}}
  .roadmap{{margin-top:26px}}
  .rm{{display:inline-block;font-family:ui-monospace,monospace;font-size:12px;color:var(--roadmap);background:#f2f5f9;border:1px dashed var(--line);border-radius:20px;padding:5px 12px;margin:0 6px 6px 0}}
  .foot-note{{font-size:12px;color:var(--muted);margin-top:8px;max-width:900px;line-height:1.5}}
  .note{{margin-top:12px;font-size:12.5px;color:var(--muted);background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 18px;line-height:1.6;max-width:960px}}
  .note b{{color:var(--navy)}}
  @media (prefers-color-scheme:dark){{
    :root{{--bg:#0a141f;--panel:#10202f;--ink:#e8eef4;--muted:#8ca0b3;--line:#24384b;--soft:#0d1b28;--navy:#5b9de0;--teal:#3fb99b;--severe:#e5705f;--mild:#d9a441;--normal:#3fc07a;--roadmap:#8ca0b3}}
    .rm{{background:#182636}}
    .card .v{{color:var(--ink)}}
    td.pr{{color:var(--severe)}}
    .t-severe,.t-mild,.t-normal{{color:#08131f}}
  }}
</style>
</head>
<body>
<div class="wrap">
  <nav class="nav" aria-label="site">
    <a href="../">&larr; worldenergydata</a>
    <a href="../field-atlas/">Field atlas</a>
    <a href="../capabilities/">Capabilities</a>
  </nav>
  <p class="eyebrow">worldenergydata · browse the pressure spectrum</p>
  <h1>{title}</h1>
  <p class="lede">{subtitle}</p>
  <div class="story">One axis, two extremes. Offshore Gulf of Mexico Wilcox is
     <span class="over">extreme over-pressure</span> &mdash; ultra-HPHT reservoirs to
     <b>~25,000 psi</b> (Anchor; 23,000&ndash;27,000 psi disclosed). Onshore Mid-Continent gas
     is <span class="under">extreme under-pressure</span> &mdash; a median of
     <b>~9% of hydrostatic</b> with hundreds of near-vacuum wells. Same subsurface, opposite
     ends of one pressure axis.</div>

  <div class="cards">
{tiles}
  </div>

  <div class="toggle" id="tog" role="tablist" aria-label="pressure regime">
    <button data-v="off" class="on" role="tab" aria-selected="true" aria-controls="view-off">Offshore &mdash; over-pressure</button>
    <button data-v="on" role="tab" aria-selected="false" aria-controls="view-on">Onshore &mdash; under-pressure</button>
  </div>

  <section class="view on" id="view-off" role="tabpanel" aria-label="Offshore">
    <h2 class="sec">{off_label}</h2>
    <p class="ctx">{off_regime} · {off_play}. {off_count} Lower-Tertiary fields;
       <b>{off_disclosed}</b> with a publicly disclosed reservoir pressure. Click the &#9432; on any
       row for the exact source. Fields with no published pore pressure show &mdash; (never a
       borrowed neighbour value).</p>
    <div class="tblwrap">
      <table id="t-off">
        <thead><tr>
          <th>Field</th><th>Operator</th><th>Water depth (ft)</th>
          <th>Reservoir pressure (psi)</th><th>Equip rating (psi)</th>
          <th>Temp (&deg;F)</th><th>TVD (ft)</th><th>HPHT class</th>
        </tr></thead>
        <tbody>
{off_tbody}
        </tbody>
      </table>
    </div>
    {off_foot}
    <p class="ctx" style="font-size:12px">Source: {off_source}</p>
  </section>

  <section class="view" id="view-on" role="tabpanel" aria-label="Onshore">
    <h2 class="sec">{on_label}</h2>
    <p class="ctx">{on_regime}. Top {on_shown} fields by well count (of {fields_ranked} ranked).
       Tier is coloured by field: <span class="tier t-severe">severe</span>
       <span class="tier t-mild">mild</span> <span class="tier t-normal">normal</span>; &#9888;
       flags fields containing near-vacuum wells.</p>
    <div class="chips">{chips}</div>
    <div class="agg">{agg}</div>
    <div class="tblwrap">
      <table id="t-on">
        <thead><tr>
          <th>Field</th><th>State(s)</th><th>Wells</th>
          <th>Median BHP grad (psi/ft)</th><th>% hydrostatic</th>
          <th>Near-vacuum</th><th>Earliest test yr</th><th>Tier</th>
        </tr></thead>
        <tbody>
{on_tbody}
        </tbody>
      </table>
    </div>
    <p class="ctx" style="font-size:12px">Source: {on_source}</p>
  </section>

  <h2 class="sec roadmap">Roadmap &mdash; not yet screened</h2>
  <div>{roadmap}</div>

  <h2 class="sec">Methodology</h2>
  <div class="note"><b>Offshore</b> figures are public field disclosures
     (OGJ, OTC/JPT, OffshoreMag, operator releases) &mdash; disclosed reservoir (pore/BHP)
     pressures, distinct from the wellhead equipment rating; undisclosed values render &mdash;.
     <b>Onshore</b> figures come from state well databases (Kansas KGS, Oklahoma OCC, Texas RRC)
     screened by the worldenergydata <i>underpressured_screen</i> BHP gas-column estimate. Onshore
     is a <b>depleted-era proxy</b> &mdash; it measures economic operability at extreme-low bottomhole
     pressure in mature gas areas, <b>not</b> virgin sub-hydrostatic reservoirs. Hydrostatic
     reference: <b>{href} psi/ft</b>. Every number on this page traces to the committed
     <code>_pressure.json</code>.</div>
</div>

<script>
// Segmented toggle: offshore (default) / onshore
document.getElementById('tog').addEventListener('click', function(e){{
  var b = e.target.closest('button'); if(!b) return;
  var v = b.dataset.v;
  [].forEach.call(this.children, function(x){{
    var on = x===b;
    x.classList.toggle('on', on);
    x.setAttribute('aria-selected', on?'true':'false');
  }});
  document.getElementById('view-off').classList.toggle('on', v==='off');
  document.getElementById('view-on').classList.toggle('on', v==='on');
}});

// Offshore: reveal that field's source note row; keep aria-expanded in sync
document.querySelectorAll('#t-off .disc').forEach(function(btn){{
  btn.addEventListener('click', function(e){{
    e.stopPropagation();
    var tr = btn.closest('tr'); var i = tr.dataset.i;
    var note = document.querySelector('#t-off .note-row[data-for="'+i+'"]');
    if(note){{ note.hidden = !note.hidden; btn.setAttribute('aria-expanded', note.hidden?'false':'true'); }}
  }});
}});

// Click- or keyboard-to-sort headers (numeric-aware; ignores paired note rows; announces via aria-sort)
document.querySelectorAll('table').forEach(function(table){{
  var ths = table.querySelectorAll('th');
  ths.forEach(function(th,i){{
    th.tabIndex = 0;
    th.setAttribute('role','button');
    function doSort(){{
      var tb = table.tBodies[0];
      var all = [].slice.call(tb.rows);
      var rows = all.filter(function(r){{ return !r.classList.contains('note-row'); }});
      var notes = {{}};
      all.forEach(function(r){{ if(r.classList.contains('note-row')) notes[r.dataset.for]=r; }});
      var asc = th.dataset.asc!=='1'; th.dataset.asc = asc?'1':'0';
      ths.forEach(function(o){{ if(o!==th){{ o.removeAttribute('aria-sort'); o.dataset.asc=''; }} }});
      th.setAttribute('aria-sort', asc?'ascending':'descending');
      rows.sort(function(a,b){{
        var x=a.cells[i].dataset.sort!==undefined?a.cells[i].dataset.sort:a.cells[i].innerText;
        var y=b.cells[i].dataset.sort!==undefined?b.cells[i].dataset.sort:b.cells[i].innerText;
        var nx=parseFloat(x), ny=parseFloat(y);
        if(!isNaN(nx)&&!isNaN(ny)){{x=nx;y=ny;}}
        return (x>y?1:x<y?-1:0)*(asc?1:-1);
      }});
      rows.forEach(function(r){{
        tb.appendChild(r);
        if(r.dataset.i!==undefined && notes[r.dataset.i]) tb.appendChild(notes[r.dataset.i]);
      }});
    }}
    th.addEventListener('click', doSort);
    th.addEventListener('keydown', function(e){{
      if(e.key==='Enter'||e.key===' '){{ e.preventDefault(); doSort(); }}
    }});
  }});
}});
</script>
</body>
</html>
"""


def main():
    HERE.mkdir(parents=True, exist_ok=True)
    out = HERE / "index.html"
    out.write_text(build())
    d = json.loads(DATA.read_text())
    n_off = len(d["offshore"]["fields"])
    n_on = len(d["onshore"]["top_fields"])
    print(f"  wrote {out}")
    print(f"  offshore fields: {n_off}  onshore top_fields: {n_on}")


if __name__ == "__main__":
    main()
