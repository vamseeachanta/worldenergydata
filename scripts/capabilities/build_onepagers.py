# ABOUTME: Generate self-contained capability HTML cards for the website.
# ABOUTME: One card per capability section and live work; no browser is required.
"""Build self-contained capability HTML cards.

Each card contains the worldenergydata logo, description, figures, deliverables
and report address. Cards remain in ``reports/capabilities/pdf/`` to preserve
published addresses; ``build_pages.py`` copies the folder, including retired
PDFs that remain tracked but are no longer generated, to the published tree.
The optional ``--brand CSS_FILE`` argument inlines a resource-free stylesheet
following the default styles.

Run:
    python scripts/capabilities/build_onepagers.py
"""

from __future__ import annotations

import argparse
import base64
import html
import re
import sys
from datetime import date
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
from scripts.marine_safety.report_notice import LINKED_REPORT_NOTICE, NOTICE_STYLE

_OUT = _REPO / "reports" / "capabilities" / "pdf"
_TOKENS = (_REPO / "reports" / "capabilities" / "assets" / "tokens.css").read_text(encoding="utf-8").strip()
_SITE = "https://vamseeachanta.github.io/worldenergydata"
_LOGO = """<svg viewBox="0 0 400 64" xmlns="http://www.w3.org/2000/svg" aria-label="worldenergydata">
  <g fill="none" stroke-width="3">
    <circle cx="32" cy="32" r="23" stroke="#0B3D91"/>
    <ellipse cx="32" cy="32" rx="9.5" ry="23" stroke="#2BB2A6" stroke-width="2.5"/>
    <line x1="9" y1="32" x2="55" y2="32" stroke="#2BB2A6" stroke-width="2.5"/>
    <line x1="13.5" y1="19" x2="50.5" y2="19" stroke="#0B3D91" stroke-width="2"/>
    <line x1="13.5" y1="45" x2="50.5" y2="45" stroke="#0B3D91" stroke-width="2"/>
  </g>
  <circle cx="32" cy="32" r="3" fill="#2BB2A6"/>
  <text x="74" y="43" font-family="Open Sans" font-size="31" font-weight="800" letter-spacing="-0.6">
    <tspan fill="#0B3D91">world</tspan><tspan fill="#2BB2A6">energy</tspan><tspan fill="#0B3D91">data</tspan>
  </text>
</svg>"""

# Editorial revision; independent of the print date.
REVISION_DATE = "2026-10-13"

