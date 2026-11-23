#!/usr/bin/env python3
"""Build a single self-contained, tabbed HTML portfolio report from the
per-field markdown economics reports.

- A "Portfolio" tab: all producing fields compared (latest vs frozen-V30 NPV,
  delta, revenue, oil) + a ranked bar chart + portfolio totals.
- One tab per field: that field's full report, with a Latest / Frozen-V30
  sub-toggle. Content is server-rendered into the DOM (visible without JS);
  JavaScript only switches which tab/variant is shown.

Reuses the already-generated markdown reports (no model recompute).

Usage:
    uv run --with markdown python scripts/lower_tertiary/build_portfolio_html.py
"""

from __future__ import annotations

import re
from pathlib import Path

import markdown as md

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports" / "lower_tertiary"
OUT = REPORTS / "portfolio_economics.html"

# Display order: least-negative (best) NPV first is applied after parsing.
FIELDS = [
    "Julia",
    "Jack St Malo",
    "Big Foot",
    "Shenandoah",
    "Stones",
    "Cascade Chinook",
    "Anchor",
]

_NPV_RE = re.compile(r"Terminal cumulative NPV = \*\*\$([-\d,.]+) M\*\*")
_REV_RE = re.compile(r"\|\s*Revenue\s*\|\s*\$([-\d,.]+) M\s*\|")
_OIL_RE = re.compile(r"\|\s*Oil produced \(MMbbl\)\s*\|\s*([-\d,.]+)\s*\|")
_LEASE_RE = re.compile(r"\*\*Lease:\*\*\s*([^&·\n]+)")


def _slug(name: str) -> str:
    return name.lower().replace(" ", "_").replace("/", "_")


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _to_html(md_text: str) -> str:
    return md.markdown(
        md_text,
        extensions=["tables", "fenced_code", "sane_lists", "nl2br"],
    )


def _lease_count(text: str) -> str:
    m = _LEASE_RE.search(text)
    if not m:
        return "—"
    lab = m.group(1).strip()
    cm = re.match(r"(\d+) leases", lab)
    return cm.group(1) if cm else "1"


