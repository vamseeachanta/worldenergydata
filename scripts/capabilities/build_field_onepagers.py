# ABOUTME: Generate client-facing per-field 1-page PDFs for the 10 Explorer fields.
# ABOUTME: One PDF per Lower-Tertiary field, rendered via headless Chrome (mirrors build_onepagers).
"""Build the **per-field one-pagers** — a single-page, client-facing PDF for each
of the 10 Lower-Tertiary Explorer fields (worldenergydata #945, E5 client layer).

Each one-pager is a self-contained, light-themed A4 page (worldenergydata logo,
field name, operator/region, key metrics, HPHT + decommissioning risk chips, a
performance snapshot, a lease/landman summary and the provenance line) rendered
to PDF with headless Chrome. Output:

    reports/field-atlas/onepagers/field-<id>.pdf   (frozen artifact)
    reports/field-atlas/onepagers/field-<id>.html  (committed HTML intermediate)

``build_pages.py`` copies the ``onepagers/`` set to ``public/field-atlas/onepagers/``.

OWNER PRINCIPLE (#945): the three pre-production fields (kaskida, north_platte,
tiber) have ``performance == null``. Rather than a bare em-dash, their performance
panel renders a VISIBLE placeholder that LINKS the rollout issue #948 — matching
the Explorer shell's ``renderWells`` pre-production note pattern.

This lane is self-contained: it does NOT touch the lifecycle-poster builder or the
shared lifecycle/atlas HTML templates (another lane edits those concurrently).

Run:
    .venv/bin/python scripts/capabilities/build_field_onepagers.py
    # needs google-chrome on PATH; override with CHROME=/path/to/chrome
"""

from __future__ import annotations

import html
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_EXPLORER = _REPO / "reports" / "lower_tertiary" / "lifecycle" / "_explorer.json"
_OUT = _REPO / "reports" / "field-atlas" / "onepagers"
_TOKENS = (
    (_REPO / "reports" / "capabilities" / "assets" / "tokens.css")
    .read_text(encoding="utf-8")
    .strip()
)
_SITE = "https://vamseeachanta.github.io/worldenergydata"
_ROLLOUT_ISSUE = "https://github.com/vamseeachanta/worldenergydata/issues/948"
# FDP-authoring backlog for the 7 concept-less LT fields (#759 → #962).
_FDP_ISSUE = "https://github.com/vamseeachanta/worldenergydata/issues/962"
_CHROME = (
    os.environ.get("CHROME")
    or shutil.which("google-chrome")
    or shutil.which("google-chrome-stable")
    or shutil.which("chromium")
)

# Canonical field order (matches _explorer.json field ordering; 10 fields).
FIELD_ORDER = [
    "big_foot",
    "anchor",
    "cascade_chinook",
    "jack_st_malo",
    "julia",
    "kaskida",
    "north_platte",
    "shenandoah",
    "stones",
    "tiber",
]

_LOGO = """<svg viewBox="0 0 400 64" xmlns="http://www.w3.org/2000/svg" aria-label="worldenergydata">
  <g fill="none" stroke-width="3">
    <circle cx="32" cy="32" r="23" stroke="#0B3D91"/>
    <ellipse cx="32" cy="32" rx="9.5" ry="23" stroke="#2BB2A6" stroke-width="2.5"/>
    <line x1="9" y1="32" x2="55" y2="32" stroke="#2BB2A6" stroke-width="2.5"/>
    <line x1="13.5" y1="19" x2="50.5" y2="19" stroke="#0B3D91" stroke-width="2"/>
    <line x1="13.5" y1="45" x2="50.5" y2="45" stroke="#0B3D91" stroke-width="2"/>
  </g>
  <circle cx="32" cy="32" r="3" fill="#2BB2A6"/>
  <text x="74" y="43" font-family="Arial,Helvetica,sans-serif" font-size="31" font-weight="800" letter-spacing="-0.6">
    <tspan fill="#0B3D91">world</tspan><tspan fill="#2BB2A6">energy</tspan><tspan fill="#0B3D91">data</tspan>
  </text>
</svg>"""

