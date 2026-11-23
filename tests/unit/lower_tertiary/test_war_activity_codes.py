"""Pins for the WAR activity-code definitions page (war-activity-codes.html).

The page is meant to be sent to somebody who has never seen this repository,
and its entire value is that a reader can tell, at a glance and without
context, which of three things they are looking at: something BSEE published,
something we inferred, or something nobody knows.

One failure mode destroys that outright -- an undocumented code acquiring a
meaning.  It is not hypothetical: ``PND | PENDING/UNKNOWN`` was mirrored into
this repository's config with the uncertainty note stripped off, and the
downstream reader had no way to know it was a guess (#1065).  The pin below,
``test_no_unknown_code_renders_a_meaning``, is the one that must never be
relaxed.  The others keep the page self-contained, followable to source, and
byte-regenerable from its generator.
"""

import importlib.util
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "lower_tertiary" / "build_war_activity_codes.py"
PAGE = REPO / "reports" / "lower_tertiary" / "war-activity-codes.html"
FREQ = REPO / "reports" / "lower_tertiary" / "data" / "war_activity_code_frequency.csv"

#: The only thing an undocumented code may show where a meaning would go.
EMPTY_MEANING = (
    '<span class="badge hold"><span class="d"></span>no meaning published</span>'
    '<span class="never">nothing published &mdash; nothing shown</span>'
)

#: Six codes BSEE publishes nothing for, plus the blank-code row.
UNKNOWN_CODES = {"WO", "CHZ", "PND", "MPF", "REC", "TBK"}
#: Six tokens BSEE publishes for BOREHOLE_STAT_CD and we *infer* are reused.
INFERRED_CODES = {"DRL", "COM", "TA", "PA", "ST", "DSI"}

#: Hosts the page is allowed to link to.  Anything else is either an invented
#: citation or a dependency on a third party we have not vetted.
ALLOWED_HOSTS = (
    "https://github.com/vamseeachanta/worldenergydata",
    "https://www.data.bsee.gov/",
    "https://www.bsee.gov/",
    "https://www.ecfr.gov/",
    "https://onrr.gov/",
)