def main() -> None:
    rows = []
    for field in FIELDS:
        slug = _slug(field)
        latest_md = _read(REPORTS / f"field_economics_{slug}.md")
        frozen_md = _read(REPORTS / f"field_economics_{slug}_v30.md")
        if not latest_md:
            continue
        npv_l = _NPV_RE.search(latest_md)
        npv_f = _NPV_RE.search(frozen_md)
        rev = _REV_RE.search(latest_md)
        oil = _OIL_RE.search(latest_md)
        rows.append(
            {
                "field": field,
                "slug": slug,
                "leases": _lease_count(latest_md),
                "npv_latest": _num(npv_l.group(1)) if npv_l else None,
                "npv_frozen": _num(npv_f.group(1)) if npv_f else None,
                "revenue": _num(rev.group(1)) if rev else None,
                "oil": _num(oil.group(1)) if oil else None,
                "html_latest": _to_html(latest_md),
                "html_frozen": _to_html(frozen_md) if frozen_md else "",
            }
        )

    # Rank by latest NPV (least-negative first).
    rows.sort(key=lambda r: (r["npv_latest"] is None, -(r["npv_latest"] or -9e9)))

    tot_l = sum(r["npv_latest"] for r in rows if r["npv_latest"] is not None)
    tot_f = sum(r["npv_frozen"] for r in rows if r["npv_frozen"] is not None)

    # ---- Portfolio comparison table ----
    body = []
    body.append("<table class='cmp'><thead><tr>"
                "<th>Field</th><th>Leases</th>"
                "<th class='num'>NPV latest ($MM)</th>"
                "<th class='num'>NPV frozen V30 ($MM)</th>"
                "<th class='num'>&Delta; ($MM)</th>"
                "<th class='num'>Revenue ($MM)</th>"
                "<th class='num'>Oil (MMbbl)</th></tr></thead><tbody>")
    for r in rows:
        delta = (
            r["npv_latest"] - r["npv_frozen"]
            if r["npv_latest"] is not None and r["npv_frozen"] is not None
            else None
        )
        dcls = "pos" if (delta or 0) >= 0 else "neg"
        body.append(
            f"<tr><td><a href='#' onclick=\"showTab('{r['slug']}');return false\">"
            f"{r['field']}</a></td>"
            f"<td class='num'>{r['leases']}</td>"
            f"<td class='num neg'>{r['npv_latest']:,.1f}</td>"
            f"<td class='num neg'>{r['npv_frozen']:,.1f}</td>"
            f"<td class='num {dcls}'>{delta:+,.1f}</td>"
            f"<td class='num'>{r['revenue']:,.1f}</td>"
            f"<td class='num'>{r['oil']:,.1f}</td></tr>"
        )
    body.append(
        f"<tr class='tot'><td>Producing portfolio</td><td class='num'>—</td>"
        f"<td class='num neg'>{tot_l:,.1f}</td>"
        f"<td class='num neg'>{tot_f:,.1f}</td>"
        f"<td class='num pos'>{tot_l - tot_f:+,.1f}</td>"
        f"<td class='num'></td><td class='num'></td></tr>"
    )
    body.append("</tbody></table>")

    # ---- Ranked NPV bar chart (latest), all negative ----
    max_abs = max((abs(r["npv_latest"]) for r in rows if r["npv_latest"]), default=1)
    bars = ["<div class='chart'>"]
    for r in rows:
        v = r["npv_latest"] or 0
        pct = abs(v) / max_abs * 100
        bars.append(
            f"<div class='barrow'><span class='blabel'>{r['field']}</span>"
            f"<span class='bar'><span class='fill' style='width:{pct:.1f}%'></span></span>"
            f"<span class='bval'>${v:,.0f}M</span></div>"
        )
    bars.append("</div>")

    portfolio_html = (
        "<h2>Lower Tertiary (Wilcox) &mdash; Producing Field Portfolio</h2>"
        f"<p class='lede'>{len(rows)} producing fields, full-cycle NPV @ 10% from "
        "public BSEE data. Latest window through 2026-04; frozen V30 shown for "
        "reference. Click a field name to open its tab.</p>"
        f"<p class='totals'>Portfolio NPV (latest): <b class='neg'>${tot_l:,.0f}M</b> "
        f"&middot; frozen V30: <b class='neg'>${tot_f:,.0f}M</b> "
        f"&middot; latest vs V30: <b class='pos'>+${tot_l - tot_f:,.0f}M</b></p>"
        + "".join(body)
        + "<h3>Latest NPV by field (ranked)</h3>"
        + "".join(bars)
        + "<p class='note'>Every field is NPV-negative at these public-data "
        "assumptions &mdash; the Wilcox play is capital-heavy. The latest window "
        "lifts NPV almost everywhere (more production past the capex phase); "
        "Cascade Chinook is the lone field where latest is slightly worse.</p>"
    )

    # ---- Tab bar ----
    tabs = ["<button class='tab active' data-tab='portfolio' "
            "onclick=\"showTab('portfolio')\">Portfolio</button>"]
    for r in rows:
        tabs.append(
            f"<button class='tab' data-tab='{r['slug']}' "
            f"onclick=\"showTab('{r['slug']}')\">{r['field']}</button>"
        )

    # ---- Tab panels ----
    panels = [f"<section id='tab-portfolio' class='panel active'>{portfolio_html}</section>"]
    for r in rows:
        frozen_block = (
            f"<div class='variant' id='var-{r['slug']}-frozen' style='display:none'>"
            f"{r['html_frozen']}</div>"
            if r["html_frozen"]
            else ""
        )
        toggle = (
            f"<div class='vtoggle'>"
            f"<button class='vt active' onclick=\"showVar('{r['slug']}','latest',this)\">Latest (2026-04)</button>"
            f"<button class='vt' onclick=\"showVar('{r['slug']}','frozen',this)\">Frozen V30</button>"
            f"</div>"
            if r["html_frozen"]
            else ""
        )
        panels.append(
            f"<section id='tab-{r['slug']}' class='panel'>{toggle}"
            f"<div class='variant' id='var-{r['slug']}-latest'>{r['html_latest']}</div>"
            f"{frozen_block}</section>"
        )

    html = _TEMPLATE.format(
        tabbar="".join(tabs),
        panels="".join(panels),
    )
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT}  ({len(rows)} fields, {OUT.stat().st_size // 1024} KB)")


_TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lower Tertiary Field Economics &mdash; Portfolio</title>
<style>
:root{{--ink:#1a2230;--mut:#5b6675;--line:#e1e6ec;--accent:#1f6feb;--neg:#c0392b;--pos:#1e8e4e;--bg:#f7f9fc}}
*{{box-sizing:border-box}}
body{{margin:0;font:15px/1.55 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:var(--bg)}}
header{{background:#0f2033;color:#fff;padding:18px 26px}}
header h1{{margin:0;font-size:20px}}
header .sub{{color:#9fb3c8;font-size:13px;margin-top:4px}}
.tabs{{display:flex;flex-wrap:wrap;gap:4px;padding:10px 20px 0;background:#0f2033;position:sticky;top:0;z-index:5}}
.tab{{border:0;color:#cbd6e2;background:#1b3147;padding:8px 14px;border-radius:7px 7px 0 0;cursor:pointer;font-size:13px}}
.tab:hover{{background:#26425f}}
.tab.active{{background:var(--bg);color:var(--ink);font-weight:600}}
main{{max-width:1040px;margin:0 auto;padding:24px 26px 60px}}
.panel{{display:none}}
.panel.active{{display:block}}
h2{{font-size:20px;margin:.2em 0 .4em}}
h3{{font-size:16px;margin:1.4em 0 .5em;color:var(--ink)}}
.lede,.totals,.note{{color:var(--mut)}}
.totals b{{font-size:15px}}
table{{border-collapse:collapse;width:100%;margin:14px 0;font-size:14px;background:#fff;border:1px solid var(--line);border-radius:8px;overflow:hidden}}
th,td{{padding:8px 11px;border-bottom:1px solid var(--line);text-align:left}}
th{{background:#eef2f7;font-weight:600}}
td.num,th.num{{text-align:right;font-variant-numeric:tabular-nums}}
tr.tot td{{font-weight:700;background:#f0f4f9;border-top:2px solid #c7d2e0}}
.neg{{color:var(--neg)}}
.pos{{color:var(--pos)}}
a{{color:var(--accent);text-decoration:none}}
a:hover{{text-decoration:underline}}
.chart{{margin:8px 0 4px}}
.barrow{{display:flex;align-items:center;gap:10px;margin:5px 0}}
.blabel{{width:130px;font-size:13px;color:var(--mut)}}
.bar{{flex:1;background:#edf0f5;border-radius:4px;height:16px;position:relative}}
.fill{{display:block;height:100%;background:linear-gradient(90deg,#e06b5c,#c0392b);border-radius:4px}}
.bval{{width:92px;text-align:right;font-size:13px;font-variant-numeric:tabular-nums;color:var(--neg)}}
.vtoggle{{margin:0 0 14px}}
.vt{{border:1px solid var(--line);background:#fff;padding:6px 12px;cursor:pointer;font-size:13px}}
.vt:first-child{{border-radius:6px 0 0 6px}}
.vt:last-child{{border-radius:0 6px 6px 0;border-left:0}}
.vt.active{{background:var(--accent);color:#fff;border-color:var(--accent)}}
.panel pre{{background:#0f2033;color:#d6e2f0;padding:12px;border-radius:8px;overflow:auto;font-size:12.5px;line-height:1.35}}
.panel blockquote{{border-left:3px solid var(--accent);margin:12px 0;padding:6px 14px;background:#eef4ff;color:#33455c;border-radius:0 6px 6px 0}}
.panel em{{color:var(--mut)}}
.panel hr{{border:0;border-top:1px solid var(--line);margin:22px 0}}
</style></head><body>
<header><h1>Lower Tertiary Field Economics &mdash; Portfolio</h1>
<div class="sub">Gulf of Mexico Wilcox play &middot; full-cycle NPV from public BSEE data &middot; generated by worldenergydata</div></header>
<nav class="tabs">{tabbar}</nav>
<main>{panels}</main>
<script>
function showTab(id){{
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  var p=document.getElementById('tab-'+id); if(p)p.classList.add('active');
  var b=document.querySelector('.tab[data-tab="'+id+'"]'); if(b)b.classList.add('active');
  window.scrollTo(0,0);
}}
function showVar(slug,which,btn){{
  ['latest','frozen'].forEach(function(w){{
    var el=document.getElementById('var-'+slug+'-'+w);
    if(el)el.style.display=(w===which)?'block':'none';
  }});
  var grp=btn.parentNode.querySelectorAll('.vt');
  grp.forEach(function(x){{x.classList.remove('active')}});
  btn.classList.add('active');
}}
</script>
</body></html>
"""


if __name__ == "__main__":
    main()
