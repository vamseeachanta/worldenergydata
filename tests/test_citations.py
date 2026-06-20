"""Tests for the calc-citation-contract (worldenergydata#361).

Covers:
  - Citation validates required fields; malformed (missing source) is rejected.
  - Attaching citations to a sample calc emits a sidecar that round-trips.
  - The sidecar does NOT mutate the primary numeric payload.
  - Each first-wave constant carries a real source.
  - Fail-closed resolution: a missing wiki page raises CitationResolutionError
    with code_id in the message.
"""
from __future__ import annotations

import json

import pytest

from worldenergydata.citations import (
    Citation,
    CitationResolutionError,
    CitationValidationError,
    CitedValue,
    FIRST_WAVE,
    build_sidecar,
    emit_sidecar,
    get_bsee_royalty_rate,
    get_depth_breakpoint,
    get_wti_price_base,
    load_sidecar,
    validate_citation,
)


def _good_citation(**overrides) -> Citation:
    base = dict(
        code_id="30-cfr-250",
        publisher="BSEE",
        revision="2024",
        section="Part 250",
        wiki_path="wikis/regulatory/wiki/standards/30-cfr-250.md",
    )
    base.update(overrides)
    return Citation(**base)


# --- schema: required fields -------------------------------------------------


def test_citation_accepts_complete_required_fields():
    c = _good_citation()
    assert c.code_id == "30-cfr-250"
    assert c.publisher == "BSEE"
    assert c.wiki_path.startswith("wikis/")


@pytest.mark.parametrize("missing", ["code_id", "publisher", "revision", "section"])
def test_citation_rejects_missing_required_field(missing):
    with pytest.raises(CitationValidationError):
        _good_citation(**{missing: ""})


def test_citation_rejects_missing_source_publisher():
    """A citation with no source/publisher is structurally invalid."""
    with pytest.raises(CitationValidationError):
        _good_citation(publisher="   ")


def test_citation_rejects_bad_wiki_path():
    with pytest.raises(CitationValidationError):
        _good_citation(wiki_path="standards/foo.md")  # not under wikis/
    with pytest.raises(CitationValidationError):
        _good_citation(wiki_path="wikis/../etc/passwd.md")  # traversal


# --- sidecar emission + round-trip ------------------------------------------


def test_attach_citations_emits_roundtrip_sidecar(tmp_path):
    """A sample calc writes its numeric payload, then a citation sidecar that
    round-trips back to the same Citation objects."""
    primary = tmp_path / "npv_result.json"
    payload = {"npv_usd": -531_000_000.0, "field": "julia"}
    primary.write_text(json.dumps(payload), encoding="utf-8")
    original_bytes = primary.read_bytes()

    royalty = get_bsee_royalty_rate()
    wti = get_wti_price_base()
    sidecar_path = emit_sidecar(primary, [royalty, wti])

    # Sidecar lands next to the primary, with the expected name.
    assert sidecar_path.name == "npv_result.citations.json"
    assert sidecar_path.parent == primary.parent

    # Primary numeric payload is UNTOUCHED (do-not-mutate criterion).
    assert primary.read_bytes() == original_bytes

    # Round-trip: reconstructed citations match by code_id.
    loaded = load_sidecar(sidecar_path)
    assert {c.code_id for c in loaded} == {royalty.citation.code_id, wti.citation.code_id}
    # CitedValue value survives in the sidecar payload.
    data = json.loads(sidecar_path.read_text(encoding="utf-8"))
    royalty_entry = next(e for e in data["citations"] if e["code_id"] == "30-cfr-250")
    assert royalty_entry["value"] == pytest.approx(0.125)
    assert data["contract"] == "calc-citation-contract"


def test_build_sidecar_accepts_bare_citation():
    sc = build_sidecar([_good_citation()], output_name="x.json")
    assert sc["citations"][0]["code_id"] == "30-cfr-250"
    assert sc["citations"][0]["citation"]["publisher"] == "BSEE"


def test_citation_to_from_dict_roundtrip():
    c = _good_citation(retrieved="2025-10-31", units="fraction", note="hi")
    assert Citation.from_dict(c.to_dict()) == c


# --- first-wave constants carry real sources --------------------------------


def test_first_wave_constants_carry_real_sources():
    for name, getter in FIRST_WAVE.items():
        cv = getter()
        assert isinstance(cv, CitedValue), name
        cit = cv.citation
        assert cit.code_id and cit.publisher and cit.revision, name
        assert cit.section.strip(), name
        assert cit.wiki_path.startswith("wikis/"), name


def test_bsee_royalty_real_value_and_publisher():
    cv = get_bsee_royalty_rate("deepwater")
    assert cv.value == pytest.approx(0.125)  # 1/8 statutory OCS royalty
    assert cv.citation.publisher == "BSEE"
    assert "30-cfr-250" == cv.citation.code_id
    assert get_bsee_royalty_rate("shelf").value == pytest.approx(0.1875)


def test_wti_price_base_publisher_is_eia():
    cv = get_wti_price_base()
    assert cv.units == "USD/bbl"
    assert cv.citation.publisher == "EIA"
    assert cv.citation.retrieved  # time-varying source carries an as-of date


def test_depth_breakpoints_match_config_thresholds():
    assert get_depth_breakpoint("dry").value == pytest.approx(500.0)
    assert get_depth_breakpoint("deepwater").value == pytest.approx(6000.0)


def test_unknown_lease_class_rejected():
    with pytest.raises(ValueError):
        get_bsee_royalty_rate("offworld")


# --- fail-closed resolution --------------------------------------------------


def test_missing_wiki_page_raises_with_code_id(tmp_path):
    """validate_citation against an empty repo_root must fail-closed and carry
    code_id so an operator can retarget the constant."""
    c = _good_citation()
    with pytest.raises(CitationResolutionError) as exc:
        validate_citation(c, repo_root=tmp_path)
    assert exc.value.code_id == "30-cfr-250"
    assert "30-cfr-250" in str(exc.value)
    assert exc.value.reason == "page_missing"


def test_frontmatter_mismatch_raises(tmp_path):
    """A present page whose frontmatter disagrees fails-closed."""
    page = tmp_path / "wikis" / "regulatory" / "wiki" / "standards" / "30-cfr-250.md"
    page.parent.mkdir(parents=True)
    page.write_text(
        "---\n"
        "code_id: 30-cfr-250\n"
        "publisher: WRONG\n"
        "revision: 2024\n"
        "---\n\nbody\n",
        encoding="utf-8",
    )
    with pytest.raises(CitationResolutionError) as exc:
        validate_citation(_good_citation(), repo_root=tmp_path)
    assert "frontmatter_mismatch:publisher" in exc.value.reason


def test_frontmatter_match_passes(tmp_path):
    page = tmp_path / "wikis" / "regulatory" / "wiki" / "standards" / "30-cfr-250.md"
    page.parent.mkdir(parents=True)
    page.write_text(
        "---\n"
        "code_id: 30-cfr-250\n"
        "publisher: BSEE\n"
        "revision: 2024\n"
        "---\n\nbody\n",
        encoding="utf-8",
    )
    # Should not raise.
    validate_citation(_good_citation(), repo_root=tmp_path)
