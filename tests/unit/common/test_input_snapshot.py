"""Synthetic build lifecycle checks for frozen input bytes and hashes."""

import importlib
import importlib.util
from hashlib import sha256

import pytest

from worldenergydata.common import input_snapshot


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
            assert frozen.algorithm == "sha256"
            assert dict(frozen.size) == {
                identity: len(raw) for identity, raw in frozen.bytes.items()
            }
            with pytest.raises(TypeError):
                frozen.size["source"] = 0
            assert frozen.bytes["source"] == b"synthetic text"
            assert frozen.bytes["binary"] == b"\x00\xffsynthetic binary"
    assert runs == [expected, expected]


def test_alias_identities_keep_independent_fingerprints(tmp_path):
    """Aliases retain separate entries for identical fixture bytes.

    Hand count: ``shared`` has six ASCII letters; one LF makes seven bytes.
    Digest reference: SHA-256, computed independently with hashlib.sha256.
    """
    source = tmp_path / "shared.dat"
    source.write_bytes(b"shared\n")
    pins = {
        "first": sha256(b"shared\n").hexdigest(),
        "second": sha256(b"shared\n").hexdigest(),
    }
    with _freeze({"first": source, "second": source}, expected_sha256=pins) as frozen:
        assert dict(frozen.bytes) == {"first": b"shared\n", "second": b"shared\n"}
        assert dict(frozen.size) == {"first": 7, "second": 7}
        assert dict(frozen.sha256) == pins


def test_alias_pin_mismatch_prevents_entry(tmp_path):
    """Only the later alias pin differs; SHA-256 pins use literal fixtures."""
    source = tmp_path / "shared.dat"
    source.write_bytes(b"shared\n")
    pins = {
        "first": sha256(b"shared\n").hexdigest(),
        "second": sha256(b"shared\n").hexdigest(),
    }
    pins["second"] = sha256(b"different\n").hexdigest()
    entered = False
    output = tmp_path / "published.dat"
    with pytest.raises(input_snapshot.InputIntegrityError) as caught:
        with _freeze({"first": source, "second": source}, expected_sha256=pins):
            entered = True
        output.write_bytes(b"published")
    assert caught.value.reason == "pin-mismatch"
    assert caught.value.identity == "second"
    assert not entered
    assert not output.exists()


def test_missing_later_input_prevents_entry(tmp_path):
    """A missing later input blocks context entry and publication."""
    source = tmp_path / "source.dat"
    source.write_bytes(b"shared\n")
    absent = tmp_path / "absent.dat"
    entered = False
    output = tmp_path / "published.dat"
    with pytest.raises(input_snapshot.InputIntegrityError) as caught:
        with _freeze({"first": source, "absent": absent}):
            entered = True
        output.write_bytes(b"published")
    assert caught.value.reason == "unreadable"
    assert caught.value.identity == "absent"
    assert not entered
    assert not output.exists()


def test_empty_inputs_yield_empty_immutable_maps():
    """Empty inputs yield empty maps that reject insertion."""
    with _freeze({}) as frozen:
        assert frozen.algorithm == "sha256"
        for result, value in (
            (frozen.bytes, b"x"),
            (frozen.size, len(b"x")),
            (frozen.sha256, sha256(b"x").hexdigest()),
        ):
            assert dict(result) == {}
            with pytest.raises(TypeError):
                result["added"] = value
            assert dict(result) == {}


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


@pytest.mark.parametrize("changed", [False, True])
def test_closing_hash_reads_multiple_chunks(tmp_path, monkeypatch, changed):
    """A source spanning several chunks is revalidated by content."""
    monkeypatch.setattr(input_snapshot, "_HASH_CHUNK_SIZE", 8)
    source = tmp_path / "source.dat"
    source.write_bytes(b"synthetic" * 4)
    if changed:
        with pytest.raises(ValueError, match="input changed"):
            with _freeze({"source": source}):
                source.write_bytes(b"replacement" * 4)
    else:
        with _freeze({"source": source}) as frozen:
            assert frozen.bytes["source"] == b"synthetic" * 4


