"""Synthetic, offline oracles for bounded federal lease capture."""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from worldenergydata.landman.blm_capture import (
    MAX_BYTES,
    QUERY_URL,
    Evidence,
    fetch_capture,
    write_capture,
)

RAW = b'{ "features": [{"attributes": {"CSE_NR": "SYNTHETIC"}}], "exceededTransferLimit": true }\n'
CHECKED = datetime(2026, 1, 1, tzinfo=timezone.utc)


def evidence(kind="synthetic", **changes):
    values = dict(
        kind=kind,
        terms_url="https://www.blm.gov/terms",
        terms_note="Synthetic permission evidence; no live permission is asserted.",
        access_note="Synthetic publisher metadata observation.",
        checked_at=CHECKED,
        retention="permitted",
    )
    return Evidence(**(values | changes))


def test_round_trip(tmp_path):
    folder = write_capture(tmp_path, "fixture", RAW, evidence=evidence())
    assert (folder / "response.json").read_bytes() == RAW
    manifest = json.loads((folder / "manifest.json").read_text())
    assert manifest["raw"] == {
        "path": "response.json",
        "sha256": hashlib.sha256(RAW).hexdigest(),
        "size_bytes": len(RAW),
    }
    assert manifest["schema_version"] == 1
    assert manifest["status"] == "captured"
    assert manifest["coverage"] == "partial"
    assert manifest["exceeded_transfer_limit"] is True
    assert manifest["record_count"] == 1
    assert manifest["record_cap"] == 10
    assert manifest["source"]["kind"] == "synthetic"
    assert manifest["source"]["publisher"] == "Bureau of Land Management"
    assert manifest["source"]["url"] == QUERY_URL
    assert manifest["source"]["terms_url"] == evidence().terms_url
    assert manifest["source"]["terms_note"] == evidence().terms_note
    assert manifest["source"]["access_note"] == evidence().access_note
    assert manifest["source"]["checked_at"] == "2026-01-01T00:00:00Z"
    assert manifest["source"]["retention"] == "permitted"
    assert datetime.fromisoformat(
        manifest["captured_at"].replace("Z", "+00:00")
    ).utcoffset() == timedelta(0)


@pytest.mark.parametrize(
    "raw",
    [
        b"not-json",
        b"{}",
        b"[]",
        b'{"error": {}, "features": []}',
        b'{"features": null}',
        b'{"features": [null]}',
        b'{"features": [{"attributes": []}]}',
        b'{"features": [], "exceededTransferLimit": "false"}',
        b'{"features": [], "features": []}',
        b'{"features": [], "extra": NaN}',
        b" " * (MAX_BYTES + 1),
        json.dumps({"features": [{"attributes": {}}] * 11}).encode(),
    ],
)
def test_invalid_payload_leaves_no_capture(tmp_path, raw):
    with pytest.raises(ValueError):
        write_capture(tmp_path, "invalid", raw, evidence=evidence())
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("name", ["../escape", "nested/name", ".", "..", "", "a\\b"])
def test_traversal_rejected(tmp_path, name):
    with pytest.raises(ValueError):
        write_capture(tmp_path, name, RAW, evidence=evidence())
    assert list(tmp_path.iterdir()) == []


def test_root_traversal_and_symlink_rejected(tmp_path):
    with pytest.raises(ValueError):
        write_capture(tmp_path / ".." / "escape", "fixture", RAW, evidence=evidence())
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError):
        write_capture(link, "fixture", RAW, evidence=evidence())
    assert list(target.iterdir()) == []


@pytest.mark.parametrize(
    "url",
    [
        "https://example.invalid/query",
        "https://" + "user:password" + chr(64) + "example.invalid/query",
        QUERY_URL + "&token=synthetic",
        QUERY_URL + "#fragment",
    ],
)
def test_noncanonical_url_rejected(tmp_path, url):
    with pytest.raises(ValueError):
        write_capture(tmp_path, "fixture", RAW, evidence=evidence(), request_url=url)
    assert list(tmp_path.iterdir()) == []


def test_collision_preserves_existing_bytes(tmp_path):
    folder = write_capture(tmp_path, "fixture", RAW, evidence=evidence())
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    with pytest.raises(FileExistsError):
        write_capture(tmp_path, "fixture", b'{"features": []}', evidence=evidence())
    assert {p.name: p.read_bytes() for p in folder.iterdir()} == before


def test_raw_readback_required(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "read_bytes", lambda self: b"tampered")
    with pytest.raises(OSError):
        write_capture(tmp_path, "fixture", RAW, evidence=evidence())
    assert not (tmp_path / "fixture" / "manifest.json").exists()


def test_successful_empty_is_still_partial(tmp_path):
    folder = write_capture(tmp_path, "empty", b'{"features": []}', evidence=evidence())
    manifest = json.loads((folder / "manifest.json").read_text())
    assert manifest["record_count"] == 0
    assert manifest["coverage"] == "partial"
    assert manifest["exceeded_transfer_limit"] is None


@pytest.mark.parametrize(
    "changes",
    [
        {"kind": "unknown"},
        {"retention": "unverified"},
        {"terms_note": ""},
        {"access_note": ""},
        {"terms_url": "https://" + "user:password" + chr(64) + "www.blm.gov/terms"},
        {"terms_url": "https://www.blm.gov/terms?token=synthetic"},
        {"terms_url": "https://example.invalid/terms"},
        {"checked_at": datetime(2026, 1, 1)},
        {"checked_at": datetime.now(timezone.utc) + timedelta(days=1)},
    ],
)
def test_evidence_required_before_network(tmp_path, changes):
    def unexpected(request):
        pytest.fail("Invalid evidence must not trigger a request")

    with httpx.Client(transport=httpx.MockTransport(unexpected)) as client:
        with pytest.raises(ValueError):
            fetch_capture(
                tmp_path,
                "fixture",
                evidence=evidence(**({"kind": "public"} | changes)),
                client=client,
            )
    assert list(tmp_path.iterdir()) == []


def test_synthetic_evidence_cannot_fetch(tmp_path):
    with pytest.raises(ValueError):
        fetch_capture(tmp_path, "fixture", evidence=evidence())


@pytest.mark.parametrize("failure", ["http", "redirect", "timeout", "json", "large"])
def test_fetch_failure_never_creates_inventory(tmp_path, failure):
    def respond(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("Synthetic timeout", request=request)
        if failure == "http":
            return httpx.Response(503)
        if failure == "redirect":
            return httpx.Response(302, headers={"location": "https://example.invalid/"})
        return httpx.Response(
            200, content=b"x" * (MAX_BYTES + 1) if failure == "large" else b"{}"
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises((httpx.HTTPError, ValueError)):
            fetch_capture(
                tmp_path, "fixture", evidence=evidence("public"), client=client
            )
    assert list(tmp_path.iterdir()) == []


def test_single_request_has_fixed_bounds(tmp_path):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, content=RAW)

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        folder = fetch_capture(
            tmp_path, "fixture", evidence=evidence("public"), client=client
        )
    assert len(calls) == 1
    assert str(calls[0].url) == QUERY_URL
    assert calls[0].url.params["resultRecordCount"] == "10"
    assert calls[0].extensions["timeout"]["read"] == 15.0
    assert (folder / "response.json").read_bytes() == RAW
