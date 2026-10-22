"""Offline response qualification regressions for issue #1301."""

import hashlib
import json

import pytest

from worldenergydata.modules.state_regulators.fetch import (
    FetchConfig,
    Fetcher,
    TermsCheck,
)
from worldenergydata.modules.state_regulators.fetch.storage import CacheStore


@pytest.mark.parametrize(
    "url,payload,headers,status",
    [
        ("data.csv", b"", {}, 200),
        ("data.csv", b"<html>unavailable</html>", {}, 200),
        ("data.zip", b"failure", {"Content-Type": "text/html"}, 200),
        ("page.aspx", b"<html><title>Server Error</title></html>", {}, 200),
        ("page.aspx", b"<html>error</html>", {}, 200),
        ("page.aspx", b"<html><title>Runtime Error</title></html>", {}, 200),
        ("data.csv", b"<h1>Forbidden</h1>", {}, 200),
        (
            "page.aspx",
            b'{"error":"unavailable"}',
            {"Content-Type": "application/json"},
            200,
        ),
        (
            "data.zip",
            b'{"error": "unavailable"}',
            {"Content-Type": "application/json"},
            200,
        ),
        ("data.csv", b"a,b\n", {}, 503),
    ],
)
def test_invalid_response_never_mutates_cache(tmp_path, url, payload, headers, status):
    """Literal stub bodies are empty, wrong media, or explicit errors.

    RFC 9110 (2022), sections 8.3 and 15.3.1: media describes the representation;
    200 is success. Issue #1301 additionally requires nonempty reusable content.
    """
    store = CacheStore(tmp_path)
    with pytest.raises(ValueError):
        store.put("https://records.example/" + url, payload, headers, {}, status=status)
    assert not list(store.objects.iterdir())
    assert not list(store.records.iterdir())
    assert not store.progress.exists()


@pytest.mark.parametrize("payload", [b"", b"<html>error</html>"])
def test_poisoned_cache_refetched_through_permission_layer(
    tmp_path, monkeypatch, payload
):
    """Hand calculation: one invalid legacy object needs one replacement request.

    A second read needs no request because the replacement CSV is reusable.
    """
    url = "https://records.example/data.csv"
    fetcher = Fetcher(
        FetchConfig(tmp_path, "offline-test"),
        [TermsCheck(url, url, "2020-01-01T00:00:00+00:00", True)],
    )
    store = fetcher.store
    digest = hashlib.sha256(payload).hexdigest()
    (store.objects / digest).write_bytes(payload)
    store._record(url).write_text(
        json.dumps(
            {
                "url": url,
                "sha256": digest,
                "size_bytes": len(payload),
            }
        )
    )
    calls = []

    def request(target):
        calls.append(target)
        return b"a,b\n", {"Content-Type": "text/csv"}

    monkeypatch.setattr(fetcher, "_request", request)
    assert fetcher.fetch(url).path.read_bytes() == b"a,b\n"
    assert fetcher.fetch(url).cached
    assert calls == [url]
    assert (store.objects / digest).read_bytes() == payload
