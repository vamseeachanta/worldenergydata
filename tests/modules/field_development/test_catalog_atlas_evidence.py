"""Atlas consumes validated evidence without collapsing scope or identity."""

import importlib.util
import sys
from importlib import import_module

from tests.modules.field_development import catalog_test_support as support

api = support.api
inputs = support.inputs
ATLAS = support.ROOT / "scripts/field_atlas"
sys.path.insert(0, str(ATLAS))
atlas = import_module("build_atlas_feed")


def extension():
    spec = importlib.util.spec_from_file_location(
        "catalog_extension", ATLAS / "catalog_extension.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_atlas_attaches_exact_evidence_and_public_source_urls(api, inputs):
    """Each registered field receives the evidence reader's exact-ID result."""
    bundle = api.build_integration(*inputs)
    rows, _ = extension().extend_fields([], bundle, api.row_fingerprint)
    reader = api.CatalogEvidence(bundle)
    for row in rows:
        expected = reader.entity(row["catalog_id"])
        assert row["research_evidence"] == expected
        assert (
            row["research_evidence"]["sources"][0]["url"]
            == bundle["evidence"]["sources"][0]["url"]
        )
        assert row["water_depth_ft"] is None
        assert row["current_configuration_verified"] is False


def test_atlas_nonfields_expose_cost_scope_without_adding_field_rows(
    api, inputs, tmp_path, monkeypatch
):
    """By hand: each input entity is either field or nonfield, exactly once.

    Costs stay on the typed development candidate; nonfields never inflate the
    fields collection. Global catalog and country badge values are unchanged.
    """
    snapshot, _, parent = inputs
    fields = tmp_path / "independent-fields.csv"
    fields.write_text(
        "FIELD_ID,FIELD_NAME,COUNTRY,BLOCK,CURRENT_STATUS,RESERVE_TYPE,"
        "WATER_DEPTH_FT,US_GOM_FLAG\n"
        "independent,Synthetic field,Angola,A1,Discovery,Oil,100,\n",
        encoding="utf-8",
        newline="\n",
    )
    coverage = tmp_path / "coverage.csv"
    coverage.write_text("by_country,Angola,1,0\n", encoding="utf-8", newline="\n")
    roster = tmp_path / "roster.json"
    roster.write_text("[]", encoding="utf-8", newline="\n")
    scorecard = tmp_path / "scorecard.json"
    scorecard.write_text('{"modules": {}}', encoding="utf-8", newline="\n")
    monkeypatch.setattr(atlas, "FIELDS_CSV", fields)
    monkeypatch.setattr(atlas, "COVERAGE_CSV", coverage)
    monkeypatch.setattr(atlas, "ROSTER", roster)
    monkeypatch.setattr(atlas, "SCORECARD", scorecard)
    bundle = api.build_integration(snapshot, fields, parent)
    baseline = atlas.build()
    assert len(baseline["fields"]) == 1
    assert len(baseline["countries"]) == 1
    feed = atlas.build(integration=bundle)
    metadata = feed["meta"]["catalog_extension"]
    nonfields = metadata["nonfield_entities"]
    assert len(nonfields) == sum(
        e["entity_type"] != "field" for e in bundle["entities"]
    )
    assert len(feed["fields"]) == len(baseline["fields"]) + sum(
        e["entity_type"] == "field" for e in bundle["entities"]
    )
    assert feed["countries"] == baseline["countries"]
    for row in nonfields:
        assert row["entity_type"] != "field"
        assert row["research_evidence"]["entity"]["entity_type"] == row["entity_type"]
    cost_scopes = [
        row
        for row in nonfields
        if any(
            r["table"] == "cost_observations"
            for r in row["research_evidence"]["records"]
        )
    ]
    assert len(cost_scopes) == len(bundle["evidence"]["cost_observations"])
    assert cost_scopes[0]["entity_type"] == "development"
    assert metadata["state"] == "local_draft_not_for_publication"


def test_projection_is_deterministic_and_preserves_relationships(api, inputs):
    bundle = api.build_integration(*inputs)
    reader = api.CatalogEvidence(bundle)
    for entity in bundle["entities"]:
        first = reader.entity(entity["entity_id"])
        assert first == reader.entity(entity["entity_id"])
        assert first["relationships"] == [
            row
            for row in bundle["relationships"]
            if entity["entity_id"]
            in (row["subject_entity_id"], row["object_entity_id"])
        ]
