"""Evidence-preserving catalog contract regressions."""

import hashlib
import json
from pathlib import Path

import catalog_test_support as support
import pytest

api = support.api
inputs = support.inputs
reviewed_matrix = support.reviewed_matrix
repin = support.repin
write_json = support.write_json


def test_public_export_defers_match_with_unreleased_adjudication_source(api, inputs):
    snapshot, _, _ = inputs
    sources = json.loads((snapshot / "sources.json").read_text())
    sources.append({"source_ref": "s2", "url": "https://example.org/adjudication"})
    write_json(snapshot / "sources.json", sources)
    manifest = json.loads((snapshot / "manifest.json").read_text())
    pin = next(r for r in manifest["files"] if r["path"] == "sources.json")
    pin.update(
        record_count=2,
        sha256=hashlib.sha256((snapshot / "sources.json").read_bytes()).hexdigest(),
    )
    write_json(snapshot / "manifest.json", manifest)
    draft = api.build_integration(*inputs)
    candidate = next(
        r for r in draft["crosswalk"] if r["origin_entity_id"] == "ao-cameia"
    )
    decision = dict(
        candidate,
        match_status="accepted",
        approved_by="Vamsee",
        approval_ref="fixture evidence",
        adjudication_source_refs=["s2"],
    )
    matrix = reviewed_matrix(draft)
    next(r for r in matrix if r["record_id"].endswith("sources:s2"))[
        "decision"
    ] = "prohibited"
    exported = api.public_export(
        api.build_integration(*inputs, decisions=[decision], eligibility=matrix)
    )
    assert not any(r["origin_entity_id"] == "ao-cameia" for r in exported["crosswalk"])


def test_reader_rejects_duplicate_manifest_keys(api, inputs, tmp_path):
    api.write_bundle(api.build_integration(*inputs), tmp_path / "out")
    path = tmp_path / "out/integration_manifest.json"
    path.write_text(
        path.read_text().replace("{", '{"schema_version":2,', 1), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="duplicate"):
        api.read_bundle(tmp_path / "out")


@pytest.mark.parametrize("status", ["pending", "rejected"])
def test_conflict_disposition_requires_revision_bound_evidence_claim(
    api, inputs, status
):
    bundle = api.build_integration(*inputs)
    candidate = next(
        r for r in bundle["crosswalk"] if r["origin_entity_id"] == "ao-cameia"
    )
    decision = {
        k: candidate[k]
        for k in ("entity_id", "legacy_row_fingerprint", "relation_type")
    }
    decision["match_status"] = status
    with pytest.raises(ValueError, match="evidence"):
        api.build_integration(*inputs, decisions=[decision])


@pytest.mark.parametrize(
    "public, expected",
    [
        (False, "b38604b6ac8d42ca2056569ae5e276e2b962861ad644facc48aa6b27b30f1966"),
        (True, "1792252710b4c0a1be644ecd59b628fe211b1506eb8290265a27923fdfc7ef2f"),
    ],
)
def test_frozen_catalog_bytes_survive_module_refactoring(
    api, inputs, tmp_path, public, expected
):
    bundle = api.build_integration(*inputs)
    if public:
        bundle = api.public_export(
            api.build_integration(*inputs, eligibility=reviewed_matrix(bundle))
        )
    out = tmp_path / "frozen"
    api.write_bundle(bundle, out)
    hashes = {
        file.name: api.digest_bytes(file.read_bytes()) for file in sorted(out.iterdir())
    }
    assert api.row_fingerprint(hashes) == expected


@pytest.mark.parametrize("public", [False, True])
def test_package_import_preserves_all_generated_bytes(api, inputs, tmp_path, public):
    import shutil
    import subprocess
    import sys

    package = tmp_path / "isolated_catalog"
    package.mkdir()
    (package / "__init__.py").write_text("")
    for source in Path(api.__file__).parent.glob("catalog*.py"):
        shutil.copyfile(source, package / source.name)
    script = """
import sys
sys.path.insert(0, sys.argv[1])
from isolated_catalog import catalog_integration as api
bundle = api.build_integration(*sys.argv[2:5])
if sys.argv[6] == "True":
    import json
    decisions = json.loads(sys.argv[7])
    bundle = api.public_export(api.build_integration(*sys.argv[2:5], eligibility=decisions))
api.write_bundle(bundle, sys.argv[5])
"""
    draft = api.build_integration(*inputs)
    decisions = reviewed_matrix(draft)
    expected = (
        api.public_export(api.build_integration(*inputs, eligibility=decisions))
        if public
        else draft
    )
    direct = tmp_path / "direct"
    packaged = tmp_path / "packaged"
    api.write_bundle(expected, direct)
    subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            script,
            str(tmp_path),
            *map(str, inputs),
            str(packaged),
            str(public),
            json.dumps(decisions),
        ],
        check=True,
    )
    assert {p.name: p.read_bytes() for p in packaged.iterdir()} == {
        p.name: p.read_bytes() for p in direct.iterdir()
    }
