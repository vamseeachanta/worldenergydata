"""Synthetic publication checks; expected bytes are literal construction inputs.

The only digest oracle is RFC 6234 (2011), section 8.5, SHA256 TEST1.
Race expectations follow the snapshot/staging contract in issue #1048: a changed
input or sealed output must fail before the caller publishes any returned bytes.
"""

import json
import os

import pytest

from worldenergydata.common import input_snapshot
from worldenergydata.common.artifact_snapshot import (
    OutputIntegrityError,
    build_artifacts,
)
from worldenergydata.common.input_snapshot import InputIntegrityError

# RFC 6234 (2011), section 8.5: SHA256 TEST1 is the ASCII message "abc".
ABC_SHA256 = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_steady_build_returns_frozen_inputs_outputs_and_manifest(tmp_path):
    """Identity rendering preserves the published abc digest oracle.

    Hand calculation: ASCII a, b and c each occupy one byte, so the expected
    report size is the length of that literal byte string.
    """
    source = tmp_path / "source.dat"
    source.write_bytes(b"abc")
    paths = []

    def render(inputs, stage):
        paths.append(stage.write("report", inputs.bytes["source"]))
        stage.write("manifest", json.dumps(dict(stage.sha256)).encode())

    runs = [
        build_artifacts(
            {"source": source},
            ["report", "manifest"],
            render,
            expected_sha256={"source": ABC_SHA256},
            staging_parent=tmp_path,
        )
        for _ in ("first", "second")
    ]
    first, second = runs
    assert dict(first.bytes) == dict(second.bytes)
    assert dict(first.sha256) == dict(second.sha256)
    assert first.bytes["report"] == b"abc"
    assert first.sha256["report"] == ABC_SHA256
    assert json.loads(first.bytes["manifest"]) == {"report": ABC_SHA256}
    assert first.inputs.sha256["source"] == ABC_SHA256
    assert first.size["report"] == len(b"abc")
    assert first.algorithm == "sha256"
    assert all(not path.exists() for path in paths)
    for mapping in (first.bytes, first.sha256, first.size):
        with pytest.raises(TypeError):
            mapping["report"] = None


@pytest.mark.parametrize("race", ["input", "output", "missing-output", "symlink"])
@pytest.mark.parametrize("prior", [False, True])
def test_integrity_failure_preserves_all_canonical_outputs(tmp_path, race, prior):
    """A literal old set stays identical; an absent set stays absent on failure."""
    source = tmp_path / "source.dat"
    source.write_bytes(b"abc")
    canonical = {name: tmp_path / name for name in ("report", "table", "manifest")}
    old = {name: ("prior " + name).encode() for name in canonical}
    if prior:
        for name, path in canonical.items():
            path.write_bytes(old[name])

    def render(inputs, stage):
        paths = {name: stage.write(name, inputs.bytes["source"]) for name in canonical}
        if race == "input":
            source.write_bytes(b"changed")
        elif race == "output":
            paths["table"].write_bytes(b"changed")
        elif race == "missing-output":
            paths["table"].unlink()
        else:
            paths["table"].unlink()
            paths["table"].symlink_to(source)

    error = InputIntegrityError if race == "input" else OutputIntegrityError
    with pytest.raises(error):
        result = build_artifacts(
            {"source": source}, canonical, render, staging_parent=tmp_path
        )
        for name, path in canonical.items():
            path.write_bytes(result.bytes[name])
    for name, path in canonical.items():
        if prior:
            assert path.read_bytes() == old[name]
        else:
            assert not path.exists()


def test_binary_pin_mismatch_fails_before_extraction(tmp_path):
    """The published abc oracle cannot attest to the distinct literal xyz."""
    binary = tmp_path / "binary.dat"
    binary.write_bytes(b"xyz")

    def render(inputs, stage):
        pytest.fail("fingerprint mismatch allowed extraction")

    with pytest.raises(InputIntegrityError, match="fingerprint mismatch"):
        build_artifacts(
            {"binary": binary},
            ["report"],
            render,
            expected_sha256={"binary": ABC_SHA256},
            staging_parent=tmp_path,
        )


