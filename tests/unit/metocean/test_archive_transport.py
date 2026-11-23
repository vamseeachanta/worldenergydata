"""Offline transport tests; every response is supplied by MockTransport."""

import gzip
import socket
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import httpx
import pytest

from worldenergydata.metocean.clients import archive_transport as module


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("A real network connection was attempted")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(module, "_HOSTS", {})


class Clock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def __call__(self):
        return self.now

    def sleep(self, delay):
        self.sleeps.append(delay)
        self.now += delay


def make_transport(handler, **kwargs):
    clock = Clock()
    client = httpx.Client(transport=httpx.MockTransport(handler))
    transport = module.ArchiveTransport(
        client=client,
        clock=clock,
        sleep=clock.sleep,
        utcnow=lambda: datetime(2025, 1, 1, tzinfo=timezone.utc),
        **kwargs,
    )
    return transport, clock, client


def test_download_is_immutable_and_counts_decoded_bytes():
    payload = b"wave height\n" * 100
    transport, _, client = make_transport(
        lambda request: httpx.Response(
            200,
            content=gzip.compress(payload),
            headers={"Content-Encoding": "gzip", "ETag": "archive-v1"},
        )
    )
    result = transport.download("https://example.test/archive")
    assert result.content == payload
    assert result.headers["etag"] == "archive-v1"
    assert result.fetched_at == datetime(2025, 1, 1, tzinfo=timezone.utc)
    assert transport.bytes_downloaded == len(payload)
    assert transport.requests_by_host == {"example.test": 1}
    with pytest.raises(FrozenInstanceError):
        result.content = b"changed"
    with pytest.raises(TypeError):
        result.headers["etag"] = "changed"
    transport.close()
    assert not client.is_closed
    client.close()


@pytest.mark.parametrize("status", [301, 302, 401, 403, 404])
def test_refusal_and_redirect_are_never_retried(status):
    transport, clock, client = make_transport(
        lambda request: httpx.Response(status, headers={"Location": "/other"})
    )
    with pytest.raises(httpx.HTTPStatusError):
        transport.download("https://example.test/archive")
    assert transport.requests_by_host == {"example.test": 1}
    assert clock.sleeps == []
    client.close()


@pytest.mark.parametrize(
    "retry_after,minimum",
    [("75", 75), ("Wed, 01 Jan 2025 00:02:00 GMT", 120), ("invalid", 60)],
)
def test_temporary_failure_respects_retry_after(retry_after, minimum):
    responses = iter([429, 200])
    transport, clock, client = make_transport(
        lambda request: httpx.Response(
            next(responses), headers={"Retry-After": retry_after}, content=b"ok"
        )
    )
    assert transport.download("https://example.test/archive").content == b"ok"
    assert clock.sleeps[0] >= minimum
    assert transport.requests_by_host == {"example.test": 2}
    client.close()


def test_temporary_retries_are_bounded():
    transport, clock, client = make_transport(lambda request: httpx.Response(503))
    with pytest.raises(httpx.HTTPStatusError):
        transport.download("https://example.test/archive")
    assert transport.requests_by_host == {"example.test": 3}
    assert clock.sleeps == [60, 120]
    client.close()


def test_connection_failure_is_not_server_authorized_retry():
    def handler(request):
        raise httpx.ConnectError("unavailable", request=request)

    transport, clock, client = make_transport(handler)
    with pytest.raises(httpx.ConnectError):
        transport.download("https://example.test/archive")
    assert transport.requests_by_host == {"example.test": 1}
    assert clock.sleeps == []
    client.close()


def test_conditional_request_and_no_inherited_authentication():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(304)

    transport, _, client = make_transport(handler)
    client.auth = httpx.BasicAuth("synthetic", "synthetic")
    client.cookies.set("synthetic", "synthetic")
    result = transport.download(
        "https://example.test/archive", headers={"If-None-Match": "v1"}
    )
    assert result.status_code == 304
    assert result.content == b""
    assert seen[0].headers["if-none-match"] == "v1"
    assert "authorization" not in seen[0].headers
    assert "cookie" not in seen[0].headers
    assert seen[0].headers["user-agent"] == module.USER_AGENT
    client.close()


def test_host_rate_is_shared_across_instances():
    transport, clock, client = make_transport(lambda request: httpx.Response(200))
    other = module.ArchiveTransport(client=client, sleep=clock.sleep, clock=clock)
    transport.download("https://example.test/one")
    other.download("https://example.test/two")
    assert clock.sleeps == [1.1]
    client.close()


@pytest.mark.parametrize("kwargs", [{"max_file_bytes": 4}, {"max_total_bytes": 4}])
def test_decoded_payload_limit(kwargs):
    transport, _, client = make_transport(
        lambda request: httpx.Response(
            200,
            content=gzip.compress(b"oversized"),
            headers={"Content-Encoding": "gzip"},
        ),
        **kwargs,
    )
    with pytest.raises(module.ArchiveLimitError):
        transport.download("https://example.test/archive")
    client.close()


def test_request_budget_prevents_request():
    transport, _, client = make_transport(
        lambda request: httpx.Response(200), max_requests_per_host=1
    )
    transport.download("https://example.test/one")
    with pytest.raises(module.ArchiveLimitError):
        transport.download("https://example.test/two")
    assert transport.requests_by_host == {"example.test": 1}
    client.close()


def test_exhausted_run_budget_prevents_request():
    transport, _, client = make_transport(
        lambda request: httpx.Response(200, content=b"four"), max_total_bytes=4
    )
    transport.download("https://example.test/one")
    with pytest.raises(module.ArchiveLimitError):
        transport.download("https://example.test/two")
    assert transport.requests_by_host == {"example.test": 1}
    client.close()


@pytest.mark.parametrize(
    "url",
    [
        "http://example.test/data",
        "https://synthetic@example.test/data",
        "https:///data",
        "https://example.test/data#fragment",
    ],
)
def test_invalid_url_fails_before_request(url):
    transport, _, client = make_transport(lambda request: pytest.fail("requested"))
    with pytest.raises(ValueError):
        transport.download(url)
    client.close()


def test_arbitrary_headers_are_rejected():
    transport, _, client = make_transport(lambda request: pytest.fail("requested"))
    with pytest.raises(ValueError):
        transport.download("https://example.test/data", headers={"Cookie": "synthetic"})
    client.close()


def test_owned_client_closed_and_use_after_close_rejected():
    transport = module.ArchiveTransport()
    transport.close()
    assert transport.client.is_closed
    with pytest.raises(RuntimeError):
        transport.download("https://example.test/data")