def test_closing_check_does_not_repeat_whole_file_read(tmp_path, monkeypatch):
    """Only the entry capture uses Path.read_bytes."""
    source = tmp_path / "source.dat"
    source.write_bytes(b"synthetic")
    read_bytes = type(source).read_bytes
    reads = []

    def read_once(path):
        reads.append(path)
        assert len(reads) == 1, "closing check repeated whole-file read"
        return read_bytes(path)

    monkeypatch.setattr(type(source), "read_bytes", read_once)
    with _freeze({"source": source}):
        pass
    assert reads == [source]


@pytest.mark.parametrize(
    ("failure", "reason"),
    [
        ("missing-entry", "unreadable"),
        ("directory-entry", "unreadable"),
        ("unknown", "unknown-identity"),
        ("pin", "pin-mismatch"),
        ("changed", "changed"),
        ("missing-exit", "unavailable"),
    ],
)
def test_integrity_failure_has_reason_and_identity(tmp_path, failure, reason):
    """Each integrity failure can be distinguished from caller errors."""
    source = tmp_path / "source.dat"
    source.write_bytes(b"synthetic")
    pins = None
    if failure == "missing-entry":
        source.unlink()
    elif failure == "directory-entry":
        source = tmp_path
    elif failure == "unknown":
        pins = {"missing": sha256(b"synthetic").hexdigest()}
    elif failure == "pin":
        pins = {"source": sha256(b"different").hexdigest()}
    with pytest.raises(ValueError) as caught:
        with _freeze({"source": source}, expected_sha256=pins):
            if failure == "changed":
                source.write_bytes(b"changed")
            elif failure == "missing-exit":
                source.unlink()
    assert isinstance(caught.value, input_snapshot.InputIntegrityError)
    assert caught.value.reason == reason
    assert caught.value.identity == ("missing" if failure == "unknown" else "source")


def test_caller_value_error_is_not_integrity_failure(tmp_path):
    """A caller exception propagates unchanged without closing revalidation."""
    source = tmp_path / "source.dat"
    source.write_bytes(b"synthetic")
    caller_error = ValueError("synthetic rendering failure")
    with pytest.raises(ValueError) as caught:
        with _freeze({"source": source}):
            source.unlink()
            raise caller_error
    assert caught.value is caller_error
    assert not isinstance(caught.value, input_snapshot.InputIntegrityError)


@pytest.mark.parametrize("case", ["upper", "mixed"])
def test_correct_hex_pin_accepts_letter_case(tmp_path, case):
    """Valid hexadecimal pins are compared without case sensitivity."""
    source = tmp_path / "source.dat"
    source.write_bytes(b"synthetic")
    digest = sha256(b"synthetic").hexdigest()
    pin = digest.upper() if case == "upper" else digest[:32].upper() + digest[32:]
    with _freeze({"source": source}, expected_sha256={"source": pin}) as frozen:
        assert frozen.sha256["source"] == digest


@pytest.mark.parametrize(
    "invalid", ["wrong-upper", "short", "nonhex", "space", "prefix"]
)
def test_invalid_pin_fails_closed(tmp_path, invalid):
    """Wrong or malformed pins fail before any frozen bytes are yielded."""
    source = tmp_path / "source.dat"
    source.write_bytes(b"synthetic")
    digest = sha256(b"synthetic").hexdigest()
    pin = {
        "wrong-upper": sha256(b"different").hexdigest().upper(),
        "short": digest[:-1],
        "nonhex": "g" + digest[1:],
        "space": " " + digest,
        "prefix": "0x" + digest,
    }[invalid]
    with pytest.raises(ValueError, match="fingerprint mismatch") as caught:
        with _freeze({"source": source}, expected_sha256={"source": pin}):
            pytest.fail("invalid pin reached the caller")
    assert isinstance(caught.value, input_snapshot.InputIntegrityError)
    assert caught.value.reason == "pin-mismatch"
    assert caught.value.identity == "source"
