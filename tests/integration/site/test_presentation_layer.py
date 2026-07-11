# ABOUTME: Client-presentation-layer gate (issue #945) — builds the public site
# ABOUTME: in-process and pins provenance footers, the guided-demo band, the
# ABOUTME: page-level data-sources footer, the dual country-scope numbers, and
# ABOUTME: the branding pass.

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def public(tmp_path_factory):
    """Build the whole site in-process (same seam as test_public_link_graph)."""
    spec = importlib.util.spec_from_file_location(
        "build_pages_presentation", REPO / "scripts" / "build_pages.py"
    )
    bp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bp)
    out = tmp_path_factory.mktemp("public_presentation") / "public"
    bp.PUBLIC = out
    bp.ASSETS = out / "assets"
    bp.build()
    return out


# --- Sub-feature 1: provenance footers + page-level data-sources footer -------


def test_xprov_line_appears_three_times(public):
    # field panel (renderField) + wells panel (renderWells) + well panel
    # (renderWell) each emit exactly one citation line.
    text = (public / "field-atlas/index.html").read_text()
    assert text.count('class="xprov"') == 3


def test_page_level_footer_present(public):
    text = (public / "field-atlas/index.html").read_text()
    assert 'class="pgfoot"' in text
    assert "Data &amp; provenance" in text
    assert "data.bsee.gov" in text
    # contributions link into the repo issues
    assert "github.com/vamseeachanta/worldenergydata/issues" in text


def test_footer_has_no_snake_case_or_null_leak(public):
    # QA lesson: hand-written copy only — no interpolated payload keys.
    import re

    text = (public / "field-atlas/index.html").read_text()
    # isolate the footer block for the copy check
    start = text.index('class="pgfoot"')
    end = text.index("</footer>", start)
    footer = text[start:end]
    assert "null" not in footer
    # no snake_case payload identifiers (e.g. jack_st_malo, first_oil) in copy
    assert re.search(r"[a-z]+_[a-z]+", footer) is None


# --- Sub-feature 2: guided-demo default path ---------------------------------


def test_guided_demo_band_present(public):
    text = (public / "field-atlas/index.html").read_text()
    assert 'class="guide"' in text


def test_guided_demo_four_fragment_hrefs(public):
    text = (public / "field-atlas/index.html").read_text()
    for href in (
        'href="#"',
        'href="#/field/jack_st_malo"',
        'href="#/field/jack_st_malo/wells"',
        'href="#/field/jack_st_malo/wells/PN002"',
    ):
        assert href in text, href


# --- single-<h1> gate must still hold after footer + band --------------------


def test_atlas_still_single_h1(public):
    text = (public / "field-atlas/index.html").read_text()
    assert text.count("<h1") == 1


# --- Sub-feature 3: dual country-scope numbers on all three surfaces ----------

DUAL_SURFACES = (
    "capabilities/index.html",
    "capabilities/insights.html",
    "all-regions-atlas.html",
)


def test_dual_country_numbers_on_all_three_surfaces(public):
    for rel in DUAL_SURFACES:
        text = (public / rel).read_text()
        assert "205 countries in atlas scope" in text, rel
        assert "84 with offshore-field data" in text, rel


def test_capabilities_hero_repointed(public):
    text = (public / "capabilities/index.html").read_text()
    # stale count dropped; explorer framing added; link unchanged
    assert "120 GoM fields" not in text
    assert 'href="../field-atlas/"' in text
    assert "Field Explorer" in text


# --- Sub-feature 4: branding pass --------------------------------------------


def test_no_ace_branding_on_client_surface(public):
    for rel in (
        "field-atlas/index.html",
        "capabilities/index.html",
        "capabilities/insights.html",
        "all-regions-atlas.html",
    ):
        text = (public / rel).read_text()
        assert "A&CE" not in text, rel
        assert "A&amp;CE" not in text, rel
