# ABOUTME: Generate client-facing 1-page capability PDFs (light theme, branded).
# ABOUTME: One PDF per left-nav section and per live work; rendered via headless Chrome.
"""Build the **capability one-pagers** — a single-page, client-facing PDF for every
left-nav section and every live work surfaced on ``/capabilities/``.

Each one-pager is a self-contained, light-themed, A4 page (worldenergydata logo,
what-it-is, key figures, what-you-get, and the live link) rendered to PDF with
headless Chrome. Output: ``reports/capabilities/pdf/<id>.pdf`` (committed frozen
artifacts; ``build_pages.py`` copies them to ``public/capabilities/pdf/``).

Run:
    .venv/bin/python scripts/capabilities/build_onepagers.py
    # needs google-chrome on PATH; override with CHROME=/path/to/chrome
"""

from __future__ import annotations

import html
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_OUT = _REPO / "reports" / "capabilities" / "pdf"
_TOKENS = (_REPO / "reports" / "capabilities" / "assets" / "tokens.css").read_text(encoding="utf-8").strip()
_SITE = "https://vamseeachanta.github.io/worldenergydata"
_CHROME = os.environ.get("CHROME") or shutil.which("google-chrome") or shutil.which(
    "google-chrome-stable"
) or shutil.which("chromium")

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

