"""Offline identity-join guards; synthetic names carry no engineering values."""

import csv
import importlib.util
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE = (
    ROOT
    / "packages/worldenergydata-cost/src/worldenergydata/cost/project_field_crosswalk.py"
)
CLI = ROOT / "scripts/cost/validate_project_field_crosswalk.py"


@pytest.fixture
def api():
    spec = importlib.util.spec_from_file_location("project_field_crosswalk", MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def fields():
    return [
        dict(
            field_id="field_a",
            name="Example A",
            aliases=["Alias A"],
            operator="Operator A",
            blocks=["AA001"],
        ),
        dict(
            field_id="field_b",
            name="Example B",
            aliases=[],
            operator="Operator B",
            blocks=["BB002"],
        ),
    ]


@pytest.fixture
def projects():
    return [
        dict(
            project_id="cost-a",
            name="Example A",
            sources=["curated/example.csv#PROJECT=Example A"],
            operator="Operator A",
            blocks=["AA001"],
        )
    ]


def link(**changes):
    row = dict(
        PROJECT_ID="cost-a",
        COST_PROJECT_ID="",
        PROJECT="Example A",
        CATALOG_FIELD_ID="field_a",
        MATCH_METHOD="exact_name",
        CONFIDENCE="high",
        PROVENANCE="derived",
        EVIDENCE="",
        REASON="",
    )
    row.update(changes)
    row["EVIDENCE"] = changes.get(
        "EVIDENCE",
        json.dumps(
            dict(
                project_sources=["curated/example.csv#PROJECT=Example A"],
                catalog_fields=(
                    [row["CATALOG_FIELD_ID"]] if row["CATALOG_FIELD_ID"] else []
                ),
                basis="Synthetic identity evidence",
                limitation="Field identity only; project scope retained; no cost allocation or scope equivalence.",
            )
        ),
    )
    return row


@pytest.mark.parametrize(
    "name,method", [(" Example   A ", "exact_name"), ("alias a", "alias")]
)
def test_name_and_held_alias_matching(api, fields, name, method):
    result = api.match_project(dict(name=name, operator="", blocks=[]), fields)
    assert result == dict(
        field_ids=["field_a"], method=method, confidence="high", reason=""
    )


def test_operator_and_block_require_both_and_a_unique_candidate(api, fields):
    query = dict(name="Different label", operator="operator a", blocks=["AA001"])
    result = api.match_project(query, fields)
    assert result["field_ids"] == ["field_a"]
    assert result["method"] == "operator_block"
    assert result["confidence"] == "medium"
    for change in ({"operator": ""}, {"blocks": []}, {"blocks": ["ZZ999"]}):
        assert api.match_project(query | change, fields)["field_ids"] == []


def test_ambiguity_is_not_silently_resolved(api, fields):
    collision = fields + [fields[0] | dict(field_id="field_c")]
    result = api.match_project(
        dict(name="Example A", operator="Operator A", blocks=["AA001"]), collision
    )
    assert result["field_ids"] == []
    assert "ambiguous" in result["reason"].lower()
    collision = fields + [fields[1] | dict(field_id="field_c", aliases=["Alias A"])]
    assert (
        "ambiguous"
        in api.match_project(dict(name="Alias A"), collision)["reason"].lower()
    )


def test_no_fuzzy_or_partial_bundle_match(api, fields):
    for name in ("Example A Phase 2", "Example A / Example B", "Example"):
        result = api.match_project(dict(name=name), fields)
        assert result["field_ids"] == []
        assert result["reason"]


def test_valid_one_to_many_and_explained_rows(api, projects, fields):
    rows = [
        link(),
        link(CATALOG_FIELD_ID="field_b", MATCH_METHOD="manual"),
    ]
    report = api.validate_crosswalk(rows, projects, fields)
    assert report["projects"] == report["mapped"] == report["accounted_for"] == 1
    assert report["explained"] == 0
    report = api.validate_crosswalk(
        [
            link(
                CATALOG_FIELD_ID="",
                MATCH_METHOD="unmatched",
                CONFIDENCE="low",
                REASON="Catalog coverage gap",
            )
        ],
        projects,
        [],
    )
    assert report["mapped"] == 0
    assert report["explained"] == report["accounted_for"] == 1


@pytest.mark.parametrize(
    "change,message",
    [
        ({"CATALOG_FIELD_ID": "missing"}, "field"),
        ({"PROJECT_ID": "missing"}, "project"),
        ({"PROJECT": "Wrong label"}, "name"),
        ({"EVIDENCE": " "}, "evidence"),
        ({"CONFIDENCE": "certain"}, "confidence"),
        ({"MATCH_METHOD": "fuzzy"}, "method"),
        ({"PROVENANCE": "sourced"}, "provenance"),
        ({"REASON": "contradiction"}, "reason"),
        ({"CATALOG_FIELD_ID": "", "MATCH_METHOD": "unmatched"}, "reason"),
        ({"MATCH_METHOD": "unmatched"}, "unmatched"),
        ({"CATALOG_FIELD_ID": "field_b"}, "match"),
    ],
)
def test_invalid_links_fail_closed(api, projects, fields, change, message):
    with pytest.raises(ValueError, match=message):
        api.validate_crosswalk([link(**change)], projects, fields)


def test_duplicates_missing_and_mixed_outcomes_rejected(api, projects, fields):
    with pytest.raises(ValueError, match="duplicate"):
        api.validate_crosswalk([link(), link()], projects, fields)
    with pytest.raises(ValueError, match="missing"):
        api.validate_crosswalk([], projects, fields)
    unmatched = link(
        CATALOG_FIELD_ID="", MATCH_METHOD="unmatched", CONFIDENCE="low", REASON="gap"
    )
    with pytest.raises(ValueError, match="mixed"):
        api.validate_crosswalk([link(), unmatched], projects, fields)
    with pytest.raises(ValueError, match="duplicate"):
        api.validate_crosswalk([link()], projects, fields + [deepcopy(fields[0])])


def write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def test_inventory_includes_staging_and_preserves_existing_ids(api, tmp_path):
    base = tmp_path / "data/modules/cost"
    identity = dict(
        OPAQUE_ID="prj-existing",
        DISPLAY_LABEL="Not the join key",
        ACTIVE="true",
        STATE="active",
        ENTITY_KIND="project",
        TOMBSTONED_BY_ID="",
        ALIASES="",
        SOURCE_TABLE="sanctioned_projects.csv",
        SOURCE_RECORD_LOCATOR="PROJECT=Example A",
    )
    write_csv(base / "curated/cost_project_identity.csv", list(identity), [identity])
    for filename in ("curated/sanctioned_projects.csv", "staging/batch/projects.csv"):
        write_csv(
            base / filename,
            ["PROJECT", "OPERATOR"],
            [
                dict(PROJECT="Example A", OPERATOR="Operator A"),
                dict(PROJECT="Example B", OPERATOR="Operator B"),
            ],
        )
    write_csv(
        base / "curated/references.csv",
        ["PROJECT_ID"],
        [dict(PROJECT_ID="prj-existing")],
    )
    found = api.load_cost_projects(tmp_path)
    assert {p["project_id"] for p in found} == {
        "PROJECT:Example A",
        "PROJECT:Example B",
    }
    assert all(any("staging/" in s for s in p["sources"]) for p in found)
    write_csv(base / "staging/new.csv", ["PROJECT"], [dict(PROJECT="New project")])
    fields = [
        dict(field_id="field_a", name="Example A", aliases=[], operator="", blocks=[])
    ]
    with pytest.raises(ValueError, match="missing"):
        rows = [
            link(
                PROJECT_ID=p["project_id"],
                COST_PROJECT_ID=p["cost_project_id"],
                PROJECT=p["name"],
                CATALOG_FIELD_ID="",
                MATCH_METHOD="unmatched",
                CONFIDENCE="low",
                REASON="gap",
                EVIDENCE=json.dumps(
                    dict(project_sources=p["sources"], catalog_fields=[], basis="gap")
                ),
            )
            for p in found
        ]
        api.validate_crosswalk(rows, api.load_cost_projects(tmp_path), fields)


def test_inventory_rejects_dangling_id_reference(api, tmp_path):
    write_csv(
        tmp_path / "data/modules/cost/staging/references.csv",
        ["PROJECT_ID"],
        [dict(PROJECT_ID="unknown")],
    )
    with pytest.raises(ValueError, match="unknown project"):
        api.load_cost_projects(tmp_path)


@pytest.mark.parametrize(
    "text", ["PROJECT,PROJECT\nA,A\n", "PROJECT\nA,extra\n", "PROJECT,OPERATOR\nA\n"]
)
def test_malformed_inventory_csv_is_rejected(api, tmp_path, text):
    path = tmp_path / "data/modules/cost/staging/bad.csv"
    path.parent.mkdir(parents=True)
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="CSV"):
        api.load_cost_projects(tmp_path)