_TEMPLATE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<style>
  @page{{size:A4;margin:0}}
  {tokens}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:Arial,Helvetica,sans-serif;color:var(--ink);background:#fff;
       width:210mm;min-height:297mm;padding:16mm 18mm 14mm}}
  .top{{display:flex;align-items:center;justify-content:space-between;
       border-bottom:2px solid var(--navy);padding-bottom:12px}}
  .top svg{{height:30px;width:auto}}
  .kind{{font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:var(--teal);font-weight:700}}
  h1{{font-size:29px;color:var(--navy);margin:20px 0 3px;letter-spacing:-.4px;line-height:1.15}}
  .sub{{color:var(--muted);font-weight:600;font-size:13.5px}}
  .chips{{margin:12px 0 2px;display:flex;gap:8px;flex-wrap:wrap}}
  .chip{{font-size:11.5px;font-weight:700;padding:4px 10px;border-radius:999px;
        border:1px solid var(--teal);color:var(--teal);background:transparent}}
  .chip.hpht{{border-color:#f5a524;color:#b9760a}}
  .mets{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:18px 0 4px}}
  .met{{background:var(--soft);border:1px solid var(--line);border-radius:11px;padding:11px 13px}}
  .met .v{{font-size:20px;font-weight:800;color:var(--navy);letter-spacing:-.5px}}
  .met .l{{font-size:11px;color:var(--muted);margin-top:2px}}
  h2{{font-size:12.5px;text-transform:uppercase;letter-spacing:1px;color:var(--muted);
     margin:22px 0 9px;border-left:4px solid var(--teal);padding-left:10px}}
  .snap{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}}
  .snap .cell{{border:1px solid var(--line);border-radius:10px;padding:9px 11px}}
  .snap .v{{font-size:16px;font-weight:800;color:var(--ink)}}
  .snap .l{{font-size:10.5px;color:var(--muted);margin-top:2px}}
  .ph{{background:var(--soft);border:1px dashed var(--teal);border-radius:10px;padding:12px 14px;
      font-size:13px;line-height:1.5;color:var(--ink)}}
  .ph a{{color:var(--navy);font-weight:700}}
  .arch{{border:1px solid var(--line);border-radius:11px;padding:12px 14px;text-align:center}}
  .arch svg{{max-width:100%;height:auto}}
  .arch .cap{{font-size:11px;color:var(--muted);margin-top:6px;text-align:left}}
  table.lease{{width:100%;border-collapse:collapse;font-size:12px;margin-top:4px}}
  table.lease th{{text-align:left;color:var(--muted);font-size:10.5px;text-transform:uppercase;
                 letter-spacing:.5px;border-bottom:1px solid var(--line);padding:4px 6px}}
  table.lease td{{padding:5px 6px;border-bottom:1px solid var(--line)}}
  .leadin{{font-size:12px;color:var(--muted);margin:0 0 4px}}
  .pending{{color:var(--muted)}}
  .prov{{font-size:11px;line-height:1.5;color:var(--muted);margin-top:16px;
        border-top:1px solid var(--line);padding-top:10px}}
  .foot{{position:absolute;left:18mm;right:18mm;bottom:14mm;border-top:1px solid var(--line);
        padding-top:9px;display:flex;justify-content:space-between;align-items:flex-end;
        font-size:11px;color:var(--muted)}}
  .foot .live{{color:var(--navy);font-weight:700}}
</style></head>
<body>
  <div class="top">{logo}<div class="kind">Field one-pager · Lower Tertiary</div></div>
  <h1>{name}</h1>
  <p class="sub">{operator} &middot; {region}</p>
  {chips}
  <div class="mets">{mets}</div>
  <h2>Field architecture</h2>
  {architecture}
  <h2>Performance snapshot</h2>
  {perf}
  <h2>Lease &amp; landman</h2>
  {lease}
  <p class="prov">Provenance: {provenance}</p>
  <div class="foot">
    <div>worldenergydata &middot; open energy-data &middot; deterministic outputs on public regulatory filings<br>
      <span class="live">Explore live: {live}</span></div>
    <span>Status: {status}</span>
  </div>