# Each spec: id, kind (section|work), title, std (basis line), path (live page),
# blurb (what it is), figures [(value,label)], bullets (what you get).
SPECS: list[dict] = [
    # ---- sections (one per left-nav menu item) ----
    dict(id="sec-economics", kind="section", title="Field economics & benchmarking",
         std="BSEE OGOR-A · life-to-date, public data", path="capabilities/#economics",
         blurb="Per-well, per-block and per-field NPV (@10%) and breakeven WTI for the seven "
               "Lower-Tertiary deepwater fields, computed from public BSEE production filings — "
               "life-to-date, not full-cycle — and regression-guarded by a CI test on every change.",
         figures=[("7", "deepwater fields"), ("158", "producing wells"), ("685.0", "MMbbl cum. oil")],
         bullets=["Life-to-date cashflow, NPV timeline and breakeven per field",
                  "Price sensitivity (dNPV/dWTI), reproducible to the cent",
                  "Portfolio roll-up plus cross-field well benchmarking (2010–latest)"]),
    dict(id="sec-wells", kind="section", title="Well operations",
         std="BSEE Well Activity Reports · directional surveys", path="capabilities/#wells",
         blurb="Drilling and completion performance and well geometry reconstructed directly "
               "from BSEE Well Activity Reports for the Lower-Tertiary deepwater play.",
         figures=[("217", "wells"), ("12", "fields"), ("38 / 24 d", "median drill / completion")],
         bullets=["Spud→TD drilling and TD→final-activity completion spans, medians by field",
                  "Per-well depth and water-depth context (to 37,743 ft MD)",
                  "Interactive 3D directional surveys from one frozen data contract"]),
    dict(id="sec-playbook", kind="section", title="Offshore field-development playbook",
         std="SubseaIQ catalog × BSEE assets", path="capabilities/#playbook",
         blurb="From a field's parameters to a ranked development concept, a to-scale subsea "
               "schematic and indicative economics — generated deterministically across every "
               "major offshore region.",
         figures=[("~2,150", "global fields"), ("333", "Gulf of Mexico"), ("115", "BSEE-matched")],
         bullets=["Concept-selection engine at Concept-Select / FEL-1 fidelity",
                  "To-scale subsea schematics and 3D hardware, self-contained",
                  "Recommended vs as-built concept across 115 BSEE-cross-referenced fields"]),
    dict(id="sec-safety", kind="section", title="Offshore safety & HSE",
         std="BSEE · USCG · TSB · IMO GISIS · MAIB", path="capabilities/#safety",
         blurb="Public marine-casualty and offshore-incident data, normalized and analysed "
               "deterministically — incident classification, cause-event breakdowns, and "
               "engineering screens anchored to real failures.",
         figures=[("102,618", "incident records"), ("7,349", "fatalities analysed"), ("13,338", "IMO casualties")],
         bullets=["Cross-database fatality / foundering / hatch breakdowns",
                  "IMO GISIS casualties by severity, vessel type and flag state (1900–2025)",
                  "Mooring-fatigue screening anchored to real BSEE failure incidents"]),
    dict(id="sec-validation", kind="section", title="Verified figures & provenance",
         std="source-traceable · CI-guarded", path="capabilities/#validation",
         blurb="Every published number traces to a public regulatory filing; the economics are "
               "regression-guarded by CI so a result can never silently drift from the method it "
               "claims.",
         figures=[("BSEE", "public source"), ("CI", "regression-guarded"), ("100%", "source-traceable")],
         bullets=["Every figure labelled with its source and any data limits",
                  "Deterministic, stdlib-only static build — identical for everyone, every time",
                  "Where data is incomplete, each page says so rather than guessing"]),
    # ---- works (one per live card) ----
    *[dict(id=f"economics-{slug}", kind="work", title=f"{name} field economics",
           std="BSEE OGOR-A · life-to-date, public data", path=f"economics-{slug}.html",
           blurb=f"Per-well stackup, NPV timeline and critical-operations detail for the {name} "
                 "Lower-Tertiary deepwater field, life-to-date on public BSEE data (not full-cycle).",
           figures=[], bullets=["Per-well and field-level NPV (@10%), breakeven WTI and cashflow",
                                 "NPV timeline with drilling/completion operation markers",
                                 "Deterministic and regression-guarded by CI on every change"])
      for slug, name in [("anchor", "Anchor"), ("big_foot", "Big Foot"),
                         ("cascade_chinook", "Cascade–Chinook"), ("jack_st_malo", "Jack / St. Malo"),
                         ("julia", "Julia"), ("shenandoah", "Shenandoah"), ("stones", "Stones")]],
    dict(id="portfolio", kind="work", title="Lower-Tertiary portfolio summary",
         std="field-by-field roll-up", path="portfolio.html",
         blurb="The whole Lower-Tertiary play at a glance, aggregated from the per-field "
               "economics.",
         figures=[("7", "fields"), ("158", "wells"), ("685.0", "MMbbl")],
         bullets=["Side-by-side NPV and production across all seven fields",
                  "Inherits each field's figures and data limits"]),
    dict(id="benchmark", kind="work", title="Well benchmarking",
         std="BSEE OGOR-A · 2010–latest", path="benchmark.html",
         blurb="Cross-field per-well performance benchmarking over the Lower-Tertiary play.",
         figures=[], bullets=["Normalized cumulative and rate comparisons across fields",
                              "Same data window as the field economics"]),
    dict(id="completion", kind="work", title="Drilling & completion days",
         std="BSEE Well Activity Reports", path="completion/",
         blurb="WAR-derived drilling and completion durations across the Lower-Tertiary "
               "deepwater fields, with medians by field and full depth context.",
         figures=[("217", "wells"), ("12", "fields"), ("38 / 24 d", "median drill / compl.")],
         bullets=["Spud→TD drilling and TD→final-activity completion spans",
                  "Per-field medians robust to sidetracks and recompletions",
                  "Deterministic from a frozen WAR-derived reference workbook"]),
    dict(id="well-path", kind="work", title="Julia well paths (3D)",
         std="BSEE directional surveys", path="well-path.html",
         blurb="Interactive 3D directional surveys for the Julia development, two renderers "
               "(Plotly + Three.js) driven by one frozen JSON data contract.",
         figures=[], bullets=["North/east-correct 3D well geometry",
                              "One data contract → two independent renderers"]),
    dict(id="fd-showcase", kind="work", title="Field-development capability showcase",
         std="concept → schematic → economics", path="field-development/showcase.html",
         blurb="What the field-development playbook produces end-to-end, with generated subsea "
               "schematics for real fields across every major offshore region.",
         figures=[], bullets=["Concept selection, schematic and indicative economics in one view",
                              "Verified exemplar fields per offshore region"]),
    dict(id="fd-playbook", kind="work", title="Interactive playbook",
         std="live parameter sliders", path="field-development/playbook.html",
         blurb="Move water depth, reserves and tieback distance and watch the recommended "
               "development concept and its schematic update live.",
         figures=[], bullets=["Instant concept recommendation from field parameters",
                              "To-scale schematic regenerates as you move the sliders"]),
    dict(id="fd-portfolio", kind="work", title="Deepwater portfolio",
         std="10-field Gulf of Mexico", path="field-development/portfolio/",
         blurb="Full field-development plans for a 10-field deepwater Gulf of Mexico portfolio, "
               "one page per field.",
         figures=[("10", "fields")], bullets=["DEXPI-style layout plus 3D hardware",
                                              "One self-contained page per field"]),
    dict(id="fd-bsee-matched", kind="work", title="BSEE-matched fields",
         std="recommended vs as-built", path="field-development/bsee-matched/",
         blurb="Recommended versus as-built development concept, with schematics, across "
               "BSEE-cross-referenced Gulf of Mexico fields.",
         figures=[("115", "fields")], bullets=["Engine pick vs the real as-built concept",
                                               "Schematics for every matched field"]),
    dict(id="ms-exec", kind="work", title="Marine safety analytics",
         std="TSB · IMO GISIS · MAIB", path="marine_safety/executive_summary.html",
         blurb="Cross-database marine-casualty analysis — the executive summary and entry point "
               "to the fatality, foundering and hatch breakdowns.",
         figures=[("102,618", "records"), ("7,349", "fatalities")],
         bullets=["Combined public casualty databases, normalized",
                  "Links through to fatality / foundering / hatch detail"]),
    dict(id="ms-fatality", kind="work", title="Fatality analysis",
         std="cross-database", path="marine_safety/fatality_analysis.html",
         blurb="Fatal-incident breakdown and leading causes across the combined casualty databases.",
         figures=[], bullets=["Leading fatal-incident causes ranked", "Counts by category"]),
    dict(id="ms-foundering", kind="work", title="Foundering analysis",
         std="cross-database", path="marine_safety/foundering_analysis.html",
         blurb="Foundering-incident breakdown, fatality distribution and patterns.",
         figures=[], bullets=["Fatality distribution per incident", "Pattern breakdown"]),
    dict(id="ms-hatch", kind="work", title="Hatch analysis",
         std="cross-database", path="marine_safety/hatch_analysis.html",
         blurb="Hatch-maloperation incidents detected and classified by severity.",
         figures=[], bullets=["Severity classification of detected incidents",
                              "Regex-detected from the full incident corpus"]),
    dict(id="imo", kind="work", title="IMO GISIS casualties",
         std="IMO GISIS public database", path="IMO_GISIS_Executive_Report.html",
         blurb="Marine casualties by severity, vessel type and flag state from the IMO GISIS "
               "public database, 1900–2025.",
         figures=[("13,338", "casualties"), ("38.7%", "very serious")],
         bullets=["Severity, vessel-type and flag-state breakdowns",
                  "125-year coverage with trend analysis"]),
    dict(id="mooring", kind="work", title="Mooring-fatigue grounded card",
         std="DNV-OS-E301 T-N curves", path="hse/mooring-fatigue-grounded-card.html",
         blurb="Mooring fatigue-life screening anchored to real BSEE mooring-failure incidents.",
         figures=[("18.4 yr", "governing life"), ("25 yr", "design")],
         bullets=["T-N curve fatigue screen vs design life",
                  "Anchored to documented BSEE failure precedents"]),
]