# id, kind, title, source and data basis, live path, deliverable, figures, bullets.
SPECS: list[dict] = [{'id': 'sec-economics',
  'kind': 'section',
  'title': 'Field economics and production comparison',
  'std': 'Bureau of Safety and Environmental Enforcement Oil and Gas Operations Reports; United '
         'States Energy Information Administration oil prices · data as of: 2025-05 · pre-tax '
         'basis · Price: historical West Texas Intermediate monthly prices; cost: recorded '
         'drilling, completion, facilities and operating assumptions',
  'path': 'capabilities/#economics',
  'blurb': 'Life-to-date field, block and well cashflow for the selected deepwater Gulf of Mexico '
           'developments. The comparison covers recorded production and costs estimated from the '
           'stated assumptions, rather than a full-cycle forecast.',
  'figures': [['7', 'developments recorded as producing in the reference population']],
  'bullets': ['Net present value at a 10% annual discount rate and field cashflow timelines',
              'Oil-price sensitivity and field breakeven comparisons',
              'Well and block contributions, with shared costs allocated by production share']},
 {'id': 'economics-anchor',
  'kind': 'work',
  'title': 'Anchor field economics',
  'std': 'Bureau of Safety and Environmental Enforcement Oil and Gas Operations Reports; United '
         'States Energy Information Administration oil prices · data as of: 2025-05 · pre-tax '
         'basis · Price: historical West Texas Intermediate monthly prices; cost: recorded '
         'drilling, completion, facilities and operating assumptions',
  'path': 'economics-anchor.html',
  'blurb': 'The field record starts production in 2024-08. The reference population contains 2 '
           'producing wells and 15 total wellbores. Shared field costs are allocated by production '
           'share.',
  'figures': [],
  'bullets': ['Net present value at a 10% annual discount rate and field breakeven oil price',
              'Well and block cashflow contributions and production totals',
              'Cashflow timeline with drilling and completion activity context']},
 {'id': 'economics-big_foot',
  'kind': 'work',
  'title': 'Big Foot field economics',
  'std': 'Bureau of Safety and Environmental Enforcement Oil and Gas Operations Reports; United '
         'States Energy Information Administration oil prices · data as of: 2025-05 · pre-tax '
         'basis · Price: historical West Texas Intermediate monthly prices; cost: recorded '
         'drilling, completion, facilities and operating assumptions',
  'path': 'economics-big_foot.html',
  'blurb': 'A deepwater Gulf of Mexico field. The field record starts production in 2018-11. The '
           'reference population contains 7 producing wells and 38 total wellbores. Shared field '
           'costs are allocated by production share.',
  'figures': [],
  'bullets': ['Net present value at a 10% annual discount rate and field breakeven oil price',
              'Well and block cashflow contributions and production totals',
              'Cashflow timeline with drilling and completion activity context']},
 {'id': 'economics-cascade_chinook',
  'kind': 'work',
  'title': 'Cascade–Chinook field economics',
  'std': 'Bureau of Safety and Environmental Enforcement Oil and Gas Operations Reports; United '
         'States Energy Information Administration oil prices · data as of: 2025-05 · pre-tax '
         'basis · Price: historical West Texas Intermediate monthly prices; cost: recorded '
         'drilling, completion, facilities and operating assumptions',
  'path': 'economics-cascade_chinook.html',
  'blurb': 'The corrected field record starts production in 2012-09. The reference population '
           'contains 3 producing wells and 14 total wellbores. Shared field costs are allocated by '
           'production share.',
  'figures': [],
  'bullets': ['Net present value at a 10% annual discount rate and field breakeven oil price',
              'Well and block cashflow contributions and production totals',
              'Cashflow timeline with drilling and completion activity context']},
 {'id': 'economics-jack_st_malo',
  'kind': 'work',
  'title': 'Jack / St. Malo field economics',
  'std': 'Bureau of Safety and Environmental Enforcement Oil and Gas Operations Reports; United '
         'States Energy Information Administration oil prices · data as of: 2025-05 · pre-tax '
         'basis · Price: historical West Texas Intermediate monthly prices; cost: recorded '
         'drilling, completion, facilities and operating assumptions',
  'path': 'economics-jack_st_malo.html',
  'blurb': 'The field record starts production in 2014-12. The reference population contains 22 '
           'producing wells and 73 total wellbores. Shared field costs are allocated by production '
           'share.',
  'figures': [],
  'bullets': ['Net present value at a 10% annual discount rate and field breakeven oil price',
              'Well and block cashflow contributions and production totals',
              'Cashflow timeline with drilling and completion activity context']},
 {'id': 'economics-julia',
  'kind': 'work',
  'title': 'Julia field economics',
  'std': 'Bureau of Safety and Environmental Enforcement Oil and Gas Operations Reports; United '
         'States Energy Information Administration oil prices · data as of: 2025-05 · pre-tax '
         'basis · Price: historical West Texas Intermediate monthly prices; cost: recorded '
         'drilling, completion, facilities and operating assumptions',
  'path': 'economics-julia.html',
  'blurb': 'The field record starts production in 2016-03. The reference population contains 4 '
           'producing wells and 9 total wellbores. Shared field costs are allocated by production '
           'share.',
  'figures': [],
  'bullets': ['Net present value at a 10% annual discount rate and field breakeven oil price',
              'Well and block cashflow contributions and production totals',
              'Cashflow timeline with drilling and completion activity context']},
 {'id': 'economics-shenandoah',
  'kind': 'work',
  'title': 'Shenandoah field economics',
  'std': 'Bureau of Safety and Environmental Enforcement Oil and Gas Operations Reports; United '
         'States Energy Information Administration oil prices · data as of: 2025-05 · pre-tax '
         'basis · Price: historical West Texas Intermediate monthly prices; cost: recorded '
         'drilling, completion, facilities and operating assumptions',
  'path': 'economics-shenandoah.html',
  'blurb': 'First production is recorded in 2025-02. Through the stated cut-off the record '
           'contains early production from 1 producing well and 23 total wellbores. Economics are '
           'not yet evaluated on this page; the recorded return measure is absent.',
  'figures': [],
  'bullets': ['First recorded production month and reference window',
              'Producing-well and total-wellbore population',
              'Economics not yet evaluated for this early-production record']},
 {'id': 'economics-stones',
  'kind': 'work',
  'title': 'Stones field economics',
  'std': 'Bureau of Safety and Environmental Enforcement Oil and Gas Operations Reports; United '
         'States Energy Information Administration oil prices · data as of: 2025-05 · pre-tax '
         'basis · Price: historical West Texas Intermediate monthly prices; cost: recorded '
         'drilling, completion, facilities and operating assumptions',
  'path': 'economics-stones.html',
  'blurb': 'The field record starts production in 2016-09. The reference population contains 10 '
           'producing wells and 22 total wellbores. Shared field costs are allocated by production '
           'share.',
  'figures': [],
  'bullets': ['Net present value at a 10% annual discount rate and field breakeven oil price',
              'Well and block cashflow contributions and production totals',
              'Cashflow timeline with drilling and completion activity context']},
 {'id': 'portfolio',
  'kind': 'work',
  'title': 'Lower Tertiary economics portfolio',
  'std': 'Bureau of Safety and Environmental Enforcement Oil and Gas Operations Reports; United '
         'States Energy Information Administration oil prices · data as of: 2025-05 · pre-tax '
         'basis · Price: historical West Texas Intermediate monthly prices; cost: recorded '
         'drilling, completion, facilities and operating assumptions',
  'path': 'portfolio.html',
  'blurb': 'Field-level production and life-to-date cashflow are compared for the selected '
           'deepwater Gulf of Mexico reference population. Recorded producing status includes the '
           'early-production development; the count does not imply an evaluated return for each '
           'field.',
  'figures': [['7', 'developments recorded as producing in the reference population']],
  'bullets': ['Field and well production comparisons with source limitations',
              'Life-to-date cashflow and net present value at a 10% annual discount rate']},
 {'id': 'benchmark',
  'kind': 'work',
  'title': 'Lower Tertiary well production comparison',
  'std': 'Bureau of Safety and Environmental Enforcement Oil and Gas Operations Reports; United '
         'States Energy Information Administration oil prices · data as of: 2025-05 · pre-tax '
         'basis · Price: historical West Texas Intermediate monthly prices; cost: recorded '
         'drilling, completion, facilities and operating assumptions',
  'path': 'benchmark.html',
  'blurb': 'Well-level production contributions are compared within and between the selected '
           'fields, with recorded volumes distinguished from indicative cost allocations.',
  'figures': [],
  'bullets': ['Well production profiles and cumulative contributions',
              'Comparison of well and block contributions within each field',
              'Shared field costs allocated by production share; source limitations stated']},
 {'id': 'sec-wells',
  'kind': 'section',
  'title': 'Well operations and geometry',
  'std': 'Bureau of Safety and Environmental Enforcement Well Activity Reports · data as of: '
         '2025-08-03 (latest recorded completion activity in the reference workbook; acquisition '
         'cut-off not recorded)',
  'path': 'capabilities/#wells',
  'blurb': 'Well activity, depth and surveyed geometry provide context for the reference '
           'population. The twelve lease-name groups include separate Cascade and Chinook and Jack '
           'and St. Malo groups. Kaskida and Tiber are recorded as pre-final-investment-decision; '
           'North Platte is recorded as non-producing.',
  'figures': [['217', 'well records with a recorded well identifier'],
              ['12', 'lease-name groups in the reference population']],
  'bullets': ['Spud-to-total-depth drilling spans and total-depth-to-final-activity completion '
              'spans',
              'Well depth and water-depth context; maximum measured depth: 37,743 feet',
              'Julia survey trajectories linked to well identification and surface locations']},
 {'id': 'completion',
  'kind': 'work',
  'title': 'Drilling and completion durations',
  'std': 'Bureau of Safety and Environmental Enforcement Well Activity Reports · data as of: '
         '2025-08-03 (latest recorded completion activity in the reference workbook; acquisition '
         'cut-off not recorded)',
  'path': 'completion/',
  'blurb': 'Drilling and completion duration distributions are compared by lease group, '
           'distinguishing zero recorded spans from non-zero durations. The twelve lease-name '
           'groups include separate Cascade and Chinook and Jack and St. Malo groups. Kaskida and '
           'Tiber are recorded as pre-final-investment-decision; North Platte is recorded as '
           'non-producing.',
  'figures': [['217', 'well records with a recorded well identifier'],
              ['12', 'lease-name groups in the reference population']],
  'bullets': ['Drilling: median of 217 records, including 33 with zero recorded days: 38 days; '
              'median of 184 non-zero spans: 46.5 days',
              'Completion: median of 217 records, including 31 with zero recorded days: 24 days; '
              'median of 186 non-zero spans: 33 days',
              'Spud-to-total-depth and total-depth-to-final-activity spans; source limitations '
              'stated']},
 {'id': 'well-path',
  'kind': 'work',
  'title': 'Julia well survey geometry',
  'std': 'Bureau of Safety and Environmental Enforcement directional surveys and well metadata · '
         'data as of: 2026-02-11 (survey-file vintage in the manifest); well-metadata file '
         'vintage: 2025-07-31; source acquisition cut-off not recorded',
  'path': 'well-path.html',
  'blurb': 'Three-dimensional Julia well trajectories reconstructed from survey stations and '
           'referenced to surface well locations.',
  'figures': [],
  'bullets': ['Northing, easting and depth along surveyed boreholes',
              'Well identification and surface-location context']},
 {'id': 'sec-playbook',
  'kind': 'section',
  'title': 'Offshore development concept comparison',
  'std': 'SubseaIQ commercial offshore-field catalogue; Bureau of Safety and Environmental '
         'Enforcement asset records · data as of: 2014 (approximate catalogue baseline; '
         'acquisition cut-off not recorded) · pre-tax basis · Price: supplied field oil-price '
         'inputs; cost: development-system assumptions and qualitative concept adjustments',
  'path': 'capabilities/#playbook',
  'blurb': 'Early concept comparison from field parameters, with subsea arrangements and '
           'indicative economics. This is a concept-stage assessment rather than a detailed '
           'development design.',
  'figures': [['333', 'Gulf of Mexico fields in the catalogue'],
              ['115', 'fields matched to regulator lease blocks']],
  'bullets': ['Development concept screening from depth, reserves and tieback distance',
              'Subsea arrangements and equipment geometry',
              'Comparison with recorded development concepts where matched']},
 {'id': 'fd-showcase',
  'kind': 'work',
  'title': 'Offshore development concept examples',
  'std': 'SubseaIQ commercial offshore-field catalogue; Bureau of Safety and Environmental '
         'Enforcement asset records · data as of: 2014 (approximate catalogue baseline; '
         'acquisition cut-off not recorded) · pre-tax basis · Price: supplied field oil-price '
         'inputs; cost: development-system assumptions and qualitative concept adjustments',
  'path': 'field-development/showcase.html',
  'blurb': 'Selected offshore-field examples illustrate concept screening, subsea arrangements and '
           'indicative economics.',
  'figures': [],
  'bullets': ['Field parameters and screened development concepts',
              'Subsea arrangements for the selected examples']},
 {'id': 'fd-playbook',
  'kind': 'work',
  'title': 'Development concept sensitivity',
  'std': 'SubseaIQ commercial offshore-field catalogue; Bureau of Safety and Environmental '
         'Enforcement asset records · data as of: 2014 (approximate catalogue baseline; '
         'acquisition cut-off not recorded)',
  'path': 'field-development/playbook.html',
  'blurb': 'Development concepts and subsea arrangements are compared as water depth, reserves and '
           'tieback distance vary.',
  'figures': [],
  'bullets': ['Concept response to changes in field parameters',
              'Subsea layout response to tieback-distance and water-depth changes']},
 {'id': 'fd-portfolio',
  'kind': 'work',
  'title': 'Gulf of Mexico concept portfolio',
  'std': 'SubseaIQ commercial offshore-field catalogue; Bureau of Safety and Environmental '
         'Enforcement asset records · data as of: 2014 (approximate catalogue baseline; '
         'acquisition cut-off not recorded)',
  'path': 'field-development/portfolio/',
  'blurb': 'Concept-stage development assessments for the selected deepwater Gulf of Mexico '
           'fields.',
  'figures': [['10', 'field profiles in the selected portfolio']],
  'bullets': ['Per-field development concepts and subsea arrangements',
              'Equipment geometry and field-parameter context']},
 {'id': 'fd-bsee-matched',
  'kind': 'work',
  'title': 'Matched offshore development concepts',
  'std': 'SubseaIQ commercial offshore-field catalogue; Bureau of Safety and Environmental '
         'Enforcement asset records · data as of: 2014 (approximate catalogue baseline; '
         'acquisition cut-off not recorded)',
  'path': 'field-development/bsee-matched/',
  'blurb': '333 Gulf of Mexico fields in the catalogue; 115 matched to regulator lease blocks. '
           'Screened concepts are compared with recorded as-built concepts for the matched fields.',
  'figures': [['115', 'Gulf of Mexico fields matched to regulator lease blocks']],
  'bullets': ['Recorded and screened development concepts side by side',
              'Subsea arrangements and source matching context']},
 {'id': 'ms-exec',
  'kind': 'work',
  'title': 'Marine casualty overview',
  'std': 'Transportation Safety Board of Canada marine occurrences; United States Coast Guard '
         '1995–2012 recreational boating accident reports, distributed by Data Liberation Project; '
         'International Maritime Organization Global Integrated Shipping Information System · data '
         'as of: 2025-10-11 (Organization records collated); other source cut-offs not recorded',
  'path': 'marine_safety/executive_summary.html',
  'blurb': LINKED_REPORT_NOTICE + '\n\n' + (
      'An overview of the combined casualty records, with source coverage and links to '
      'the detailed incident analyses.'),
  'figures': [],
  'bullets': ['Incident and fatality distributions by source and category',
              'Links to fatality, foundering and hatch-incident analyses']},
 {'id': 'ms-fatality',
  'kind': 'work',
  'title': 'Marine fatality analysis',
  'std': 'Transportation Safety Board of Canada marine occurrences; United States Coast Guard '
         '1995–2012 recreational boating accident reports, distributed by Data Liberation Project '
         '· data as of: 2012 (Coast Guard record coverage end); Canadian acquisition cut-off not '
         'recorded',
  'path': 'marine_safety/fatality_analysis.html',
  'blurb': LINKED_REPORT_NOTICE + '\n\n' + (
      'Fatal incidents are grouped by recorded cause and category, with reported '
      'fatalities distinguished from incident counts.'),
  'figures': [],
  'bullets': ['Ranked causes among fatal incidents',
              'Incident-category counts and recorded fatality distributions']},
 {'id': 'ms-foundering',
  'kind': 'work',
  'title': 'Vessel foundering analysis',
  'std': 'Transportation Safety Board of Canada marine occurrences; United States Coast Guard '
         '1995–2012 recreational boating accident reports, distributed by Data Liberation Project; '
         'International Maritime Organization Global Integrated Shipping Information System · data '
         'as of: 2025-10-11 (Organization records collated); other source cut-offs not recorded',
  'path': 'marine_safety/foundering_analysis.html',
  'blurb': LINKED_REPORT_NOTICE + '\n\n' + (
      'Foundering incidents are grouped to examine reported fatalities and recurring '
      'incident patterns. Imported International Maritime Organization records contain no '
      'fatality counts; those counts use the Canadian and Coast Guard records.'),
  'figures': [],
  'bullets': ['Recorded fatalities per foundering incident',
              'Cause and incident-pattern distributions']},
 {'id': 'ms-hatch',
  'kind': 'work',
  'title': 'Hatch and opening incidents',
  'std': 'Transportation Safety Board of Canada marine occurrences; United States Coast Guard '
         '1995–2012 recreational boating accident reports, distributed by Data Liberation Project; '
         'International Maritime Organization Global Integrated Shipping Information System · data '
         'as of: 2025-10-11 (Organization records collated); other source cut-offs not recorded',
  'path': 'marine_safety/hatch_analysis.html',
  'blurb': LINKED_REPORT_NOTICE + '\n\n' + (
      'Incident narratives are screened for hatch, door and opening maloperation, then '
      'grouped by recorded severity.'),
  'figures': [],
  'bullets': ['Severity distribution of identified incidents',
              'Incident descriptions and source context for review']},
 {'id': 'sec-safety',
  'kind': 'section',
  'title': 'Offshore and marine incident assessment',
  'std': 'Transportation Safety Board of Canada marine occurrences; United States Coast Guard '
         '1995–2012 recreational boating accident reports, distributed by Data Liberation Project; '
         'International Maritime Organization Global Integrated Shipping Information System · data '
         'as of: 2025-10-11 (Organization records collated); other source cut-offs not recorded; '
         'Bureau of Safety and Environmental Enforcement incident corpus latest recorded incident: '
         '2026-01-08',
  'path': 'capabilities/#safety',
  'blurb': 'Marine casualty and offshore incident records support cause analysis and engineering '
           'screening. Source populations and missing information limit comparisons.',
  'figures': [],
  'bullets': ['Fatality, foundering and hatch-incident distributions',
              'Casualty severity, vessel-type and flag-state comparisons',
              'Mooring fatigue screening with illustrative loading and recorded failure context']},
 {'id': 'imo',
  'kind': 'work',
  'title': 'International marine casualty analysis',
  'std': 'International Maritime Organization Global Integrated Shipping Information System · data '
         'as of: 2025-10-11 (collation date); latest export window ends 2025-10-10',
  'path': 'IMO_GISIS_Executive_Report.html',
  'blurb': LINKED_REPORT_NOTICE + '\n\n' + (
      'Marine casualty records are grouped by severity, vessel type and flag state. '
      'Recorded occurrences span 1900-01-01 to 2025-06-09.'),
  'figures': [],
  'bullets': ['Severity and vessel-type distributions',
              'Flag-state comparisons and occurrence-year trends']},
 {'id': 'mooring',
  'kind': 'work',
  'title': 'Mooring fatigue life check',
  'std': 'Bureau of Safety and Environmental Enforcement incident records; DNV-RP-C203 S-N curve '
         'D, seawater with cathodic protection (edition not recorded in linked report); Vicinay '
         'component catalogue · data as of: 2026-01-08 (latest recorded incident in the corpus)',
  'path': 'hse/mooring-fatigue-grounded-card.html',
  'blurb': 'Mooring fatigue screening compares calculated life with the design basis under an '
           'illustrative tension spectrum. The component catalogue contains no cyclic load '
           'history; project-specific loading is required for acceptance.',
  'figures': [],
  'bullets': ['Governing component life, design fatigue factor and design-life comparison',
              'Recorded mooring failure incidents for engineering context',
              'Loading and component assumptions stated beside the result']},
 {'id': 'sec-validation',
  'kind': 'section',
  'title': 'Analysis sources and limitations',
  'std': 'Bureau of Safety and Environmental Enforcement production and activity records; FDAS V30 '
         'Financial Project Summary · data as of: 2026-01-30 (reference extraction); production '
         'through 2025-05',
  'path': 'capabilities/#validation',
  'blurb': 'Source records, analysis assumptions and reference comparisons are presented with the '
           'reported results so their basis and limitations can be examined.',
  'figures': [],
  'bullets': ['Production and economic inputs identified alongside results',
              'Economics checked against the FDAS V30 Financial Project Summary',
              'Missing inputs and indicative cost allocations identified']}]