</body></html>"""


def load_explorer() -> dict:
    """Load the frozen Explorer payload (fields dict + flat wells list)."""
    return json.loads(_EXPLORER.read_text(encoding="utf-8"))


def _chips(field: dict) -> str:
    risk = field.get("risk") or {}
    out = []
    hpht = risk.get("hpht")
    if hpht and hpht.get("label"):
        out.append(f'<span class="chip hpht">{html.escape(hpht["label"])}</span>')
    dec = risk.get("decommissioning")
    if dec and dec.get("label"):
        out.append(f'<span class="chip">{html.escape(dec["label"])}</span>')
    if not out:
        return ""
    return f'<div class="chips">{"".join(out)}</div>'


def _metrics(field: dict) -> str:
    cells = []
    for m in field.get("metrics") or []:
        v = str(m.get("v", "")).strip()
        u = str(m.get("u", "")).strip()
        val = f"{v} {u}".strip() if u else v
        cells.append(
            f'<div class="met"><div class="v">{html.escape(val)}</div>'
            f'<div class="l">{html.escape(str(m.get("k", "")))}</div></div>'
        )
    return "".join(cells)


def _perf(field: dict) -> str:
    """Performance snapshot, or an issue-linked placeholder for pre-production
    fields (performance is null) — the OWNER PRINCIPLE for #945."""
    perf = field.get("performance")
    if not perf:
        return (
            '<div class="ph">Production &amp; performance figures are pending &mdash; this '
            "field is pre-production, so no oil has flowed yet. Rollout tracked in "
            f'<a href="{_ROLLOUT_ISSUE}">#948</a>.</div>'
        )

    def _num(v, suffix=""):
        if v is None:
            return "&mdash;"
        return html.escape(f"{v}{suffix}")

    cells = [
        (_num(perf.get("cum_oil_mmbbl")), "Cum. oil (MMbbl)"),
        (_num(perf.get("wells")), "Producing wells"),
        (_num(perf.get("avg_uptime_pct"), "%"), "Avg uptime"),
        (_num(perf.get("avg_decline_pct_yr"), "%/yr"), "Avg decline"),
        (_num(perf.get("eur_mmbbl")), "EUR (MMbbl)"),
        (
            (
                "$" + str(perf.get("breakeven_wti"))
                if perf.get("breakeven_wti") is not None
                else "&mdash;"
            ),
            "Breakeven WTI",
        ),
        (_num(perf.get("npv_mm"), " $MM"), "NPV (V30)"),
        (_num(perf.get("interventions")), "Interventions"),
    ]
    body = "".join(
        f'<div class="cell"><div class="v">{v}</div><div class="l">{html.escape(lab)}</div></div>'
        for v, lab in cells
    )
    return f'<div class="snap">{body}</div>'


def _architecture(field: dict) -> str:
    """Inline plan-view SVG for an authored field, else an issue-linked
    placeholder (#969). The SVG string comes verbatim from the Explorer payload
    (rendered once by the poster builder), so it is identity-gate-consistent and
    already PDF-portable (no pattern/clip-path/filter/mask)."""
    arch = field.get("architecture") or {}
    svg = arch.get("svg")
    if not svg:
        return (
            '<div class="ph">A to-scale field architecture drawing is pending &mdash; '
            "this field has no committed development-concept geometry yet. Tracked in "
            f'<a href="{_FDP_ISSUE}">#962</a>.</div>'
        )
    caption = arch.get("caption") or ""
    cap = f'<div class="cap">Plan view &middot; {html.escape(caption)}</div>' if caption else ""
    return f'<div class="arch">{svg}{cap}</div>'