@pytest.mark.parametrize("mistake", ["missing", "unknown", "duplicate"])
def test_declared_output_set_is_enforced(tmp_path, mistake):
    """A declared report must be written exactly once under its own identity."""

    def render(inputs, stage):
        if mistake == "unknown":
            stage.write("unexpected", b"abc")
        elif mistake == "duplicate":
            stage.write("report", b"abc")
            stage.write("report", b"xyz")

    with pytest.raises(OutputIntegrityError):
        build_artifacts({}, ["report"], render, staging_parent=tmp_path)


def test_caller_exception_is_preserved_and_stage_is_private(tmp_path):
    """Rendering failures propagate without returning publishable bytes.

    On POSIX, group rwx (octal 070) plus other rwx (octal 007) is octal 077.
    A zero bitwise intersection means all those bits are clear. Windows stat
    mode bits do not establish ACL privacy; exception and cleanup checks still
    apply there.
    """
    caller_error = ValueError("synthetic render failure")
    paths = []

    def render(inputs, stage):
        path = stage.write("report", b"abc")
        paths.append(path)
        if os.name == "posix":
            assert path.parent.stat().st_mode & 0o077 == 0
        raise caller_error

    with pytest.raises(ValueError) as caught:
        build_artifacts({}, ["report"], render, staging_parent=tmp_path)
    assert caught.value is caller_error
    assert all(not path.exists() for path in paths)


def test_input_output_and_pin_enumerations_are_captured_before_render(tmp_path):
    """Changing caller containers cannot change the captured contract."""
    source = tmp_path / "source.dat"
    source.write_bytes(b"abc")
    inputs = {"source": source}
    outputs = ["report"]
    pins = {"source": ABC_SHA256}

    def render(frozen, stage):
        inputs.clear()
        outputs.append("unexpected")
        pins["source"] = "invalid"
        stage.write("report", frozen.bytes["source"])

    result = build_artifacts(
        inputs, outputs, render, expected_sha256=pins, staging_parent=tmp_path
    )
    assert dict(result.bytes) == {"report": b"abc"}
    assert dict(result.inputs.bytes) == {"source": b"abc"}


def test_returned_bytes_do_not_reopen_staging_paths(tmp_path):
    """A replacement at a former staging path cannot change returned bytes."""
    paths = []

    def render(inputs, stage):
        paths.append(stage.write("report", b"abc"))

    result = build_artifacts({}, ["report"], render, staging_parent=tmp_path)
    (path,) = paths
    path.parent.mkdir()
    path.write_bytes(b"xyz")
    assert result.bytes["report"] == b"abc"
    assert result.sha256["report"] == ABC_SHA256


def test_output_mutation_during_closing_input_check_is_rejected(tmp_path, monkeypatch):
    """An output changed during input revalidation must not escape the guard."""
    source = tmp_path / "source.dat"
    source.write_bytes(b"abc")
    paths = []
    rehash = input_snapshot._hash_paths

    def closing_hash(inputs):
        hashes = rehash(inputs)
        (path,) = paths
        path.write_bytes(b"changed")
        return hashes

    def render(inputs, stage):
        paths.append(stage.write("report", inputs.bytes["source"]))

    monkeypatch.setattr(input_snapshot, "_hash_paths", closing_hash)
    with pytest.raises(OutputIntegrityError, match="staged output changed"):
        build_artifacts({"source": source}, ["report"], render, staging_parent=tmp_path)


@pytest.mark.parametrize("outputs", [["report", "report"], [""], [None], "report"])
def test_invalid_output_declarations_fail_before_rendering(tmp_path, outputs):
    """Duplicate, empty and non-string identities cannot define an output set."""

    def render(inputs, stage):
        pytest.fail("invalid output declaration reached rendering")

    with pytest.raises((TypeError, ValueError)):
        build_artifacts({}, outputs, render, staging_parent=tmp_path)


def test_staged_hashes_cannot_be_edited_by_renderer(tmp_path):
    """The renderer cannot replace a sealed digest through the public mapping."""

    def render(inputs, stage):
        stage.write("report", b"abc")
        with pytest.raises(TypeError):
            stage.sha256["report"] = "replacement"

    result = build_artifacts({}, ["report"], render, staging_parent=tmp_path)
    assert result.sha256["report"] == ABC_SHA256
