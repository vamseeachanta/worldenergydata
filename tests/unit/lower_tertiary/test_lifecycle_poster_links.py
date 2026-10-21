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


@unit
def test_poster_and_explorer_use_the_same_sourced_lease_table():
    """Expected values are literal source columns, independently loaded from JSON."""
    builder = _load_builder()
    source = PROJECT_ROOT / "data/modules/bsee/leases"
    expected = {
        r["lease_num"]: r for r in json.loads((source / "leases.json").read_text())
    }
    seen = set()
    for facts in _facts():
        field = builder.facts_to_field(facts)
        for row in field["landman"]["leases"]:
            reference = expected[row["lease_num"]]
            assert row["status"] == reference["status"]
            assert row["per_lease_block"] == reference["area_block"]
            assert row["effective_date"] == reference["effective_date"]
            seen.add(row["lease_num"])
        assert "L.table_html" in builder.render(field)
    assert seen == set(expected)
    atlas = (PROJECT_ROOT / "reports/field-atlas/atlas_template.html").read_text(
        encoding="utf-8"
    )
    assert "L.table_html" in atlas


@unit
def test_published_explorer_uses_sourced_lease_table():
    atlas = (PROJECT_ROOT / "reports/field-atlas/index.html").read_text(
        encoding="utf-8"
    )
    landman = atlas.split('let landman = "";', 1)[1].split(
        "// Concept & development", 1
    )[0]
    assert "L.table_html" in landman
    assert "— pending" not in landman


@unit
@pytest.mark.parametrize("lease_panels_only", [False, True])
def test_generator_can_write_to_a_separate_output_directory(
    tmp_path, monkeypatch, lease_panels_only
):
    """Generated panels and Explorer must carry identical serialized payloads."""
    builder = _load_builder()
    argv = ["build_lifecycle_posters.py", "--output-dir", str(tmp_path)]
    if lease_panels_only:
        argv.append("--lease-panels-only")
    monkeypatch.setattr("sys.argv", argv)
    builder.main()
    explorer = json.loads((tmp_path / "_explorer.json").read_text())
    for field_id, field in explorer["fields"].items():
        poster = (tmp_path / f"{field_id}_lifecycle.html").read_text(encoding="utf-8")
        # The generator embeds exactly this JSON object in the poster script.
        assert (
            json.dumps(field, indent=2, ensure_ascii=False).replace("<", "\\u003c")
            in poster
        )
        assert field["landman"]["source"]["freshness_status"] == "unknown"
        assert "leases" not in field["landman"]
        assert field["landman"]["n_leases"] > 0
        assert '<table class="lease xwells">' in field["landman"]["table_html"]
    if lease_panels_only:
        frozen = json.loads((builder.HERE / "_explorer.json").read_text())
        for field_id, field in explorer["fields"].items():
            assert {k: v for k, v in field.items() if k != "landman"} == {
                k: v for k, v in frozen["fields"][field_id].items() if k != "landman"
            }


@unit
def test_source_names_cannot_close_the_embedded_poster_script():
    from worldenergydata.field_development.landman import render_lease_table

    builder = _load_builder()
    field = builder.facts_to_field(_facts()[0])
    malicious = "</script><script>alert('source name')</script>"
    field["landman"]["leases"][0]["per_lease_working_interest"] = [
        {"owner_name": malicious}
    ]
    field["landman"]["table_html"] = render_lease_table(field["landman"])
    assert malicious not in builder.render(field)
    assert "&lt;/script&gt;" in builder.render(field)


@unit
def test_poster_serialization_uses_one_lease_representation_without_mutating_input():
    builder = _load_builder()
    field = builder.facts_to_field(_facts()[0])
    original = json.loads(json.dumps(field))
    poster = builder.render(field)
    published = json.loads(re.search(r"const FIELD = (\{.*?\n\});", poster, re.S)[1])
    assert "leases" not in published["landman"]
    assert published["landman"]["table_html"] == original["landman"]["table_html"]
    assert {k: v for k, v in published.items() if k != "landman"} == {
        k: v for k, v in original.items() if k != "landman"
    }
    assert field == original


@unit
@pytest.mark.parametrize("published", [False, True])
def test_poster_block_caveats_remain_visible(published):
    """Registry caveats must reach the rendered and committed poster sections."""
    builder = _load_builder()
    for facts in _facts():
        field = builder.facts_to_field(facts)
        if published:
            html = (builder.HERE / f"{field['id']}_lifecycle.html").read_text(
                encoding="utf-8"
            )
        else:
            html = builder.render(field)
        landman = html.split("if (FIELD.landman) {", 1)[1].split('$("f-metrics")', 1)[0]
        assert "L.block_note" in landman