def test_held_catalog_and_register_readback(api):
    fields = api.load_catalog(ROOT)
    assert {f["field_id"] for f in fields} >= {"big_foot", "jack_st_malo"}
    assert next(f for f in fields if f["field_id"] == "big_foot")["aliases"] == [
        "Bigfoot"
    ]
    projects = api.load_cost_projects(ROOT)
    assert len(projects) >= 80
    assert (
        next(p for p in projects if p["name"] == "Big Foot")["project_id"]
        == "PROJECT:Big Foot"
    )
    assert (
        next(p for p in projects if p["name"] == "Big Foot")["cost_project_id"]
        == "prj-000001"
    )
    result = api.validate_repository(ROOT)
    assert result["projects"] == len(projects)
    assert result["accounted_for"] == len(projects)
    held = api.read_crosswalk(ROOT / api.CROSSWALK, projects, fields)
    assert {r["CATALOG_FIELD_ID"] for r in held if r["CATALOG_FIELD_ID"]} >= {
        "anchor",
        "big_foot",
        "jack_st_malo",
        "julia",
        "kaskida",
        "shenandoah",
        "north_platte",
        "tiber",
    }


def test_crosswalk_reader_revalidates_and_manifest_pins_inputs(api, tmp_path):
    path = tmp_path / "bad.csv"
    write_csv(path, list(link()), [link(CATALOG_FIELD_ID="not-a-field")])
    with pytest.raises(ValueError, match="field"):
        api.read_crosswalk(
            path,
            [dict(project_id="cost-a", name="Example A")],
            [dict(field_id="field_a", name="Example A", aliases=[])],
        )
    manifest = json.loads(
        (
            ROOT / "data/modules/cost/curated/project_field_crosswalk.manifest.json"
        ).read_text("utf-8")
    )
    assert manifest["dataset_id"] == "cost-project-field-crosswalk"
    assert (
        "src/worldenergydata/field_development/past_projects.yml" in manifest["inputs"]
    )
    assert "config/fields.yml" in manifest["inputs"]
    api.verify_manifest(ROOT, manifest)
    manifest["inputs"]["config/fields.yml"] = "0" * 64
    with pytest.raises(ValueError, match="digest"):
        api.verify_manifest(ROOT, manifest)


