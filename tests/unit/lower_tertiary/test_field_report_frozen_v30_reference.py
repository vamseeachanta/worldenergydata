"""Guard: per-field economics reports carry a SINGLE unlabelled result.

The economics reports collapsed from a frozen-V30/latest dual-column apparatus
to one unlabelled result (worldenergydata#982). These tests assert that the
published ``field_economics_<slug>.md`` reports keep a single-column NPV row and
never re-introduce version labels (frozen / V30 / V50 / sanctioned) or a second
NPV column in user-visible prose. V30/V50 survive only as INTERNAL validation
identifiers (config baselines, code selectors) — never in the reports.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
REPORTS_DIR = PROJECT_ROOT / "reports" / "lower_tertiary"

REPORTS = sorted(REPORTS_DIR.glob("field_economics_*.md"))

# Tokens that must never appear in a user-visible report. "V30"/"V50" are
# checked case-sensitively (upper-case) so they catch the removed labels without
# tripping on lower-case code identifiers, which are absent from the reports
# anyway; "frozen"/"sanctioned" are checked case-insensitively.
BANNED_CASE_SENSITIVE = ("V30", "V50", "reference NPV", "V50-KC recompute")
BANNED_CASE_INSENSITIVE = ("frozen", "sanctioned")

# Single-column NPV row, e.g. ``| **NPV @ 10%** | **$-482.8 M** |``.
_SINGLE_NPV_ROW = re.compile(r"\| \*\*NPV @ 10%\*\* \| \*\*\$[-0-9,]+\.[0-9] M\*\* \|")
# A dual-column NPV row would carry a second ``$`` value after the first cell.
_DUAL_NPV_ROW = re.compile(r"\| \*\*NPV @ 10%\*\* \|[^|]*\|[^|]*\$[^|]*\|")


def test_reports_present():
    assert REPORTS, "expected at least one field_economics_<slug>.md report"


@pytest.mark.parametrize("path", REPORTS, ids=lambda p: p.name)
def test_single_column_npv_row_present(path: Path):
    md = path.read_text(encoding="utf-8")
    assert _SINGLE_NPV_ROW.search(md), f"{path.name}: missing single-column NPV row"


@pytest.mark.parametrize("path", REPORTS, ids=lambda p: p.name)
def test_no_second_npv_column(path: Path):
    md = path.read_text(encoding="utf-8")
    assert not _DUAL_NPV_ROW.search(md), f"{path.name}: a second NPV column is present"


@pytest.mark.parametrize("path", REPORTS, ids=lambda p: p.name)
def test_no_version_labels(path: Path):
    md = path.read_text(encoding="utf-8")
    lower = md.lower()
    for token in BANNED_CASE_SENSITIVE:
        assert token not in md, f"{path.name}: banned label {token!r} present"
    for token in BANNED_CASE_INSENSITIVE:
        assert (
            token.lower() not in lower
        ), f"{path.name}: banned label {token!r} present"
