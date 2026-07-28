"""Gates for the committed D&C QA/QC report hub (wo-april-2026-qaqc-hub.html).

The hub is the report-set entry point and the reference implementation of the
self-contained report-hub design (evidence badges, tiered cards, guided path).
These pins keep it self-contained and keep its numbers tied to the matrix.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HUB = REPO / "reports" / "lower_tertiary" / "wo-april-2026-qaqc-hub.html"


def _text() -> str:
    return HUB.read_text(encoding="utf-8")


def test_hub_exists_and_is_a_full_document():
    text = _text()
    assert text.lstrip().lower().startswith("<!doctype html>")
    assert "</html>" in text
    assert "<title>D&C Days QA/QC — Report Hub</title>" in text


def test_hub_is_self_contained():
    """No external stylesheets, scripts, fonts, or images — CSS/SVG inline only."""
    text = _text()
    assert "<link" not in text
    assert "<script" not in text
    assert "<img" not in text
    assert "@import" not in text
    assert "fonts.googleapis" not in text


def test_external_hrefs_are_github_only():
    text = _text()
    for url in re.findall(r'href="(https?://[^"]+)"', text):
        assert url.startswith("https://github.com/vamseeachanta/worldenergydata"), url


def test_relative_links_point_at_published_pages():
    text = _text()
    rel = {
        u for u in re.findall(r'href="([^"#][^":]*)"', text) if not u.startswith("http")
    }
    expected = {
        "index.html",
        "wo-april-2026-validation.html",
        "wo-april-2026-per-well-dc.html",
        "roy-rig-days-validation.html",
        "fdas-revision-comparison.html",
        "completion/verification.html",
    }
    assert rel == expected, rel


def test_hub_carries_matrix_numbers():
    text = _text()
    for needle in (
        "253 bores · 11 developments",
        "25,404 D&amp;C days",
        "211 bores · 21,944 days",
        "+119",
        "0<small>/253</small>",
        "completion-boundary rule (#846) open",
    ):
        assert needle in text, needle


def test_hub_has_both_theme_definitions():
    text = _text()
    assert "@media (prefers-color-scheme: dark)" in text
    assert ':root[data-theme="dark"]' in text
    assert ':root[data-theme="light"]' in text