def test_cli_validates_local_checkout_and_rejects_missing_file(api, tmp_path):
    before = {
        p: (ROOT / p).read_bytes()
        for p in api.input_paths(ROOT)
        + [api.CROSSWALK.as_posix(), api.MANIFEST.as_posix()]
    }
    command = [sys.executable, str(CLI), "--root", str(ROOT)]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["accounted_for"] >= 80
    result = subprocess.run(
        command + ["--crosswalk", str(tmp_path / "absent.csv")],
        capture_output=True,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    assert result.returncode != 0
    assert "error" in result.stderr.lower()
    assert before == {p: (ROOT / p).read_bytes() for p in before}


def test_manual_override_and_mismatched_evidence_rejected(api, projects, fields):
    with pytest.raises(ValueError, match="override omits"):
        api.validate_crosswalk(
            [link(CATALOG_FIELD_ID="field_b", MATCH_METHOD="manual")], projects, fields
        )
    bad = json.loads(link()["EVIDENCE"])
    bad["catalog_fields"] = ["field_b"]
    with pytest.raises(ValueError, match="evidence field mismatch"):
        api.validate_crosswalk([link(EVIDENCE=json.dumps(bad))], projects, fields)
    bad = json.loads(link()["EVIDENCE"])
    bad["project_sources"] = ["curated/other.csv#PROJECT=Example A"]
    with pytest.raises(ValueError, match="evidence project source mismatch"):
        api.validate_crosswalk([link(EVIDENCE=json.dumps(bad))], projects, fields)


def test_full_block_set_and_phase_scope_are_required(api, fields):
    fields[0]["blocks"] = ["AA001", "AA002"]
    query = dict(name="Different label", operator="Operator A", blocks=["AA001"])
    assert not api.match_project(query, fields)["field_ids"]
    assert not api.match_project(
        query | dict(name="Example A Phase 2", blocks=["AA001", "AA002"]), fields
    )["field_ids"]


def test_output_is_not_inventory_and_empty_project_is_rejected(api, tmp_path):
    base = tmp_path / "data/modules/cost"
    write_csv(base / "curated/projects.csv", ["PROJECT"], [dict(PROJECT="Example A")])
    write_csv(
        base / "curated/project_field_crosswalk.csv",
        ["PROJECT"],
        [dict(PROJECT="Output only")],
    )
    assert [p["name"] for p in api.load_cost_projects(tmp_path)] == ["Example A"]
    path = base / "staging/empty.csv"
    write_csv(path, ["PROJECT", "OPERATOR"], [dict(PROJECT=" ", OPERATOR="Operator A")])
    with pytest.raises(ValueError, match="CSV project name"):
        api.load_cost_projects(tmp_path)


def test_active_identity_uses_source_locator_and_rejects_mislabelled_reference(
    api, tmp_path
):
    base = tmp_path / "data/modules/cost"
    identity = dict(
        OPAQUE_ID="prj-existing",
        DISPLAY_LABEL="Wrong label",
        ACTIVE="true",
        STATE="active",
        ENTITY_KIND="project",
        TOMBSTONED_BY_ID="",
        ALIASES="Different label",
        SOURCE_TABLE="projects.csv",
        SOURCE_RECORD_LOCATOR="PROJECT=Example A",
    )
    write_csv(base / "curated/projects.csv", ["PROJECT"], [dict(PROJECT="Example A")])
    path = base / "curated/cost_project_identity.csv"
    write_csv(path, list(identity), [identity])
    reference = base / "staging/reference.csv"
    write_csv(
        reference,
        ["PROJECT_ID", "PROJECT"],
        [dict(PROJECT_ID="prj-existing", PROJECT="Different label")],
    )
    with pytest.raises(ValueError, match="ID/name mismatch"):
        api.load_cost_projects(tmp_path)
    write_csv(reference, ["PROJECT_ID"], [dict(PROJECT_ID="prj-existing")])
    for changes in (
        dict(ACTIVE="false"),
        dict(STATE="tombstoned"),
        dict(TOMBSTONED_BY_ID="successor"),
        dict(ENTITY_KIND="award"),
    ):
        write_csv(path, list(identity), [identity | changes])
        with pytest.raises(ValueError, match="unknown project ID"):
            api.load_cost_projects(tmp_path)
    write_csv(path, list(identity), [identity, identity | dict(OPAQUE_ID="prj-other")])
    with pytest.raises(ValueError, match="duplicate project identity"):
        api.load_cost_projects(tmp_path)


def test_non_locator_table_does_not_authenticate_a_controlled_id(api, tmp_path):
    base = tmp_path / "data/modules/cost"
    identity = dict(
        OPAQUE_ID="prj-existing",
        ACTIVE="true",
        STATE="active",
        ENTITY_KIND="project",
        SOURCE_TABLE="projects.csv",
        SOURCE_RECORD_LOCATOR="PROJECT=Example A",
    )
    write_csv(base / "curated/cost_project_identity.csv", list(identity), [identity])
    write_csv(base / "staging/projects.csv", ["PROJECT"], [dict(PROJECT="Example A")])
    with pytest.raises(ValueError, match="missing project identity source"):
        api.load_cost_projects(tmp_path)


def test_manifest_input_set_and_newlines(api, tmp_path):
    for index, raw in enumerate((b"a\nb\n", b"a\r\nb\r\n", b"a\rb\r")):
        path = tmp_path / str(index)
        path.write_bytes(raw)
    assert len({api.text_digest(tmp_path / str(i)) for i in range(3)}) == 1
    manifest = api.build_manifest(ROOT)
    assert "data/modules/cost/curated/cost_project_identity.csv" in manifest["inputs"]
    assert all(
        "data/modules/cost/curated/" + table in manifest["inputs"]
        for table in api.REGISTER_TABLES
    )
    assert api.CROSSWALK.as_posix() not in manifest["inputs"]
    for changed in (
        manifest | dict(inputs={}),
        manifest | dict(crosswalk_sha256="0" * 64),
    ):
        with pytest.raises(ValueError, match="digest mismatch"):
            api.verify_manifest(ROOT, changed)


def test_csv_bom_is_supported_and_lowercase_header_fails(api, tmp_path):
    path = tmp_path / "data/modules/cost/staging/projects.csv"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"\xef\xbb\xbfPROJECT\nExample A\n")
    assert api.load_cost_projects(tmp_path)[0]["name"] == "Example A"
    path.write_text("Project\nExample A\n", encoding="utf-8")
    with pytest.raises(ValueError, match="CSV PROJECT header"):
        api.load_cost_projects(tmp_path)


