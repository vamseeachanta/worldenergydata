"""Contract tests for Lower Tertiary lifecycle poster link wiring.

These guard the poster builder's consumption of the canonical field registry
surfaces flags: economics links come from ``config/fields.yml`` and the
benchmark link targets the published root benchmark page.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest
import yaml

from tests.test_markers import unit
from worldenergydata.common.fields_registry import load_fields

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FACTS_PATH = PROJECT_ROOT / "reports" / "lower_tertiary" / "lifecycle" / "_facts.json"
BUILDER_PATH = (
    PROJECT_ROOT / "scripts" / "lower_tertiary" / "build_lifecycle_posters.py"
)

ECONOMICS_HREF_RE = re.compile(r"^\.\./economics-[a-z_]+\.html$")


def _load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_lifecycle_posters", BUILDER_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _facts():
    return json.loads(FACTS_PATH.read_text())


def _fact_by_id(field_id):
    return next(f for f in _facts() if f["id"] == field_id)


@unit
def test_registry_economics_flags_drive_poster_economics_links():
    builder = _load_builder()
    registry = load_fields()

    fields = {f["id"]: builder.facts_to_field(f) for f in _facts()}
    economics_ids = {
        field.canonical_id
        for field in registry.fields
        if field.surfaces.get("lifecycle_poster")
        and field.surfaces.get("economics_page")
    }
    no_economics_ids = set(fields) - economics_ids

    assert economics_ids == {
        "anchor",
        "big_foot",
        "cascade_chinook",
        "jack_st_malo",
        "julia",
        "shenandoah",
        "stones",
    }
    assert no_economics_ids == {"kaskida", "north_platte", "tiber"}

    for field_id in economics_ids:
        href = fields[field_id]["economics_href"]
        assert href == f"../economics-{field_id}.html"
        assert ECONOMICS_HREF_RE.match(href)

    for field_id in no_economics_ids:
        assert fields[field_id].get("economics_href") is None


@unit
def test_poster_fields_all_carry_published_benchmark_href():
    builder = _load_builder()

    hrefs = {builder.facts_to_field(f)["benchmark_href"] for f in _facts()}

    assert hrefs == {"../benchmark.html"}


@unit
def test_rendered_poster_has_hidden_economics_card_and_secondary_benchmark_chip():
    builder = _load_builder()

    html = builder.render(builder.facts_to_field(_fact_by_id("big_foot")))

    assert 'id="f-economics-card" hidden' in html
    assert "Field economics · monthly cash-flow model" in html
    assert "Open full economics" in html
    assert "Well benchmarking" in html
    assert "FIELD.economics_href" in html
    assert "FIELD.benchmark_href" in html


@pytest.mark.parametrize("field_id", ["cascade_chinook", "jack_st_malo"])
def test_unresolved_working_interests_match_canonical_status(field_id):
    """Issue 747: field YAML status governs eligibility, not entity ownership.

    Expected statuses come from field.working_interest_status in the committed
    YAML, whose P4/P7 references distinguish field interests from entity shares.
    No combined-field allocation is established by those references.
    """
    config_path = (
        PROJECT_ROOT / "config/analysis/lower_tertiary/fields" / f"{field_id}.yml"
    )
    config = yaml.safe_load(config_path.read_text())["field"]
    facts = _fact_by_id(field_id)
    assert facts["working_interest_status"] == config["working_interest_status"]
    assert facts["working_interest"] == []
    assert "NOT_EVALUATED" in facts["provenance"]


@pytest.mark.parametrize("status", ["contradicted", "unverified"])
def test_unresolved_shares_are_withheld_from_every_poster_payload(status):
    """A known Julia split is ineligible when flagged unresolved (issue 747).

    Julia's source P6 (operator release, 2016-04-19) supplies the fixture split.
    The expected empty arrays follow the eligibility rule, with no allocation
    calculation: unresolved shares cannot become a displayed field interest.
    """
    builder = _load_builder()
    facts = _fact_by_id("julia")
    facts["working_interest_status"] = status
    original_shares = list(facts["working_interest"])

    field = builder.facts_to_field(facts)

    assert field["workingInterest"] == []
    assert field["landman"]["working_interest"] == []
    assert not any(metric["k"] == "Operator WI" for metric in field["metrics"])
    assert ["Working interests", "NOT_EVALUATED — field allocation not verified"] in (
        field["hostFacts"]
    )
    assert facts["working_interest"] == original_shares


def test_established_shares_remain_visible():
    """Julia P6 (2016-04-19) supports its unchanged partner shares and operator."""
    builder = _load_builder()
    facts = _fact_by_id("julia")
    field = builder.facts_to_field(facts)
    assert field["workingInterest"]
    assert field["landman"]["working_interest"] == facts["working_interest"]
    assert any(metric["k"] == "Operator WI" for metric in field["metrics"])


@pytest.mark.parametrize("field_id", ["cascade_chinook", "jack_st_malo"])
def test_generated_posters_and_explorer_withhold_unresolved_shares(field_id):
    """Published payloads must obey the same issue 747 eligibility rule."""
    directory = FACTS_PATH.parent
    html = (directory / f"{field_id}_lifecycle.html").read_text()
    embedded = re.search(r"const FIELD = (\{.*?\n\});", html, re.DOTALL)
    assert embedded is not None
    poster = json.loads(embedded.group(1))
    explorer = json.loads((directory / "_explorer.json").read_text())

    assert poster == explorer["fields"][field_id]
    assert poster["workingInterest"] == []
    assert poster["landman"]["working_interest"] == []
    assert "NOT_EVALUATED" in poster["provenance"]
    assert any("NOT_EVALUATED" in value for _, value in poster["hostFacts"])
    assert not any(metric["k"] == "Operator WI" for metric in poster["metrics"])
