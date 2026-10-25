"""Reviewed correspondence must not publish email addresses."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
EMAIL = re.compile(r"[\w.+%-]+@[\w.-]+\.[A-Za-z]{2,}")


@pytest.mark.parametrize(
    "relative_path",
    [
        "docs/data-sources/bsee/analysis/field/field_layout.md",
        "docs/data-sources/bsee/data/drilling_data_rev1.md",
        "docs/data-sources/bsee/data/well/well_count.md",
    ],
)
def test_reviewed_correspondence_contains_no_email_addresses(relative_path):
    text = (ROOT / relative_path).read_text(encoding="utf-8")
    lines = [
        number for number, line in enumerate(text.splitlines(), 1) if EMAIL.search(line)
    ]
    assert not lines, f"Email addresses at {relative_path}, lines {lines}"
