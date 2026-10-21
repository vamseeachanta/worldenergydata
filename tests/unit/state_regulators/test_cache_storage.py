"""Cache payload contract from issue #1301: empty responses are never reusable."""

import hashlib
import json

import pytest

from worldenergydata.modules.state_regulators.fetch.storage import CacheStore


def test_empty_put_preserves_existing_cache(tmp_path):
    """Hand check: b'' contains no bytes; rejection must precede every write."""
    store = CacheStore(tmp_path)
    url = "https://records.example.org/data"
    store.put(url, b"records", {}, {})
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}

    with pytest.raises(ValueError, match="empty payload"):
        store.put(url, b"", {}, {})

    assert {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before
    assert store.get(url).path.read_bytes() == b"records"


def test_empty_put_creates_no_cache_evidence(tmp_path):
    """Hand check: the empty byte string has no content to retain or complete."""
    store = CacheStore(tmp_path)
    with pytest.raises(ValueError, match="empty payload"):
        store.put("https://records.example.org/data", b"", {}, {})
    assert not list(store.objects.iterdir())
    assert not list(store.records.iterdir())
    assert not store.progress.exists()
    assert store.state == {"completed": {}, "hosts": {}}


def test_legacy_empty_cache_is_refused_and_preserved(tmp_path):
    """Build legacy evidence independently: length of b'' is zero by definition."""
    store = CacheStore(tmp_path)
    url = "https://records.example.org/data"
    digest = hashlib.sha256(b"").hexdigest()
    path = store.objects / digest
    path.write_bytes(b"")
    record = store.records / (hashlib.sha256(url.encode()).hexdigest() + ".json")
    record.write_text(
        json.dumps({"url": url, "sha256": digest, "size_bytes": len(b"")})
    )
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}

    with pytest.raises(ValueError, match="empty payload"):
        store.get(url)

    assert {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("payload", [b"x", b"records", b"\x00", b" "])
def test_nonempty_payload_round_trip(tmp_path, payload):
    """Expected bytes are the literal input, independent of cache implementation."""
    store = CacheStore(tmp_path)
    url = "https://records.example.org/data"
    result = store.put(url, payload, {}, {})
    assert not result.cached
    cached = CacheStore(tmp_path).get(url)
    assert cached.cached
    assert cached.path.read_bytes() == payload
    assert cached.metadata["size_bytes"] == len(payload)