@pytest.mark.parametrize("header", ["project_id", "Project Name"])
def test_variant_identity_headers_do_not_leave_inventory_silently(
    api, tmp_path, header
):
    path = tmp_path / "data/modules/cost/staging/projects.csv"
    path.parent.mkdir(parents=True)
    path.write_text(header + "\nExample A\n", encoding="utf-8")
    with pytest.raises(ValueError, match="CSV PROJECT header"):
        api.load_cost_projects(tmp_path)


def test_blank_blocks_column_does_not_hide_structured_block(api, tmp_path):
    path = tmp_path / "data/modules/cost/staging/projects.csv"
    write_csv(
        path,
        ["PROJECT", "BLOCK", "BLOCKS"],
        [dict(PROJECT="Example A", BLOCK="AA001", BLOCKS="")],
    )
    assert api.load_cost_projects(tmp_path)[0]["blocks"] == ["AA001"]
    write_csv(
        path,
        ["PROJECT", "BLOCK", "BLOCKS"],
        [dict(PROJECT="Example A", BLOCK="AA001", BLOCKS="BB002")],
    )
    with pytest.raises(ValueError, match="conflicting structured blocks"):
        api.load_cost_projects(tmp_path)


def test_candidate_readback_does_not_require_the_held_output_digest(api, tmp_path):
    _, rows = api.read_csv(ROOT / api.CROSSWALK)
    manual = next(r for r in rows if r["MATCH_METHOD"] == "manual")
    evidence = json.loads(manual["EVIDENCE"])
    evidence["basis"] += " Additional review note for candidate verification."
    manual["EVIDENCE"] = json.dumps(evidence)
    candidate = tmp_path / "candidate.csv"
    write_csv(candidate, api.COLUMNS, rows)
    expected = len(api.load_cost_projects(ROOT))
    assert api.validate_repository(ROOT, candidate)["accounted_for"] == expected