ROW_RE = re.compile(r'<tr class="(t-unk|t-inf)">(.*?)</tr>', re.S)
MEANING_RE = re.compile(r'<td class="meaning">(.*?)</td>', re.S)
CODE_RE = re.compile(r'<td class="code">(?:<code>|<em>)([^<]+)')
#: The inference box carries no nested <div>, so the lazy close is exact.
BOX_RE = re.compile(r'<div class="inference-box">.*?</div>', re.S)


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("build_war_activity_codes", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def page() -> str:
    return PAGE.read_text(encoding="utf-8")


def _rows(page: str, tier: str) -> dict[str, str]:
    """Code -> row HTML, for one provenance tier."""
    out = {}
    for kind, body in ROW_RE.findall(page):
        if kind != tier:
            continue
        code = CODE_RE.search(body)
        out[code.group(1) if code else "?"] = body
    return out


# ---------------------------------------------------------------------------
# The guarantee the page exists to make
# ---------------------------------------------------------------------------
def test_no_unknown_code_renders_a_meaning(page):
    """Every ``unknown`` row shows the empty sentinel and nothing else.

    Not a style pin.  A published gloss on an undocumented code is
    indistinguishable, downstream, from a BSEE definition -- which is the
    defect #1065 was opened for.
    """
    rows = _rows(page, "t-unk")
    assert set(rows) == UNKNOWN_CODES | {"(blank)"}, set(rows)
    for code, body in rows.items():
        meaning = MEANING_RE.search(body)
        assert meaning, code
        assert meaning.group(1) == EMPTY_MEANING, code
        # No label markup, and no borrowed wording from the published domain.
        assert '<span class="lbl">' not in body, code
        for published in (
            "Drilling Active",
            "Borehole Completed",
            "Temporarily Abandoned",
            "Permanently Abandoned",
            "Borehole Side Tracked",
            "Drilling Suspended",
        ):
            assert published not in body, (code, published)


def test_pnd_is_never_glossed_as_pending_outside_the_inference_box(page):
    """PND is the one everybody wants to gloss. It may not be glossed here."""
    boxes = [m.span() for m in BOX_RE.finditer(page)]
    assert boxes, "no inference box found"
    hits = [m.start() for m in re.finditer("pending", page, re.I)]
    assert hits, "expected the inference to be quoted somewhere"
    for hit in hits:
        assert any(start <= hit < end for start, end in boxes), page[
            hit - 90 : hit + 40
        ]
    # And the inference box says, in terms, that it is not a definition.
    box = page[boxes[0][0] : boxes[0][1]]
    assert "Not a definition" in box
    assert "BSEE publishes no meaning for <code>PND</code>" in box


def test_generator_refuses_to_publish_a_meaning_for_an_unknown_code(mod):
    """The build fails rather than shipping a guess as a definition."""
    doc = {"codes": [{"code": "PND", "provenance": "unknown", "label": "Pending"}]}
    with pytest.raises(ValueError, match="refusing to publish a meaning"):
        mod.assert_no_meaning_for_unknown(doc)
    # ...and the cell renderer never emits a label for an unknown row.
    cell = mod.meaning_cell({"code": "PND", "provenance": "unknown", "label": None})
    assert cell == (
        '<span class="badge hold"><span class="d"></span>no meaning published</span>'
    )


def test_reuse_is_declared_inferred_on_every_published_other_domain_row(page):
    """Six rows carry BSEE's wording — every one must say the reuse is ours."""
    rows = _rows(page, "t-inf")
    assert set(rows) == INFERRED_CODES, set(rows)
    for code, body in rows.items():
        assert "BSEE wording, for <code>BOREHOLE_STAT_CD</code>" in body, code
        assert "boreholeFields" in body, code


def test_generator_checks_labels_against_bsee_wording(mod):
    doc = {
        "codes": [
            {
                "code": "DRL",
                "provenance": "published_other_domain",
                "label": "Drilling, probably",
            }
        ]
    }
    with pytest.raises(ValueError, match="no longer\n?\\s*matches|no longer matches"):
        mod.check_published_labels(doc)


# ---------------------------------------------------------------------------
# Headline and audit trail
# ---------------------------------------------------------------------------
def test_page_leads_with_the_negative_result(page):
    assert "BSEE publishes no <code>WELL_ACTIVITY_CD</code> domain at all." in page
    assert "0 of 12 codes defined by\n  BSEE" in page
    assert (
        "Not one of those\n  twelve values has a published definition for this field."
        in page
    )


def test_the_negative_result_is_auditable(page):
    """Every surface checked is named, with its outcome and a way to check it."""
    for surface in (
        "eWell WAR Field Definitions",
        "eWellWARRawData.zip",
        "Form BSEE-0133 (Well Activity Report)",
        "30 CFR 250.743",
        "ONRR Appendix H",
    ):
        assert surface in page, surface
    assert "5 of 5 negative" in page


def test_page_carries_the_outstanding_bsee_query(page):
    assert "TDM@bsee.gov" in page
    assert "The full WELL_ACTIVITY_CD domain, not PND alone." in page
    assert "Do not ask about <code>PND</code> alone." in page


def test_frequencies_are_shown_and_tie_to_the_committed_cache(mod, page):
    freq = mod.load_frequency()
    total = int(freq["(all rows)"]["rows"])
    codes = {k: v for k, v in freq.items() if k != "(all rows)"}
    assert sum(int(r["rows"]) for r in codes.values()) == total
    assert len(codes) == 13  # twelve codes plus the blank-code row
    assert f"{total:,}" in page
    for code, row in codes.items():
        assert f'<td class="num">{int(row["rows"]):,}</td>' in page, code


# ---------------------------------------------------------------------------
# Shape, links, regenerability
# ---------------------------------------------------------------------------
def test_page_is_self_contained(page):
    assert page.lstrip().lower().startswith("<!doctype html>")
    assert "</html>" in page
    for forbidden in ("<link", "<script", "<img", "@import", "fonts.googleapis"):
        assert forbidden not in page, forbidden


def test_page_has_both_theme_definitions(page):
    assert "@media (prefers-color-scheme: dark)" in page
    assert ':root[data-theme="dark"]' in page
    assert ':root[data-theme="light"]' in page


def test_external_links_are_github_or_a_cited_public_source(page):
    for url in re.findall(r'href="(https?://[^"]+)"', page):
        assert url.startswith(ALLOWED_HOSTS), url


def test_every_code_row_links_to_the_definitions_artifact(page):
    blob = (
        "https://github.com/vamseeachanta/worldenergydata/blob/main/packages"
        "/worldenergydata-bsee/src/worldenergydata/bsee/analysis/data"
        "/war_activity_codes.yml"
    )
    for kind in ("t-unk", "t-inf"):
        for code, body in _rows(page, kind).items():
            assert f'href="{blob}#L' in body, code
    assert f'href="{blob}"' in page


def test_relative_links_point_at_published_pages(page):
    rel = {
        u for u in re.findall(r'href="([^"#][^":]*)"', page) if not u.startswith("http")
    }
    assert rel == {
        "index.html",
        "wo-april-2026-qaqc-hub.html",
        "wo-april-2026-validation.html",
        "roy-rig-days-validation.html",
    }


def test_page_is_regenerable_and_deterministic(mod, page):
    yaml_path = mod.resolve_yaml()
    if yaml_path is None:
        pytest.skip(f"definitions artifact not available (expected {mod.PACKAGE_YAML})")
    assert mod.build(yaml_path) == page


def test_frequency_cache_is_committed(mod):
    assert FREQ.exists()
    assert set(mod.load_frequency()) >= UNKNOWN_CODES | INFERRED_CODES
