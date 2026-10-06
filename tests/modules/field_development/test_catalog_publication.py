"""Transactional writer and complete publication accounting regressions."""

import copy
import json

import catalog_test_support as support
import pytest

api = support.api
inputs = support.inputs


@pytest.mark.parametrize("kind", ["dataset", "blank_entity", "multiplicity"])
def test_invalid_writer_leaves_no_artifacts_or_input_changes(
    api, inputs, tmp_path, kind
):
    draft = api.build_integration(*inputs)
    bundle = api.public_export(
        api.build_integration(*inputs, eligibility=support.reviewed_matrix(draft))
    )
    original = copy.deepcopy(bundle)
    before = {
        p: p.read_bytes()
        for root in inputs
        for p in ([root] if root.is_file() else root.iterdir())
    }
    if kind == "dataset":
        bundle["manifest"]["dataset_id"] = "wrong-dataset"
    elif kind == "blank_entity":
        bundle["entities"][0]["entity_id"] = ""
    else:
        bundle["links"]["records"][0]["multiplicity"] += 1
    out = tmp_path / "public"
    with pytest.raises(ValueError):
        api.write_bundle(bundle, out)
    assert not out.exists()
    assert not list(tmp_path.glob(".public.*"))
    assert before == {p: p.read_bytes() for p in before}
    assert original != bundle


def test_writer_preserves_existing_destination(api, inputs, tmp_path):
    out = tmp_path / "existing"
    out.mkdir()
    (out / "evidence.bin").write_bytes(b"preserve")
    with pytest.raises(FileExistsError):
        api.write_bundle(api.build_integration(*inputs), out)
    assert {p.name: p.read_bytes() for p in out.iterdir()} == {
        "evidence.bin": b"preserve"
    }


def test_writer_validates_before_destination_mutation(
    api, inputs, tmp_path, monkeypatch
):
    out = tmp_path / "blocked"

    def reject(*args, **kwargs):
        raise ValueError("simulated semantic rejection")

    monkeypatch.setattr(api.storage, "read_bundle", reject)
    with pytest.raises(ValueError, match="simulated"):
        api.write_bundle(api.build_integration(*inputs), out)
    assert not out.exists()
    assert not list(tmp_path.glob(".blocked.*"))


def test_duplicate_record_deferral_counts_raw_multiplicity(api, inputs, tmp_path):
    snapshot, _, _ = inputs
    path = snapshot / "cost_observations.json"
    rows = json.loads(path.read_text())
    support.write_json(path, rows + rows)
    manifest_path = snapshot / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    pin = next(row for row in manifest["files"] if row["path"] == path.name)
    pin.update(record_count=2, sha256=api.digest_bytes(path.read_bytes()))
    support.write_json(manifest_path, manifest)
    draft = api.build_integration(*inputs)
    decisions = support.reviewed_matrix(draft)
    for decision in decisions:
        if decision["table"] == "cost_observations":
            decision["decision"] = "prohibited"
    bundle = api.public_export(api.build_integration(*inputs, eligibility=decisions))
    assert bundle["manifest"]["source_counts"]["cost_observations"] == 2
    assert bundle["manifest"]["deferred_counts"]["cost_observations"] == 2
    assert bundle["manifest"]["counts"]["cost_observations"] == 0
    out = tmp_path / "public"
    api.write_bundle(bundle, out)
    assert (
        api.read_bundle(out, public_only=True)["manifest"]["deferred_counts"]
        == bundle["manifest"]["deferred_counts"]
    )


def test_public_export_preserves_original_surviving_match_decision(
    api, inputs, tmp_path
):
    draft = api.build_integration(*inputs)
    candidate = next(
        row for row in draft["crosswalk"] if row["origin_entity_id"] == "ao-dalia"
    )
    decision = {
        key: candidate[key]
        for key in (
            "entity_id",
            "legacy_row_fingerprint",
            "relation_type",
            "candidate_sha256",
        )
    }
    decision.update(
        match_status="accepted", approved_by="Vamsee", approval_ref="test-owner-claim"
    )
    exported = api.public_export(
        api.build_integration(
            *inputs, decisions=[decision], eligibility=support.reviewed_matrix(draft)
        )
    )
    assert exported["match_decisions"] == [decision]
    assert exported["manifest"]["decision_sha256"] == api.row_fingerprint([decision])
    out = tmp_path / "accepted"
    api.write_bundle(exported, out)
    assert api.read_bundle(out, public_only=True)["match_decisions"] == [decision]


def test_writer_partial_failure_removes_only_owned_files(
    api, inputs, tmp_path, monkeypatch
):
    original = api.storage._write_owned_file
    calls = []

    def fail_publication(path, raw, owned):
        calls.append(path)
        if len(calls) == 2:
            raise OSError("publication disk failure")
        original(path, raw, owned)

    monkeypatch.setattr(api.storage, "_write_owned_file", fail_publication)
    out = tmp_path / "partial"
    with pytest.raises(OSError, match="publication disk failure"):
        api.write_bundle(api.build_integration(*inputs), out)
    assert not out.exists()