_TEMPLATE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<style>
  @page{{size:A4;margin:0}}
  {tokens}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:Arial,Helvetica,sans-serif;color:var(--ink);background:#fff;
       width:210mm;min-height:297mm;padding:18mm 18mm 14mm}}
  .top{{display:flex;align-items:center;justify-content:space-between;
       border-bottom:2px solid var(--navy);padding-bottom:12px}}
  .top svg{{height:30px;width:auto}}
  .kind{{font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:var(--teal);font-weight:700}}
  h1{{font-size:30px;color:var(--navy);margin:26px 0 4px;letter-spacing:-.4px;line-height:1.15}}
  .std{{color:var(--teal);font-weight:700;font-size:13px}}
  .blurb{{color:var(--ink);font-size:14.5px;line-height:1.55;margin:18px 0 4px;max-width:165mm}}
  .figs{{display:flex;gap:14px;margin:22px 0 6px}}
  .fig{{flex:1;background:var(--soft);border:1px solid var(--line);border-radius:12px;padding:14px 16px}}
  .fig .v{{font-size:25px;font-weight:800;color:var(--navy);letter-spacing:-.5px}}
  .fig .l{{font-size:11.5px;color:var(--muted);margin-top:3px}}
  h2{{font-size:13px;text-transform:uppercase;letter-spacing:1px;color:var(--muted);
     margin:26px 0 10px;border-left:4px solid var(--teal);padding-left:10px}}
  ul{{list-style:none}}
  li{{font-size:14px;line-height:1.5;padding:6px 0 6px 24px;position:relative;border-bottom:1px solid var(--line)}}
  li:before{{content:"";position:absolute;left:4px;top:13px;width:8px;height:8px;border-radius:50%;
            background:var(--teal)}}
  .foot{{position:absolute;left:18mm;right:18mm;bottom:14mm;border-top:1px solid var(--line);
        padding-top:10px;display:flex;justify-content:space-between;align-items:flex-end;
        font-size:11.5px;color:var(--muted)}}
  .foot .live{{color:var(--navy);font-weight:700}}
  .cta{{background:linear-gradient(135deg,#0f8a7e,#0B3D91);color:#fff;font-weight:700;
       font-size:12px;padding:8px 14px;border-radius:9px;display:inline-block}}
</style></head>
<body>
  <div class="top">{logo}<div class="kind">Capability one-pager</div></div>
  <div class="std">{std}</div>
  <h1>{title}</h1>
  <p class="blurb">{blurb}</p>
  {figs}
  <h2>What you get</h2>
  <ul>{bullets}</ul>
  <div class="foot">
    <div>worldenergydata · open energy-data · deterministic outputs on public regulatory filings<br>
      <span class="live">Explore live: {live}</span></div>
    <span class="cta">View interactive &rarr;</span>
  </div>
</body></html>"""


def _render_html(spec: dict) -> str:
    figs = ""
    if spec["figures"]:
        cells = "".join(
            f'<div class="fig"><div class="v">{html.escape(v)}</div>'
            f'<div class="l">{html.escape(l)}</div></div>'
            for v, l in spec["figures"]
        )
        figs = f'<div class="figs">{cells}</div>'
    bullets = "".join(f"<li>{html.escape(b)}</li>" for b in spec["bullets"])
    live = f"{_SITE}/{spec['path']}"
    return _TEMPLATE.format(tokens=_TOKENS, 
        logo=_LOGO, std=html.escape(spec["std"]), title=html.escape(spec["title"]),
        blurb=html.escape(spec["blurb"]), figs=figs, bullets=bullets, live=html.escape(live),
    )


def _to_pdf(html_text: str, out_pdf: Path) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html_text)
        src = f.name
    try:
        subprocess.run(
            [_CHROME, "--headless", "--no-sandbox", "--disable-gpu",
             "--no-pdf-header-footer", f"--print-to-pdf={out_pdf}", src],
            check=True, capture_output=True, timeout=90,
        )
    finally:
        os.unlink(src)


def main() -> None:
    if not _CHROME:
        raise SystemExit("No Chrome found; set CHROME=/path/to/google-chrome")
    _OUT.mkdir(parents=True, exist_ok=True)
    ids = set()
    for spec in SPECS:
        assert spec["id"] not in ids, f"duplicate id {spec['id']}"
        ids.add(spec["id"])
        _to_pdf(_render_html(spec), _OUT / f"{spec['id']}.pdf")
    print(f"Wrote {len(SPECS)} one-pager PDFs into {_OUT.relative_to(_REPO)}/")


if __name__ == "__main__":
    main()