def _lease(field: dict) -> str:
    lm = field.get("landman") or {}
    leases = lm.get("leases") or []
    iss = f"https://github.com/vamseeachanta/worldenergydata/issues/{lm.get('ingest_issue', 951)}"
    ph = f'<a class="pending" href="{iss}">&mdash; pending</a>'
    wi = " &middot; ".join(
        f"{html.escape(w['name'])} {w['wi']}%"
        + (" (op)" if w.get("operator") or w.get("lead") else "")
        for w in (lm.get("working_interest") or field.get("workingInterest") or [])
    )
    blocks = ", ".join(lm.get("blocks") or [])
    leadin = (
        f'<p class="leadin">Operator <b>{html.escape(lm.get("operator") or field.get("operator") or "—")}</b>'
        f'{(" &middot; WI " + wi) if wi else ""}'
        f'{(" &middot; Blocks " + html.escape(blocks)) if blocks else ""}</p>'
    )
    rows = []
    for r in leases:
        depth = f'{r["water_depth_ft"]:,} ft' if r.get("water_depth_ft") else ph
        dev = html.escape(r["dev_system"]) if r.get("dev_system") else ph
        rows.append(
            f"<tr><td>{html.escape(str(r.get('lease_num', '')))}</td>"
            f"<td>{depth}</td><td>{dev}</td><td>{ph}</td></tr>"
        )
    if not rows:
        rows.append(f'<tr><td colspan="4">{ph}</td></tr>')
    note = (
        f'<p class="leadin" style="margin-top:6px">Status, dates &amp; per-lease detail pending '
        f'the <a href="{iss}">BSEE lease ingest (#{lm.get("ingest_issue", 951)})</a>.</p>'
    )
    return (
        leadin
        + '<table class="lease"><thead><tr><th>Lease</th><th>Depth</th><th>Dev</th>'
        + "<th>Status</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
        + note
    )


def render_field_html(fid: str, field: dict) -> str:
    """Render one self-contained one-page HTML for a field."""
    return _TEMPLATE.format(
        tokens=_TOKENS,
        logo=_LOGO,
        name=html.escape(field.get("name", fid)),
        operator=html.escape(field.get("operator") or "—"),
        region=html.escape(field.get("region") or "—"),
        chips=_chips(field),
        mets=_metrics(field),
        architecture=_architecture(field),
        perf=_perf(field),
        lease=_lease(field),
        provenance=html.escape(field.get("provenance") or "—"),
        live=html.escape(f"{_SITE}/field-atlas/#/field/{fid}"),
        status=html.escape(field.get("statusLabel") or "—"),
    )


def _to_pdf(html_text: str, out_pdf: Path) -> None:
    with tempfile.NamedTemporaryFile(
        "w", suffix=".html", delete=False, encoding="utf-8"
    ) as f:
        f.write(html_text)
        src = f.name
    try:
        subprocess.run(
            [
                _CHROME,
                "--headless",
                "--no-sandbox",
                "--disable-gpu",
                "--no-pdf-header-footer",
                f"--print-to-pdf={out_pdf}",
                src,
            ],
            check=True,
            capture_output=True,
            timeout=90,
        )
    finally:
        os.unlink(src)


def main() -> None:
    data = load_explorer()
    fields = data["fields"]
    missing = [fid for fid in FIELD_ORDER if fid not in fields]
    if missing:
        raise SystemExit(f"Explorer payload missing fields: {missing}")
    _OUT.mkdir(parents=True, exist_ok=True)
    n_pdf = 0
    for fid in FIELD_ORDER:
        html_text = render_field_html(fid, fields[fid])
        (_OUT / f"field-{fid}.html").write_text(html_text, encoding="utf-8")
        if _CHROME:
            _to_pdf(html_text, _OUT / f"field-{fid}.pdf")
            n_pdf += 1
    where = _OUT.relative_to(_REPO)
    if _CHROME:
        print(f"Wrote {n_pdf} field one-pager PDFs (+HTML intermediates) into {where}/")
    else:
        print(
            f"No Chrome found — wrote {len(FIELD_ORDER)} HTML intermediates into {where}/ "
            "(set CHROME=/path/to/google-chrome to render PDFs)"
        )


if __name__ == "__main__":
    main()