@pytest.mark.parametrize("kind", ["directory", "file"])
def test_concurrent_destination_creation_is_preserved(
    api, inputs, tmp_path, monkeypatch, kind
):
    original = api.storage._validated_files
    out = tmp_path / "raced"

    def race(bundle):
        files = original(bundle)
        if kind == "directory":
            out.mkdir()
        else:
            out.write_bytes(b"concurrent file")
        return files

    monkeypatch.setattr(api.storage, "_validated_files", race)
    with pytest.raises(FileExistsError):
        api.write_bundle(api.build_integration(*inputs), out)
    if kind == "directory":
        assert out.is_dir()
        assert list(out.iterdir()) == []
    else:
        assert out.read_bytes() == b"concurrent file"


def test_reader_fails_closed_until_manifest_written_last(
    api, inputs, tmp_path, monkeypatch
):
    original = api.storage._write_owned_file
    observed = []

    def inspect(path, raw, owned):
        observed.append(path.name)
        if path.name != "integration_manifest.json":
            with pytest.raises(FileNotFoundError):
                api.read_bundle(path.parent)
        original(path, raw, owned)

    monkeypatch.setattr(api.storage, "_write_owned_file", inspect)
    out = tmp_path / "committed"
    api.write_bundle(api.build_integration(*inputs), out)
    assert observed[-1] == "integration_manifest.json"
    assert api.read_bundle(out)["entities"]


def test_writer_preserves_foreign_and_tampered_residue(
    api, inputs, tmp_path, monkeypatch
):
    original = api.storage._write_owned_file
    calls = []
    out = tmp_path / "residue"

    def tamper(path, raw, owned):
        calls.append(path)
        if len(calls) == 2:
            calls[0].write_bytes(b"foreign-tamper")
            (out / "foreign.txt").write_bytes(b"foreign")
            raise OSError("concurrent tampering")
        original(path, raw, owned)

    monkeypatch.setattr(api.storage, "_write_owned_file", tamper)
    with pytest.raises(OSError, match="concurrent tampering") as error:
        api.write_bundle(api.build_integration(*inputs), out)
    assert calls[0].read_bytes() == b"foreign-tamper"
    assert (out / "foreign.txt").read_bytes() == b"foreign"
    assert not (out / "integration_manifest.json").exists()
    assert any("residue" in note for note in error.value.__notes__)


def test_writer_rejects_accepted_same_entity_for_development_scope(
    api, inputs, tmp_path
):
    draft = api.build_integration(*inputs)
    candidate = next(
        row for row in draft["crosswalk"] if row["origin_entity_id"] == "ao-dalia"
    )
    decision = {
        key: candidate[key]
        for key in (
            "entity_id",
            "legacy_row_fingerprint",
            "relation_type",
            "candidate_sha256",
        )
    }
    decision.update(
        match_status="accepted",
        approved_by="Vamsee",
        approval_ref="test-owner-claim",
        adjudication_source_refs=["s1"],
    )
    exported = api.public_export(
        api.build_integration(
            *inputs, decisions=[decision], eligibility=support.reviewed_matrix(draft)
        )
    )
    next(row for row in exported["entities"] if row["origin_entity_id"] == "ao-dalia")[
        "entity_type"
    ] = "development"
    out = tmp_path / "invalid-same-entity"
    with pytest.raises(ValueError):
        api.write_bundle(exported, out)
    assert not out.exists()
    assert not list(tmp_path.glob(".invalid-same-entity.*"))


def test_partial_low_level_write_rolls_back_known_written_prefix(
    api, inputs, tmp_path, monkeypatch
):
    original = type(tmp_path).open
    out = tmp_path / "short-write"

    class ShortWrite:
        def __init__(self, stream):
            self.stream = stream
            self.calls = 0

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()

        def fileno(self):
            return self.stream.fileno()

        def write(self, raw):
            self.calls += 1
            if self.calls > 1:
                raise OSError("short-write failure")
            return self.stream.write(raw[:3])

    def partial_open(path, mode="r", *args, **kwargs):
        stream = original(path, mode, *args, **kwargs)
        return ShortWrite(stream) if mode == "xb" and path.parent == out else stream

    monkeypatch.setattr(type(tmp_path), "open", partial_open)
    with pytest.raises(OSError, match="short-write failure"):
        api.write_bundle(api.build_integration(*inputs), out)
    assert not out.exists()


def test_rollback_residue_preserves_legacy_exception_without_add_note(
    api, inputs, tmp_path, monkeypatch
):
    class LegacyError(OSError):
        add_note = None

    original = api.storage._write_owned_file
    out = tmp_path / "legacy-residue"
    calls = []

    def fail(path, raw, owned):
        calls.append(path)
        if len(calls) == 2:
            (out / "foreign.txt").write_bytes(b"foreign")
            raise LegacyError("legacy publication failure")
        original(path, raw, owned)

    monkeypatch.setattr(api.storage, "_write_owned_file", fail)
    with pytest.raises(
        RuntimeError, match="publication rollback preserved residue"
    ) as error:
        api.write_bundle(api.build_integration(*inputs), out)
    assert isinstance(error.value.__cause__, LegacyError)
    assert str(error.value.__cause__) == "legacy publication failure"
    assert (out / "foreign.txt").read_bytes() == b"foreign"
