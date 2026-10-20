"""FDP authoring contracts for the remaining Lower Tertiary fields.

Coverage derives from issue #962's field list. Engineering expectations below
come from the publications cited in each test, independently of the renderer.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from worldenergydata.field_development.concept import build_concept

ROOT = Path(__file__).resolve().parents[3]
PORTFOLIO = ROOT / "reports/field_development/portfolio"
REMAINING = (
    "big_foot",
    "anchor",
    "jack_st_malo",
    "kaskida",
    "north_platte",
    "shenandoah",
    "tiber",
)
SPEC = importlib.util.spec_from_file_location(
    "fdp_portfolio", ROOT / "scripts/field_development/build_fdp_portfolio.py"
)
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def profiles():
    return json.loads((PORTFOLIO / "_research.json").read_text())


def registry():
    from worldenergydata.common.fields_registry import load_fields

    return load_fields()


def profile_for(field_id):
    field = registry().by_id(field_id)
    return next(d for d in profiles() if builder._slug(d["name"]) == field.fdp_slug)


@pytest.mark.parametrize("field_id", REMAINING)
def test_documented_page_and_registry_link(field_id):
    """Issue #962 requires a page and a live registry-driven link for each id."""
    field = registry().by_id(field_id)
    assert field.surfaces["fdp_page"] is True
    profile = profile_for(field_id)
    assert builder.to_concept(profile).concept_type is not None
    page = PORTFOLIO / f"{field.fdp_slug}.html"
    assert page.read_text() == builder.build_profile_page(profile)
    panel = build_concept(
        concept_label=profile["concept_type"],
        host_type=profile["host_facility"],
        play=profile["reservoir_play"],
        first_oil=None,
        fid_year=None,
        fdp_slug=field.fdp_slug,
        has_fdp=field.surfaces["fdp_page"],
        fdp_issue=962,
    )
    assert panel["fdp_href"].endswith(f"/{page.name}")
    assert (
        panel["fdp_href"]
        in (
            ROOT / "reports/lower_tertiary/lifecycle" / f"{field_id}_lifecycle.html"
        ).read_text()
    )
    explorer = json.loads(
        (ROOT / "reports/lower_tertiary/lifecycle/_explorer.json").read_text()
    )
    assert explorer["fields"][field_id]["concept"]["fdp_href"] == panel["fdp_href"]


@pytest.mark.parametrize("field_id", REMAINING)
def test_evidence_and_honesty_sections(field_id):
    """Every reported input has a source; unsupported calculations stay unevaluated."""
    profile = profile_for(field_id)
    citations = profile["input_sources"]
    for key in (
        "concept_type",
        "operator_current",
        "host_facility",
        "water_depth_m",
        "num_wells",
        "plateau_boed",
        "first_oil_year",
        "recoverable_reserves_mmboe",
        "reported_oil_capacity_bpd",
    ):
        if profile.get(key) is not None:
            assert citations[key]["source"] in profile["evidence"]
            assert citations[key]["comment"]
    page = builder.build_profile_page(profile)
    for heading in (
        "Summary",
        "Revision history",
        "Engineering rationale",
        "Field parameters",
        "Architecture",
        "Economics",
        "Sources",
        "NOT_EVALUATED",
    ):
        assert heading in page
    assert page.index("Summary") < page.index("Revision history")
    assert page.index("Revision history") < page.index("Engineering rationale")
    assert "Est. CAPEX" not in page
    for source in profile["evidence"].values():
        assert source["url"] in page.replace("&amp;", "&")
        assert source["http_status"] == 200
        assert len(source["sha256"]) == 64


def test_sparta_published_example():
    """Equinor, 'Final Investment Decision for Sparta', 20 December 2023.

    The Facts about Sparta box states eight subsea wells, 1,310 metres of water,
    and 100,000 boe/d designed peak capacity. Direct transcription gives
    FieldConcept(8, 1310, 100000); capacity is not measured production. No
    equation, conversion or inferred reserve midpoint is involved.
    """
    concept = builder.to_concept(profile_for("north_platte"))
    assert concept.num_wells == 8
    assert concept.water_depth_m == 1310
    assert concept.plateau_rate_boed == 100000
    assert concept.recoverable_reserves_mmboe is None
    assert concept.year_first_oil is None


def test_tiber_scope_and_oil_units():
    """Oilfield Technology, 30 September 2025: six Tiber wells, two Guadalupe wells.

    Independent scope calculation: the combined hub has 6 + 2 = 8 wells;
    Tiber alone has 6. The hub's 80,000 bbl/d oil capacity is neither a Tiber
    boe/d plateau nor a Tiber reserve estimate, so those inputs stay null.
    """
    profile = profile_for("tiber")
    concept = builder.to_concept(profile)
    assert concept.num_wells == 6
    assert profile["reported_oil_capacity_bpd"] == 80000
    assert concept.plateau_rate_boed is None
    assert concept.recoverable_reserves_mmboe is None
    assert concept.year_first_oil is None
    assert "Guadalupe" in builder.build_profile_page(profile)


def test_unknowns_do_not_become_default_wells_or_first_oil():
    profile = profile_for("big_foot")
    assert builder.to_concept(profile).num_wells is None
    assert builder.to_concept(profile_for("kaskida")).year_first_oil is None


def test_documented_pages_do_not_run_heuristics(monkeypatch):
    def reject(*args, **kwargs):
        raise AssertionError("documented pages must not invent model outputs")

    monkeypatch.setattr(builder, "recommend", reject)
    monkeypatch.setattr(builder, "build_fdp_html", reject)
    for field_id in REMAINING:
        assert "NOT_EVALUATED" in builder.build_profile_page(profile_for(field_id))


def test_documented_content_is_escaped():
    profile = dict(profile_for("anchor"), narrative="<script>unsafe</script>")
    page = builder.build_profile_page(profile)
    assert "<script>unsafe</script>" not in page
    assert "&lt;script&gt;unsafe&lt;/script&gt;" in page


def test_index_covers_every_researched_field():
    page = builder.build_index(profiles())
    for profile in profiles():
        assert f'href="{builder._slug(profile["name"])}.html"' in page
    assert "Concept (reported)" in page
    assert "NOT_EVALUATED" in page


def test_documented_only_build_is_reproducible(tmp_path, monkeypatch):
    """The CLI builds the documented profiles without rewriting legacy pages."""
    import sys

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_fdp_portfolio.py",
            str(PORTFOLIO / "_research.json"),
            "--documented-only",
            "--output-dir",
            str(tmp_path),
        ],
    )
    builder.main()
    expected = {
        f'{builder._slug(profile["name"])}.html'
        for profile in profiles()
        if profile.get("evidence")
    } | {"index.html"}
    assert {path.name for path in tmp_path.iterdir()} == expected
    for name in expected:
        assert (tmp_path / name).read_bytes() == (PORTFOLIO / name).read_bytes()


def test_known_value_without_citation_is_rejected():
    profile = dict(profile_for("anchor"), input_sources={})
    with pytest.raises(ValueError, match="Missing input citation"):
        builder.build_profile_page(profile)
