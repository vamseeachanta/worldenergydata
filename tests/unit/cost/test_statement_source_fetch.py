"""Synthetic transport only: no live requests in CI."""

import hashlib
import io
from urllib.error import HTTPError

import pytest

from worldenergydata.cost.data_collection.statement_source_fetch import fetch_source


class SyntheticResponse(io.BytesIO):
    status = 200
    headers = {"Content-Type": "text/plain"}


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("network forbidden")

    monkeypatch.setattr("urllib.request.OpenerDirector.open", forbidden)


def test_bounded_fetch_metadata_and_timeout(monkeypatch):
    calls = []

    def transport(request, timeout):
        calls.append((request, timeout))
        return SyntheticResponse(b"synthetic source")

    pauses = []
    monkeypatch.setattr("time.sleep", pauses.append)
    result, data = fetch_source("https://example.org/robots.txt", transport=transport)
    assert data == b"synthetic source"
    assert result["size_bytes"] == len(data)
    assert result["sha256"] == hashlib.sha256(data).hexdigest()
    assert result["http_status"] == 200
    assert result["retrieved_at_utc"].endswith("Z")
    assert calls[0][1] == 30
    assert "https://github.com/vamseeachanta/worldenergydata" in calls[0][0].get_header(
        "User-agent"
    )
    assert pauses == [2]


def test_response_cap(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    with pytest.raises(ValueError, match="size limit"):
        fetch_source(
            "https://example.org/robots.txt",
            max_bytes=3,
            transport=lambda request, timeout: SyntheticResponse(b"1234"),
        )


def test_refusal_no_retry_or_server_wait(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda seconds: None)

    def refused(request, timeout):
        raise HTTPError(
            request.full_url,
            429,
            "Synthetic refusal",
            {"Retry-After": "9999"},
            io.BytesIO(b"refused"),
        )

    result, data = fetch_source("https://example.org/robots.txt", transport=refused)
    assert result["http_status"] == 429
    assert data == b"refused"


def test_default_transport_blocked(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    with pytest.raises(AssertionError, match="network forbidden"):
        fetch_source("https://example.org/robots.txt")


@pytest.mark.parametrize("status", [301, 302, 403])
def test_redirect_or_refusal_is_returned_once(monkeypatch, status):
    monkeypatch.setattr("time.sleep", lambda seconds: None)

    def refused(request, timeout):
        raise HTTPError(
            request.full_url,
            status,
            "Synthetic response",
            {"Location": "https://example.org/other"},
            io.BytesIO(b"synthetic"),
        )

    result, data = fetch_source("https://example.org/source", transport=refused)
    assert result["http_status"] == status
    assert result["size_bytes"] == len(data)


@pytest.mark.parametrize("limit", [0, -1, 30_000_001])
def test_invalid_limit_prevents_request(limit):
    with pytest.raises(ValueError, match="size limit"):
        fetch_source("https://example.org/source", max_bytes=limit)
