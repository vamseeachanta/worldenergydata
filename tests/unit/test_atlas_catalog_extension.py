"""Atlas identity and scope regressions for the Angola catalog extension."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "catalog_extension", ROOT / "scripts/field_atlas/catalog_extension.py"
)


def load_api():
    module = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(module)
    return module


def entity(identifier, name, kind="field"):
    return {"entity_id": identifier, "primary_name": name, "entity_type": kind,
            "country": "Angola", "readiness": "partial_research_only"}


def test_pending_matches_do_not_suppress_legacy_or_allocate_depth():
    api = load_api()
    legacy = {"FIELD_NAME": "Dalia", "COUNTRY": "Angola"}
    other = {"FIELD_NAME": "Other", "COUNTRY": "Brazil"}
    original = {"name": "Dalia", "catalog_id": "2", "country": "Angola"}
    unaffected = {"name": "Other", "catalog_id": "2", "country": "Brazil"}
    bundle = {"entities": [entity("ao:dalia", "Dalia"), entity("ao:phase", "Dalia phase", "phase")],
              "crosswalk": [{"entity_id": "ao:dalia", "legacy_row_fingerprint": "dalia",
                             "match_status": "pending", "relation_type": "same_entity"}],
              "evidence": {"field_observations": [{"entity_id": "dalia", "water_depth_m": {"min": 600, "max": 1200}}]},
              "manifest": {"schema_version": 1, "as_of": "2026-10-02"}}
    fields, counts = api.extend_fields([(legacy, original), (other, unaffected)], bundle,
                                      lambda row: row["FIELD_NAME"].lower())
    assert unaffected in fields and fields[fields.index(unaffected)] == unaffected
    assert original in fields
    modern = next(row for row in fields if row["catalog_id"] == "ao:dalia")
    assert modern["possible_duplicate"] is True
    assert modern["water_depth_ft"] is None
    assert counts["registered_fields"] == 1 and counts["registered_nonfields"] == 1
    assert counts["accepted_reconciled_identities"] == 0


def test_accepted_fingerprint_group_keeps_all_attributed_legacy_rows():
    api = load_api()
    pairs = [({"FIELD_NAME": "Dalia"}, {"name": "Dalia", "country": "Angola", "status": "old"})] * 2
    bundle = {"entities": [entity("ao:dalia", "Dalia")],
              "crosswalk": [{"entity_id": "ao:dalia", "legacy_row_fingerprint": "dalia",
                             "match_status": "accepted", "relation_type": "same_entity"}],
              "evidence": {}, "manifest": {"schema_version": 1}}
    fields, counts = api.extend_fields(pairs, bundle, lambda row: "dalia")
    assert len(fields) == 1
    assert len(fields[0]["legacy_attributes"]) == 2
    assert fields[0]["status"] is None
    assert counts["accepted_reconciled_identities"] == 1


def test_composite_relationship_never_suppresses_constituent_field():
    api = load_api()
    old = {"name": "Tombua Landana", "country": "Angola"}
    bundle = {"entities": [entity("ao:tombua", "Tombua")],
              "crosswalk": [{"entity_id": "ao:tombua", "legacy_row_fingerprint": "composite",
                             "match_status": "accepted", "relation_type": "constituent_of"}],
              "evidence": {}, "manifest": {"schema_version": 1}}
    fields, counts = api.extend_fields([({}, old)], bundle, lambda row: "composite")
    assert old in fields and len(fields) == 2
    assert counts["accepted_reconciled_identities"] == 0
    assert next(row for row in fields if row.get("catalog_id") == "ao:tombua")["possible_duplicate"] is True


def test_real_atlas_extension_preserves_non_angola_entries():
    import hashlib
    import sys
    sys.path.insert(0, str(ROOT / "scripts/field_atlas"))
    import build_atlas_feed as atlas
    baseline = atlas.build()
    bundle = {"entities": [entity("ao:new", "New research field")], "crosswalk": [],
              "evidence": {}, "manifest": {"schema_version": 1, "input_hashes": {
                  "legacy_catalog": hashlib.sha256(atlas.FIELDS_CSV.read_bytes()).hexdigest()}}}
    extended = atlas.build(integration=bundle)
    assert [row for row in baseline["fields"] if row["country"] != "Angola"] == [
        row for row in extended["fields"] if row["country"] != "Angola"]
    assert len(extended["fields"]) == len(baseline["fields"]) + 1
    assert extended["countries"] == baseline["countries"]


def test_atlas_rejects_extension_pinned_to_another_legacy_catalog():
    import sys
    import pytest
    sys.path.insert(0, str(ROOT / "scripts/field_atlas"))
    import build_atlas_feed as atlas
    bundle = {"entities": [], "crosswalk": [], "manifest": {
        "input_hashes": {"legacy_catalog": "0" * 64}}}
    with pytest.raises(ValueError, match="legacy catalog digest"):
        atlas.build(integration=bundle)


def test_research_preview_cannot_replace_default_public_feed(tmp_path):
    import os
    import shutil
    import subprocess
    import sys
    paths = ["scripts/field_atlas/build_atlas_feed.py", "scripts/catalog_badges.py",
             "data/modules/offshore_assets/curated/fields.csv",
             "data/modules/offshore_assets/curated/coverage_summary.csv",
             "data/freshness-scorecard.json", "reports/field-atlas/_roster.json"]
    for path in paths:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, target)
    environment = {key: value for key, value in os.environ.items()
                   if key not in {"GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"}}
    result = subprocess.run([sys.executable, str(tmp_path / paths[0]),
                             "--catalog-extension", "missing", "--research-preview"],
                            capture_output=True, text=True, env=environment, cwd=tmp_path)
    assert result.returncode != 0
    assert "explicit output" in result.stderr
    assert not (tmp_path / "reports/field-atlas/_atlas_feed.json").exists()
