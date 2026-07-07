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
    assert "Field economics · V30 monthly cash-flow model" in html
    assert "Open full economics" in html
    assert "Well benchmarking" in html
    assert "FIELD.economics_href" in html
    assert "FIELD.benchmark_href" in html
