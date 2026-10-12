"""Synthetic build lifecycle checks for frozen input bytes and hashes."""

import importlib
import importlib.util
from hashlib import sha256

import pytest


def _freeze(inputs, **kwargs):
    name = "worldenergydata.common.input_snapshot"
    assert (
        importlib.util.find_spec(name) is not None
    ), "shared snapshot helper is absent"
    return importlib.import_module(name).freeze_inputs(inputs, **kwargs)


def test_source_mutation_between_render_and_manifest_fails(tmp_path):
    source = tmp_path / "source.dat"
    source.write_bytes(b"original synthetic bytes")
    output = tmp_path / "output.dat"
    output.write_bytes(b"previous result")
    with pytest.raises(ValueError, match="input changed"):
        with _freeze({"source": source}) as frozen:
            rendered = frozen.bytes["source"].upper()
            source.write_bytes(b"replacement synthetic bytes")
            manifest = dict(frozen.sha256)
        output.write_bytes(rendered)
    assert output.read_bytes() == b"previous result"
    assert manifest["source"] == sha256(b"original synthetic bytes").hexdigest()


def test_external_binary_fingerprint_mismatch_blocks_render_and_publication(tmp_path):
    source = tmp_path / "binary.dat"
    source.write_bytes(b"live synthetic binary")
    rendered = published = False
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        with _freeze(
            {"binary": source},
            expected_sha256={
                "binary": sha256(b"different synthetic binary").hexdigest()
            },
        ):
            rendered = True
        published = True
    assert not rendered
    assert not published


def test_steady_state_hashes_match_synthetic_bytes_in_two_runs(tmp_path):
    source = tmp_path / "source.dat"
    binary = tmp_path / "binary.dat"
    source.write_bytes(b"synthetic text")
    binary.write_bytes(b"\x00\xffsynthetic binary")
    expected = {
        "source": sha256(b"synthetic text").hexdigest(),
        "binary": sha256(b"\x00\xffsynthetic binary").hexdigest(),
    }
    runs = []
    for _ in range(2):
        with _freeze(
            {"source": source, "binary": binary}, expected_sha256=expected
        ) as frozen:
            runs.append(dict(frozen.sha256))
            assert frozen.bytes["source"] == b"synthetic text"
            assert frozen.bytes["binary"] == b"\x00\xffsynthetic binary"
    assert runs == [expected, expected]


def test_render_reads_frozen_bytes_after_live_source_changes(tmp_path):
    source = tmp_path / "source.dat"
    source.write_bytes(b"original")
    with pytest.raises(ValueError, match="input changed"):
        with _freeze({"source": source}) as frozen:
            source.write_bytes(b"replacement")
            assert frozen.bytes["source"] == b"original"
            assert frozen.sha256["source"] == sha256(b"original").hexdigest()


def test_snapshot_byte_and_hash_maps_are_immutable(tmp_path):
    source = tmp_path / "source.dat"
    source.write_bytes(b"synthetic")
    with _freeze({"source": source}) as frozen:
        with pytest.raises(TypeError):
            frozen.bytes["source"] = b"replacement"
        with pytest.raises(TypeError):
            frozen.sha256["source"] = sha256(b"replacement").hexdigest()


def test_deleted_input_fails_revalidation(tmp_path):
    source = tmp_path / "source.dat"
    source.write_bytes(b"synthetic")
    with pytest.raises(ValueError, match="input unavailable"):
        with _freeze({"source": source}):
            source.unlink()


def test_caller_mapping_edits_cannot_replace_captured_inputs(tmp_path):
    original = tmp_path / "original.dat"
    replacement = tmp_path / "replacement.dat"
    original.write_bytes(b"original")
    replacement.write_bytes(b"replacement")
    inputs = {"source": original}
    with pytest.raises(ValueError, match="input changed"):
        with _freeze(inputs) as frozen:
            inputs["source"] = replacement
            inputs["new"] = replacement
            original.write_bytes(b"changed")
            assert dict(frozen.bytes) == {"source": b"original"}


def test_unknown_fingerprint_identity_fails_before_render(tmp_path):
    source = tmp_path / "source.dat"
    source.write_bytes(b"synthetic")
    rendered = False
    with pytest.raises(ValueError, match="unknown fingerprint"):
        with _freeze(
            {"source": source},
            expected_sha256={"missing": sha256(b"synthetic").hexdigest()},
        ):
            rendered = True
    assert not rendered
