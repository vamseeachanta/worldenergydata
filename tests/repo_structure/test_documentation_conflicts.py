"""Keep the repaired reporting standards and specification guide conflict-free."""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MARKER_LINE = re.compile(rb"(?:<{7}|={7}|>{7})(?:[ \t].*)?")


@pytest.mark.parametrize(
    "relative_path",
    [
        "docs/HTML_REPORTING_STANDARDS.md",
        "docs/modules/agent-os/enhanced-create-specs-user-guide.md",
    ],
)
def test_documentation_has_no_unresolved_conflict_lines(relative_path):
    lines = (REPO_ROOT / relative_path).read_bytes().splitlines()
    conflicts = [
        number
        for number, line in enumerate(lines, start=1)
        if MARKER_LINE.fullmatch(line)
    ]
    assert not conflicts, f"{relative_path}: unresolved marker lines {conflicts}"
