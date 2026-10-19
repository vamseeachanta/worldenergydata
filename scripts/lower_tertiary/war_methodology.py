"""One publication note for the legacy WAR-derived D&C surfaces."""

from html import escape

# Publication revision for the duration pages extended by issue #1078.
WAR_REVISION_HTML = """<section class="war-revision"><h2>Revision history</h2>
<table><thead><tr><th>Revision</th><th>Date</th><th>Change and reason</th></tr></thead>
<tbody><tr><td>1</td><td>2026-10-19</td><td>Added the sourced WAR methodology
limits so day counts carry their coverage, boundary and basis caveats.
Published numerical results are retained.</td></tr></tbody></table></section>"""

WAR_METHODOLOGY = """## WAR methodology limits

Weekly boundary quantization: 30 CFR 250.743(a) requires weekly WARs for the
region covered by that paragraph, Sunday (12 a.m.) through Saturday (11:59 p.m.).
Periods are no longer than seven days; first and last periods may be shorter.
When activity transitions are inferred only from weekly status rows, a per-well
count is quantized at each boundary by up to one reporting week. This is an
inference from the cadence, not a measured error bound on every report date;
daily narratives or more frequent reports can refine the boundaries.

Coverage floor: the repository records reports submitted since April 2004
(Makefile, comment above the data target, attributed to issue 1066). This is
reported, not confirmed from an agency page; the bulk-file start date remains
unconfirmed from the BSEE Raw Data and eWell WAR Field Definitions pages
examined here. Historical completeness, including coverage of earlier paper
reports, is not established. Missing historical reports shall not be
interpreted as zero days.

Depth basis: legacy Days/10K ratios are per 10,000 ft and use measured depth (MD), MAX_BH_TOTAL_MD,
minus water depth as drilled footage below the mudline, with the denominator
bounded below in the code. The learning-series ratios are per 1,000 ft and instead use true vertical
depth (TVD), MAX_WELL_BORE_TVD. MD and TVD are not interchangeable; these D&C
surfaces display counts and geometry and do not calculate a new dry-hole ratio.
Code locators: scripts/extract_all_well_data.py, the footage calculation;
packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/drilling_learning.py,
_clean; and bsee.analysis.drilling_intensity.DEPTH_COLUMNS.

Publisher-declared basis: no definition was found in the sources cited here
(30 CFR 250.743, BSEE Raw Data and eWell WAR Field Definitions). Existing figures
retain their legacy calendar and WAR-union arithmetic. Milestone basis is the
default: drilling days = total-depth date minus spud date; completion days =
every reported day from total depth onward, all activity codes, with unreported
gaps left out. The activity-code breakdown, milestone basis and interim rule
are retained side by side, including suspended and temporarily abandoned time
kept separate in the activity-code breakdown and combined figures derived from
the granular ones. The decision requires confirmation across the wider well
population once the weekly records are obtained, before any published figure
is replaced. This note replaces no figure and infers no additional code meanings.
Decision: repository issue 1064#issuecomment-6132640847

Sanity reference: the public publisher-deposited abstract of SPE-87117-MS,
Deepwater Success Through Predictable and Distinctive Drilling and Completion
Performance, paragraph 4, reports 20–23 days per 10,000 ft for its deepwater
examples. The abstract does not establish MD versus TVD or comparability to
the legacy figures here. The band is a plausibility reference, not an acceptance
threshold; no per-well ratio is reproduced or asserted by this note.
Record: https://api.crossref.org/works/10.2118/87117-MS

Sources examined 2026-10-12:

- eCFR, Office of the Federal Register, 30 CFR 250.743(a): \
https://www.ecfr.gov/current/title-30/chapter-II/subchapter-B/part-250/subpart-G/\
subject-group-ECFRa4d25de54b283e6/section-250.743
- BSEE Raw Data, eWell Submissions WAR row: https://www.data.bsee.gov/Main/RawData.aspx
- BSEE eWell WAR Online Query Field Definitions: \
https://www.data.bsee.gov/Well/eWellWAR/FieldDefinitions.aspx
"""


def methodology_html() -> str:
    """Render the same note without requiring site-builder dependencies."""
    heading, *paragraphs = WAR_METHODOLOGY.strip().split("\n\n")
    blocks = []
    for paragraph in paragraphs:
        if paragraph.startswith("- "):
            items = "".join(
                f"<li>{escape(line.removeprefix('- '))}</li>"
                for line in paragraph.splitlines()
            )
            blocks.append(f"<ul>{items}</ul>")
        else:
            blocks.append(f"<p>{escape(paragraph)}</p>")
    body = "".join(blocks)
    return (
        '<section class="panel war-methodology"><h2>'
        + escape(heading.removeprefix("## "))
        + "</h2>"
        + body
        + "</section>"
    )
