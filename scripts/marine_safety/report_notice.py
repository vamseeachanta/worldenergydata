"""Dependency-free notices for reports without repository-backed agreement tests."""

UNVERIFIED_NOTICE = (
    "Figures on this page could not be re-derived from data held in this "
    "repository; treat as unverified."
)
# The committed record-count page has no producer in either detail writer.
HATCH_RECORD_NOTICE = (
    "The assessment-class and annual charts count records analysed by assessment "
    "class and year, respectively, not detected hatch incidents."
)
HATCH_RECORD_TITLES = (
    "Records Analysed by Assessment Class (Top Categories)",
    "Records Analysed per Year (Last 10 Years)",
)
LINKED_REPORT_NOTICE = UNVERIFIED_NOTICE.replace("on this page", "in the linked report")
NOTICE_STYLE = '        .unverified { font-weight: 400; opacity: 0.75; }\n        .header p.unverified { font-weight: 400; opacity: 0.75; font-size: 0.95em; }'
VERIFIED_PAGES = ()


def unverified_notice(page_name: str) -> str:
    """Mark reports unless repository-backed agreement tests cover the page."""
    if page_name in VERIFIED_PAGES:
        return ""
    return f'<p class="unverified">{UNVERIFIED_NOTICE}</p>'
