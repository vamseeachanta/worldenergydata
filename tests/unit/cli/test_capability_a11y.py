"""Template baseline for the capability one-pager generator (wh#3401 / #908).

Static checks (no heavyweight imports, matching test_capability_drift.py style):
the PDF one-pager template must NOT carry screen-only a11y rules (focus rings are
meaningless in print), and the generator must not emit any chatbot/external-API
call artifacts -- the one-pagers point only at the published report surface.
"""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_GEN = _REPO / "scripts" / "capabilities" / "build_onepagers.py"
_API_DIR = _REPO / "reports" / "capabilities" / "api"


def _src() -> str:
    return _GEN.read_text(encoding="utf-8")


def _pdf_template() -> str:
    s = _src()
    start = s.index("_TEMPLATE = ")
    return s[start : s.index('"""', s.index('"""', start) + 3)]


def test_pdf_template_has_no_screen_only_a11y():
    # focus rings are meaningless in print — must not leak into the PDF template
    assert ":focus-visible" not in _pdf_template()


def test_generator_emits_no_external_api_artifacts():
    s = _src().lower()
    assert "deckhand" not in s
    assert "/api/run" not in s
    assert not _API_DIR.exists(), "reports/capabilities/api/ must not be regenerated"
