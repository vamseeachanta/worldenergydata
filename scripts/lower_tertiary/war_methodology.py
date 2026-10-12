"""One publication note for the legacy WAR-derived D&C surfaces."""

from html import escape

WAR_METHODOLOGY = """## WAR methodology limits

Weekly boundary quantization: 30 CFR 250.743(a) requires weekly WARs for the
region covered by that paragraph, Sunday (12 a.m.) through Saturday (11:59 p.m.).
Periods are no longer than seven days; first and last periods may be shorter.
When activity transitions are inferred only from weekly status rows, a per-well
count is quantized at each boundary by up to one reporting week. This is an
inference from the cadence, not a measured error bound on every report date;
daily narratives or more frequent reports can refine the boundaries.

Coverage floor: the bulk-file start date remains unconfirmed from the BSEE
Raw Data and eWell WAR Field Definitions pages examined here. Historical
completeness, including coverage of earlier paper reports, is not established.
Missing historical reports shall not be interpreted as zero days.

Depth basis: legacy Days/10K ratios use measured depth (MD), MAX_BH_TOTAL_MD,
minus water depth as drilled footage below the mudline, with the denominator
bounded below in the code. The learning-series ratios instead use true vertical
depth (TVD), MAX_WELL_BORE_TVD. MD and TVD are not interchangeable; these D&C
surfaces display counts and geometry and do not calculate a new dry-hole ratio.
Code locators: scripts/extract_all_well_data.py, the footage calculation;
packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/drilling_learning.py,
_clean; and bsee.analysis.drilling_intensity.DEPTH_COLUMNS.

Publisher-declared basis: no definition was found in the sources cited here
(30 CFR 250.743, BSEE Raw Data and eWell WAR Field Definitions). Existing figures
retain their legacy calendar and WAR-union arithmetic. The owner decision
ratifies activity-coded drilling days and completion-coded days only, with
suspended and temporarily abandoned time reported separately and excluded
from both. A comparison is required before that rule replaces published figures;
this note does not replace those figures or infer additional code meanings.
Decision: https://github.com/vamseeachanta/worldenergydata/issues/1064#issuecomment-6131101384

Sanity reference: the public publisher-deposited abstract of SPE-87117-MS,
Deepwater Success Through Predictable and Distinctive Drilling and Completion
Performance, paragraph 4, reports 20–23 days per 10,000 ft for its deepwater
examples. The abstract does not establish MD versus TVD or comparability to
the legacy figures here. The band is a plausibility reference, not an acceptance
threshold; no per-well ratio is reproduced or asserted by this note.
Record: https://api.crossref.org/works/10.2118/87117-MS

Sources examined 2026-10-12: eCFR, Office of the Federal Register, 30 CFR
250.743(a): https://www.ecfr.gov/current/title-30/chapter-II/subchapter-B/part-250/subpart-G/subject-group-ECFRa4d25de54b283e6/section-250.743
BSEE Raw Data, eWell Submissions WAR row: https://www.data.bsee.gov/Main/RawData.aspx
BSEE eWell WAR Online Query Field Definitions: https://www.data.bsee.gov/Well/eWellWAR/FieldDefinitions.aspx
"""


def methodology_html() -> str:
    """Render the same note without requiring site-builder dependencies."""
    heading, *paragraphs = WAR_METHODOLOGY.strip().split("\n\n")
    body = "".join(f"<p>{escape(p)}</p>" for p in paragraphs)
    return (
        '<section class="panel war-methodology"><h2>'
        + escape(heading.removeprefix("## "))
        + "</h2>"
        + body
        + "</section>"
    )