def test_opaque_cost_id_cannot_be_forged(api, projects, fields):
    with pytest.raises(ValueError, match="controlled cost project ID mismatch"):
        api.validate_crosswalk([link(COST_PROJECT_ID="prj-forged")], projects, fields)


def test_held_partial_coverage_is_machine_readable(api):
    _, rows = api.read_csv(ROOT / api.CROSSWALK)
    partial = next(r for r in rows if r["PROJECT"] == "Tiber-Guadalupe")
    assert json.loads(partial["EVIDENCE"])["unmapped_scope"] == ["Guadalupe"]
    assert api.validate_repository(ROOT)["partial"] == 1


def test_manual_cannot_relabel_the_deterministic_link(api, projects, fields):
    with pytest.raises(ValueError, match="manual relabels deterministic match"):
        api.validate_crosswalk([link(MATCH_METHOD="manual")], projects, fields)


@pytest.mark.parametrize(
    "text", ['{"basis":"first","basis":"second"}', '{"basis":NaN}']
)
def test_ambiguous_evidence_json_is_rejected(api, projects, fields, text):
    with pytest.raises(ValueError, match="invalid evidence JSON"):
        api.validate_crosswalk([link(EVIDENCE=text)], projects, fields)


def test_catalog_source_drift_is_rejected(api, tmp_path):
    import yaml

    catalog = tmp_path / api.CATALOG
    identity = tmp_path / api.FIELD_IDENTITIES
    catalog.parent.mkdir(parents=True)
    identity.parent.mkdir(parents=True)
    raw = yaml.safe_load((ROOT / api.CATALOG).read_text("utf-8"))
    canonical = (ROOT / api.FIELD_IDENTITIES).read_text("utf-8")
    identity.write_text(canonical, encoding="utf-8")
    entry = raw["regions"]["gulf_of_mexico"]["projects"][0]
    for key, value, message in (
        ("project_id", "unknown", "unknown catalog field"),
        ("display_name", "Wrong", "name drift"),
        ("bsee_area_blocks", ["AA001"], "blocks drift"),
    ):
        original = entry[key]
        entry[key] = value
        catalog.write_text(yaml.safe_dump(raw), encoding="utf-8")
        with pytest.raises(ValueError, match=message):
            api.load_catalog(tmp_path)
        entry[key] = original
