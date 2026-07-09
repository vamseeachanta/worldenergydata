"""Brand/a11y baseline for generated capability API pages (wh#3401 / #908).

Static checks (no heavyweight imports, matching test_capability_drift.py style):
the interactive API template must carry the accessibility baseline and route its
logo home; the PDF one-pager template must NOT (focus rings are screen-only).
Generated api/*.html must reflect the template.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]
_GEN = _REPO / "scripts" / "capabilities" / "build_onepagers.py"
_API_DIR = _REPO / "reports" / "capabilities" / "api"


def _src() -> str:
    return _GEN.read_text(encoding="utf-8")


def _api_template() -> str:
    s = _src()
    start = s.index("_API_TEMPLATE")
    return s[start : s.index('"""', s.index('"""', start) + 3)]


def _pdf_template() -> str:
    s = _src()
    start = s.index("_TEMPLATE = ")
    return s[start : s.index('"""', s.index('"""', start) + 3)]


def test_api_template_has_focus_visible():
    assert ":focus-visible" in _api_template()


def test_api_template_has_sr_only():
    assert ".sr-only" in _api_template()


def test_api_template_logo_links_home():
    # logo wrapped in an anchor to the capabilities index (../ from api/)
    assert re.search(r'<a href="\.\./"[^>]*>\{logo\}</a>', _api_template())


def test_pdf_template_has_no_screen_only_a11y():
    # focus rings are meaningless in print — must not leak into the PDF template
    assert ":focus-visible" not in _pdf_template()


@pytest.mark.skipif(not _API_DIR.exists(), reason="api artifacts not generated")
@pytest.mark.parametrize("page", sorted(_API_DIR.glob("*.html")))
def test_generated_api_pages_carry_baseline(page: Path):
    html = page.read_text(encoding="utf-8")
    assert ":focus-visible" in html, f"{page.name} missing focus-visible"
    assert 'href="../"' in html, f"{page.name} missing logo-home link"
