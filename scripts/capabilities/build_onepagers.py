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
         std="BSEE OGOR-A · sanctioned V30 golden baseline", path="capabilities/#economics",
         blurb="Per-well, per-block and per-field NPV / MIRR / IRR for the seven Lower-Tertiary "
               "deepwater fields, computed from public BSEE production filings and sanctioned "
               "against a frozen V30 baseline that a CI test re-checks on every change.",
         figures=[("7", "deepwater fields"), ("158", "producing wells"), ("685.0", "MMbbl cum. oil")],
         bullets=["Life-to-date cashflow, NPV timeline and breakeven per field",
                  "Price sensitivity (dNPV/dWTI) and MIRR, reproducible to the cent",
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
    dict(id="sec-validation", kind="section", title="Sanctioned figures & provenance",
         std="frozen golden baselines · CI-guarded", path="capabilities/#validation",
         blurb="Every published number traces to a public regulatory filing; the sanctioned "
               "economics reproduce a frozen reference baseline, CI-guarded so a result can "
               "never silently drift from the model it claims.",
         figures=[("V30", "golden baseline"), ("CI", "regression-guarded"), ("100%", "source-traceable")],
         bullets=["Sanctioned-baseline vs data-derived clearly labelled on every figure",
                  "Deterministic, stdlib-only static build — identical for everyone, every time",
                  "Where data is incomplete, each page says so rather than guessing"]),
    # ---- works (one per live card) ----
    *[dict(id=f"economics-{slug}", kind="work", title=f"{name} field economics",
           std="BSEE OGOR-A · sanctioned V30", path=f"economics-{slug}.html",
           blurb=f"Per-well stackup, NPV timeline and critical-operations detail for the {name} "
                 "Lower-Tertiary deepwater field, sanctioned against the frozen V30 baseline.",
           figures=[], bullets=["Per-well and field-level NPV, MIRR, IRR and cashflow",
                                 "NPV timeline with drilling/completion operation markers",
                                 "Reproducible to the sanctioned V30 golden baseline"])
      for slug, name in [("anchor", "Anchor"), ("big_foot", "Big Foot"),
                         ("cascade_chinook", "Cascade–Chinook"), ("jack_st_malo", "Jack / St. Malo"),
                         ("julia", "Julia"), ("shenandoah", "Shenandoah"), ("stones", "Stones")]],
    dict(id="portfolio", kind="work", title="Lower-Tertiary portfolio summary",
         std="field-by-field roll-up", path="portfolio.html",
         blurb="The whole Lower-Tertiary play at a glance, aggregated from the per-field "
               "sanctioned V30 economics.",
         figures=[("7", "fields"), ("158", "wells"), ("685.0", "MMbbl")],
         bullets=["Side-by-side NPV and production across all seven fields",
                  "Inherits each field's sanctioned figures and data limits"]),
    dict(id="benchmark", kind="work", title="Well benchmarking",
         std="BSEE OGOR-A · 2010–latest", path="benchmark.html",
         blurb="Cross-field per-well performance benchmarking over the Lower-Tertiary play.",
         figures=[], bullets=["Normalized cumulative and rate comparisons across fields",
                              "Same frozen data window as the V30 economics"]),
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
  :root{{--navy:#0B3D91;--teal:#0f8a7e;--ink:#13233f;--muted:#5b6b86;--line:#dbe4f0;--soft:#f4f8fc}}
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
  {ask}
  <div class="foot">
    <div>worldenergydata · open energy-data · deterministic outputs on public regulatory filings<br>
      <span class="live">Explore live: {live}</span></div>
    <span class="cta">View interactive &rarr;</span>
  </div>
</body></html>"""


# Capabilities whose output is produced by a deterministic registry workflow that
# is ALSO exposed on the Deckhand workflow-API — these get a real POST /api/run
# call. Everything else is a published report surface (HTTP GET of the report).
#
# NOTE: the field-economics pages are intentionally NOT mapped to a workflow. The
# underlying `fdas-field-npv` registry workflow exists and is locally runnable, but
# it is deliberately EXCLUDED from Deckhand's public routing on PII grounds
# (deckhand#513), so the bot will not run it. The sanctioned economics are already
# published as static reports, so their honest API is a GET of the report — we do
# not advertise a POST the platform won't serve.
WORKFLOW_MAP: dict[str, str] = {
    "benchmark": "bsee-well-comparison",
    "ms-exec": "marine-safety-stats",
}
_API_INVOKE = "uv run python -m worldenergydata {input}"
_BOT = "https://t.me/the_deckhand_bot"

# A ready-to-send natural-language "starting prompt" per live work — paste it to
# @the_deckhand_bot (hermes routes NL to the workflow) or pass it as the body of
# a workflow-API run. Keyed by spec id; works without a prompt fall back to a
# generic ask built from the title.
PROMPTS: dict[str, str] = {
    "economics-anchor": "Run the sanctioned V30 field economics for Anchor — per-well NPV, MIRR and the breakeven WTI.",
    "economics-big_foot": "Run the sanctioned V30 field economics for Big Foot — per-well NPV, MIRR and the breakeven WTI.",
    "economics-cascade_chinook": "Run the sanctioned V30 field economics for Cascade–Chinook — per-well NPV, MIRR and the breakeven WTI.",
    "economics-jack_st_malo": "Run the sanctioned V30 field economics for Jack / St. Malo — per-well NPV, MIRR and the breakeven WTI.",
    "economics-julia": "Run the sanctioned V30 field economics for Julia — per-well NPV, MIRR and the breakeven WTI.",
    "economics-shenandoah": "Run the sanctioned V30 field economics for Shenandoah — per-well NPV, MIRR and the breakeven WTI.",
    "economics-stones": "Run the sanctioned V30 field economics for Stones — per-well NPV, MIRR and the breakeven WTI.",
    "portfolio": "Give me the Lower-Tertiary portfolio economics roll-up across all seven fields.",
    "benchmark": "Benchmark Lower-Tertiary well performance across fields from 2010 to latest.",
    "completion": "Show drilling and completion days for the Lower-Tertiary fields, with medians by field.",
    "well-path": "Plot the Julia development well paths in 3D from the BSEE directional surveys.",
    "fd-showcase": "Show the field-development playbook end-to-end for a representative deepwater field.",
    "fd-playbook": "Recommend a development concept for a field at 1500 m water depth, 200 MMbbl recoverable, 30 km tieback.",
    "fd-portfolio": "Generate field-development plans for the 10-field deepwater Gulf of Mexico portfolio.",
    "fd-bsee-matched": "Compare recommended vs as-built development concepts across the BSEE-matched Gulf of Mexico fields.",
    "ms-exec": "Summarise the cross-database marine-safety casualty statistics.",
    "ms-fatality": "Break down marine fatalities by leading cause.",
    "ms-foundering": "Analyse foundering incidents and their fatality distribution.",
    "ms-hatch": "Find and classify hatch-maloperation incidents by severity.",
    "imo": "Summarise IMO GISIS marine casualties by severity, vessel type and flag state, 1900–2025.",
    "mooring": "Screen mooring fatigue life against the 25-year design using DNV-OS-E301 T-N curves.",
}


def _prompt_for(spec: dict) -> str:
    return PROMPTS.get(spec["id"], f"Run the worldenergydata {spec['title'].lower()} and send me the report.")


def _api_envelope(spec: dict) -> dict:
    """A typed, self-contained workflow-API ResultEnvelope for one capability —
    honest about whether it is a registry workflow or a published report surface."""
    report_url = f"{_SITE}/{spec['path']}"
    wf = WORKFLOW_MAP.get(spec["id"])
    env: dict = {
        "schema": "deckhand.workflow_api.ResultEnvelope/2",
        "status": "ok",
        "repo": "worldenergydata",
        "report_url": report_url,
        "provenance": {"basis": spec["std"], "deterministic": True,
                       "source": "public regulatory filings"},
    }
    if wf:
        env["request"] = {
            "method": "POST", "path": "/api/run",
            "body": {"repo": "worldenergydata", "workflow": wf, "inputs": {"field": spec["title"]}},
        }
        env["invocation"] = _API_INVOKE.format(input=f"examples/workflows/{wf}/input.yml")
        env["workflow"] = f"worldenergydata:{wf}"
        env["outputs"] = [{"kind": "report", "url": report_url}]
        env["note"] = ("Deterministic registry workflow (docs/registry/workflows.yaml). "
                       "POST to the Deckhand workflow-API, or run the invocation locally; "
                       "the embedded report is the rendered output.")
    else:
        env["request"] = {"method": "GET", "url": report_url}
        env["surface"] = f"worldenergydata:{spec['id']}"
        env["outputs"] = [{"kind": "report", "url": report_url}]
        env["note"] = ("Published report surface — the deterministic output is served as a "
                       "self-contained page; GET the report_url to consume it.")
    # Natural-language starting prompt + how-to-run, so users can fire it via the
    # Deckhand bot (hermes routes NL → workflow) or the HTTP / CLI paths.
    prompt = _prompt_for(spec)
    env["prompt"] = prompt
    how: list[dict] = [
        {"via": "telegram", "bot": "@the_deckhand_bot", "deep_link": _BOT,
         "step": f"Open @the_deckhand_bot and send: {prompt}"}
    ]
    if wf:
        how.append({"via": "http", "step": "POST /api/run with a scoped bearer token",
                    "body": env["request"]["body"]})
        how.append({"via": "cli", "step": env["invocation"]})
    else:
        how.append({"via": "http", "step": f"GET {report_url}"})
    env["how_to_run"] = how
    return env


_API_TEMPLATE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — API call</title>
<style>
  :root{{--navy:#0B3D91;--teal:#0f8a7e;--ink:#13233f;--muted:#5b6b86;--line:#dbe4f0;--soft:#f4f8fc}}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:Arial,Helvetica,sans-serif;color:var(--ink);background:#eef3fa;line-height:1.5}}
  .wrap{{max-width:1000px;margin:0 auto;padding:22px}}
  .top{{display:flex;align-items:center;justify-content:space-between;border-bottom:2px solid var(--navy);padding-bottom:12px}}
  .top svg{{height:28px}} .kind{{font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:var(--teal);font-weight:700}}
  h1{{font-size:23px;color:var(--navy);margin:18px 0 2px}}
  .std{{color:var(--teal);font-weight:700;font-size:12.5px}}
  .row{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:16px}}
  .panel{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px}}
  .panel h2{{font-size:11.5px;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-bottom:8px}}
  pre{{background:#0e1726;color:#d6e2f5;border-radius:9px;padding:12px;font:12px/1.5 ui-monospace,Menlo,monospace;overflow:auto;white-space:pre-wrap;word-break:break-word}}
  .verb{{display:inline-block;font:700 11px ui-monospace,monospace;background:var(--teal);color:#fff;padding:2px 8px;border-radius:6px;margin-bottom:8px}}
  a.btn{{display:inline-block;margin-top:10px;font-size:12.5px;font-weight:700;color:#fff;
        background:linear-gradient(135deg,#0f8a7e,#0B3D91);padding:8px 14px;border-radius:9px;text-decoration:none}}
  .reportwrap{{margin-top:16px;background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden}}
  .reportwrap .bar{{font-size:12px;color:var(--muted);padding:9px 14px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between}}
  iframe{{width:100%;height:560px;border:0;display:block;background:#fff}}
  .note{{color:var(--muted);font-size:12.5px;margin-top:6px}}
  a{{color:var(--navy)}}
  .bigpanel{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-top:16px}}
  .bigpanel h2{{font-size:11.5px;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-bottom:8px}}
  .prompt{{display:flex;gap:10px;align-items:flex-start}}
  .prompt .q{{flex:1;background:var(--soft);border:1px solid var(--line);border-radius:9px;padding:11px 13px;font-size:14px;color:var(--ink)}}
  .copy{{font:700 12px Arial;color:#fff;background:linear-gradient(135deg,#0f8a7e,#0B3D91);border:0;border-radius:9px;padding:10px 13px;cursor:pointer;white-space:nowrap}}
  .how ol{{margin:8px 0 0 18px}} .how li{{font-size:13.5px;margin:7px 0;color:var(--ink)}}
  .how code{{background:#0e1726;color:#d6e2f5;padding:1px 6px;border-radius:5px;font-size:12px}}
  /* a11y baseline (wh#3401 / #908): consistent keyboard focus + text-alternative helper */
  :where(a,button,input,select,textarea,summary,[tabindex]):focus-visible{{outline:2px solid var(--teal);outline-offset:2px;border-radius:3px}}
  .sr-only{{position:absolute!important;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}}
</style></head>
<body><div class="wrap">
  <div class="top"><a href="../" aria-label="Back to capabilities index" style="display:contents">{logo}</a><div class="kind">Workflow-API · self-contained call</div></div>
  <h1>{title}</h1><div class="std">{std}</div>

  <div class="bigpanel">
    <h2>Starting prompt — fire it at Deckhand</h2>
    <div class="prompt">
      <div class="q" id="prompt">{prompt}</div>
      <button class="copy" onclick="navigator.clipboard&amp;&amp;navigator.clipboard.writeText(document.getElementById('prompt').innerText)">Copy</button>
      <a class="copy" href="{bot}" style="text-decoration:none">Run on Deckhand &rarr;</a>
    </div>
    <div class="how"><h2 style="margin-top:14px">How to run the API</h2><ol>{howsteps}</ol></div>
  </div>

  <div class="row">
    <div class="panel"><h2>Request — input</h2><span class="verb">{verb}</span>{reqsnippet}</div>
    <div class="panel"><h2>Response — ResultEnvelope</h2><pre>{envelope}</pre>
      <a class="btn" href="{id}.json" download>Download envelope JSON &darr;</a></div>
  </div>
  <p class="note">{note}</p>
  <div class="reportwrap">
    <div class="bar"><span>Comprehensive report (live output)</span><a href="{report_url}">open full report &rarr;</a></div>
    <iframe src="{report_url}" loading="lazy" title="{title} report"></iframe>
  </div>
</div></body></html>"""


def _render_api_html(spec: dict, env: dict) -> str:
    import json as _json
    report_url = env["report_url"]
    if env["request"]["method"] == "POST":
        verb = "POST /api/run"
        body = _json.dumps(env["request"]["body"], indent=2)
        reqsnippet = (
            f"<pre>curl -X POST https://api.deckhand/run \\\n"
            f"  -H 'content-type: application/json' \\\n"
            f"  -d '{html.escape(_json.dumps(env['request']['body']))}'\n\n"
            f"# or run locally (deterministic):\n# {html.escape(env['invocation'])}</pre>"
        )
    else:
        verb = "GET"
        reqsnippet = f"<pre>curl -L {html.escape(report_url)}</pre>"
    howsteps = ""
    for step in env["how_to_run"]:
        label = {"telegram": "Telegram", "http": "HTTP", "cli": "CLI"}.get(step["via"], step["via"])
        howsteps += f"<li><b>{label}.</b> {html.escape(step['step'])}</li>"
    return _API_TEMPLATE.format(
        logo=_LOGO, title=html.escape(spec["title"]), std=html.escape(spec["std"]),
        verb=verb, reqsnippet=reqsnippet,
        envelope=html.escape(_json.dumps(env, indent=2)),
        id=spec["id"], note=html.escape(env["note"]), report_url=html.escape(report_url),
        prompt=html.escape(env["prompt"]), bot=_BOT, howsteps=howsteps,
    )


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
    ask = ""
    if spec["kind"] == "work":
        ask = ('<div style="margin-top:18px;padding:11px 14px;background:var(--soft);'
               'border:1px solid var(--line);border-radius:10px;font-size:12.5px">'
               f'<b>Ask Deckhand:</b> &ldquo;{html.escape(_prompt_for(spec))}&rdquo; '
               '&mdash; send to @the_deckhand_bot to run it live.</div>')
    return _TEMPLATE.format(
        logo=_LOGO, std=html.escape(spec["std"]), title=html.escape(spec["title"]),
        blurb=html.escape(spec["blurb"]), figs=figs, bullets=bullets, live=html.escape(live),
        ask=ask,
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
    import json as _json
    if not _CHROME:
        raise SystemExit("No Chrome found; set CHROME=/path/to/google-chrome")
    _OUT.mkdir(parents=True, exist_ok=True)
    api_dir = _REPO / "reports" / "capabilities" / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    ids = set()
    n_api = 0
    for spec in SPECS:
        assert spec["id"] not in ids, f"duplicate id {spec['id']}"
        ids.add(spec["id"])
        _to_pdf(_render_html(spec), _OUT / f"{spec['id']}.pdf")
        # API artifacts: one self-contained workflow-API call per live work.
        if spec["kind"] == "work":
            env = _api_envelope(spec)
            (api_dir / f"{spec['id']}.json").write_text(
                _json.dumps(env, indent=2) + "\n", encoding="utf-8")
            (api_dir / f"{spec['id']}.html").write_text(
                _render_api_html(spec, env), encoding="utf-8")
            n_api += 1
    print(f"Wrote {len(SPECS)} one-pager PDFs into {_OUT.relative_to(_REPO)}/ "
          f"and {n_api} API artifacts (.html+.json) into capabilities/api/")


if __name__ == "__main__":
    main()