_FONT_DIR = _REPO / "reports/capabilities/assets/fonts/OpenSans"
_FONT_CSS = "".join(
    '@font-face{font-family:"Open Sans";font-style:normal;'
    f'font-weight:{weight};src:url(data:font/ttf;base64,'
    + base64.b64encode((_FONT_DIR / f"OpenSans-{name}.ttf").read_bytes()).decode("ascii")
    + ') format("truetype")}'
    for weight, name in ((400, "Regular"), (700, "Bold"), (800, "ExtraBold"))
)

_TEMPLATE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{title}</title>
<style>
{notice_style}
  @page{{size:A4;margin:0}}
  {tokens}
  {font_css}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:"Open Sans";color:var(--ink);background:#fff;
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
</style>{brand_style}</head>
<body>
  <div class="top">{logo}<div class="kind">Capability summary</div></div>
  <div class="std">{std}</div>
  <h1>{title}</h1>
  <p class="{blurb_class}">{blurb}</p>
{figs}<h2>What you get</h2>
  <ul>{bullets}</ul>
  <div class="foot">
    <div>worldenergydata · Analysis basis and limitations stated above · Revision: {revision_date}<br>
      <a class="live" href="{live}">Explore live</a></div>
  </div>
</body></html>"""


def _render_html(spec: dict, brand_css: str = "") -> str:
    _validate_spec(spec)
    _validate_brand(brand_css)
    figs = ""
    if spec["figures"]:
        cells = "".join(
            f'<div class="fig"><div class="v">{html.escape(v)}</div>'
            f'<div class="l">{html.escape(l)}</div></div>'
            for v, l in spec["figures"]
        )
        figs = f'  <div class="figs">{cells}</div>\n'
    bullets = "".join(f"<li>{html.escape(b)}</li>" for b in spec["bullets"])
    live = f"{_SITE}/{spec['path']}"
    return _TEMPLATE.format(
        notice_style=NOTICE_STYLE,
        tokens=_TOKENS,
        font_css=_FONT_CSS,
        revision_date=REVISION_DATE,
        brand_style=f"<style>{brand_css}</style>" if brand_css else "",
        logo=_LOGO,
        std=html.escape(spec["std"]),
        title=html.escape(spec["title"]),
        blurb_class="blurb unverified" if spec["blurb"].startswith(LINKED_REPORT_NOTICE) else "blurb",
        blurb='</p>\n  <p class="blurb">'.join(
            html.escape(paragraph) for paragraph in spec["blurb"].split("\n\n")
        ),
        figs=figs,
        bullets=bullets,
        live=html.escape(live),
    )


def _validate_spec(spec: dict) -> None:
    """Check the editorial contract before rendering or creating output paths."""
    page = spec["id"]
    if not spec["title"].strip():
        raise ValueError(f"{page}: title must identify the engineering deliverable")

    # Issue #1199, editorial requirements 5 and 12: preserve recorded date
    # precision, allow explicitly absent cut-offs, and print a fixed revision day.
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", REVISION_DATE):
        raise ValueError("revision must be a calendar date in year-month-day form")
    try:
        date.fromisoformat(REVISION_DATE)
    except ValueError as error:
        raise ValueError("revision must be a valid calendar day") from error

    basis = spec["std"]
    source, separator, cutoff = basis.partition(" · data as of: ")
    recorded = re.match(
        r"(not recorded|[0-9]{4}(?:-[0-9]{2}){0,2})(?=$|[ ;·(])", cutoff
    )
    if (
        not separator
        or not source.strip(" ·\t\r\n")
        or basis.count("data as of:") != 1
        or recorded is None
    ):
        raise ValueError(f"{page}: basis requires a source and explicit data cut-off")
    value = recorded.group(1)
    if value != "not recorded":
        # Missing month/day are used only to check the Gregorian calendar;
        # the supplied basis is printed unchanged, without invented precision.
        calendar_day = (value + "-01-01")[:10]
        try:
            date.fromisoformat(calendar_day)
        except ValueError as error:
            raise ValueError(f"{page}: basis contains an invalid calendar date") from error

    # Issue #1199, requirement 5; these are the existing economics-bearing pages
    # identified by test_economic_pages_state_price_and_cost_basis.
    economic_pages = {
        "sec-economics", "portfolio", "benchmark", "sec-playbook", "fd-showcase"
    }
    if (page in economic_pages or page.startswith("economics-")) and not all(
        re.search(rf"\b{label}:\s*\w", basis) for label in ("Price", "cost")
    ):
        raise ValueError(f"{page}: economics basis requires price and cost assumptions")


def _validate_specs(specs: list[dict]) -> None:
    """Preflight the complete set so invalid later pages cannot leave partial output."""
    ids: set[str] = set()
    titles: set[str] = set()
    for spec in specs:
        _validate_spec(spec)
        page = spec["id"]
        title = " ".join(spec["title"].split()).casefold()
        if page in ids:
            raise ValueError(f"{page}: duplicate page id")
        if title in titles:
            raise ValueError(f"{page}: duplicate page title")
        ids.add(page)
        titles.add(title)


def _validate_brand(css: str) -> None:
    # CSS escapes can hide imports and resource functions from literal checks.
    resources = r"@import\b|(?:url|image|(?:-webkit-)?image-set|src)\s*\(|</style"
    if "\\" in css or re.search(resources, css, re.IGNORECASE):
        raise ValueError(
            "brand stylesheet must be self-contained CSS without resources or markup"
        )


def build_onepager(
    spec: dict,
    out_dir: Path,
    *,
    brand_css: str = "",
) -> Path:
    """Write the self-contained HTML card at its retained address."""
    text = _render_html(spec, brand_css)
    out_dir.mkdir(parents=True, exist_ok=True)
    source = out_dir / f"{spec['id']}.html"
    source.write_text(text + "\n", encoding="utf-8")
    return source


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Build capability HTML cards."
    )
    parser.add_argument(
        "--brand",
        type=Path,
        metavar="CSS_FILE",
        help="Inline a stylesheet after the default styles (no external resources).",
    )
    args = parser.parse_args(argv)
    brand_css = ""
    if args.brand is not None:
        try:
            brand_css = args.brand.read_text(encoding="utf-8")
            _validate_brand(brand_css)
        except (OSError, UnicodeError, ValueError) as error:
            parser.error(f"cannot read brand stylesheet: {error}")
    try:
        _validate_specs(SPECS)
    except ValueError as error:
        parser.error(str(error))
    for spec in SPECS:
        build_onepager(spec, _OUT, brand_css=brand_css)
    print(
        f"Wrote {len(SPECS)} capability HTML cards into {_OUT.relative_to(_REPO)}/"
    )


if __name__ == "__main__":
    main()
