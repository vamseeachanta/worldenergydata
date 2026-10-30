"""Offline contracts exercised through fetch_series and the live transport.

Fixture basis: issue #1606 specifies offsets 0 and 2, pages [1, 2] and [3],
and 3600 requests/hour with calls 0.25 seconds apart. These are synthetic
identifiers and counts, not API pagination guarantees. Independent arithmetic:
3600 seconds/hour / 3600 requests/hour = 1 second/request; 1 - 0.25 = 0.75.
Other numbers are synthetic fixture inputs; call counts enumerate the explicit
miss/hit traces below. HTTP statuses use HTTPStatus (RFC 9110, section 15;
RFC 6585, section 4 for TOO_MANY_REQUESTS). No production data is used.
"""

import socket
import traceback
from http import HTTPStatus
from types import SimpleNamespace

import pytest
import requests

from worldenergydata.eia_us.client import eia_api
from worldenergydata.eia_us.client.eia_api import (
    EIAApiClient,
    EIAApiError,
    EIARateLimitError,
)

SERIES = "PET.MCRFPUS2.M"
# Deliberately synthetic markers used only to detect diagnostic disclosure.
AUTH_MARKER = "synthetic-auth-marker"
BODY_MARKER = "synthetic-response-marker"


class FakeClock:
    """Synthetic origin 10 seconds; sleep advances time without waiting."""

    def __init__(self):
        self.now = 10.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


class FakeResponse:
    def __init__(self, payload, status=HTTPStatus.OK):
        self.payload = payload
        self.status_code = status
        self.text = BODY_MARKER

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


def page(values):
    return FakeResponse(
        {
            "response": {
                "data": [
                    {"period": "synthetic-period", "value": str(value), "unit": "unit"}
                    for value in values
                ]
            }
        }
    )


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    """Fail on DNS, socket connection, or a bypass of the fake requests.get."""
    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append(True)
        pytest.fail("Real network transport is forbidden")

    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(requests.sessions.Session, "request", forbidden)
    yield
    assert attempts == []


@pytest.fixture
def transport(monkeypatch, caplog):
    caplog.set_level("DEBUG", logger=eia_api.__name__)
    clock = FakeClock()
    monkeypatch.setattr(eia_api, "time", clock)
    replies = []
    calls = []

    def get(url, *, params, timeout):
        calls.append((url, dict(params), timeout))
        assert replies, "Unexpected transport call"
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(requests, "get", get)
    return SimpleNamespace(clock=clock, replies=replies, calls=calls)


@pytest.mark.parametrize("mock_first", [True, False])
def test_mock_live_cache_separation(transport, mock_first):
    """Both orders on one client: each mode misses once, then hits itself."""
    client = EIAApiClient(api_key=AUTH_MARKER)
    transport.replies.append(page([1]))
    modes = [mock_first, not mock_first, mock_first, not mock_first]
    results = {}
    for use_mock in modes:
        records = client.fetch_series(SERIES, use_mock=use_mock)
        if use_mock in results:
            assert records is results[use_mock]
        results[use_mock] = records
    assert results[False] == [
        {"period": "synthetic-period", "value": 1.0, "unit": "unit"}
    ]
    assert results[True] != results[False]
    assert len(transport.calls) == 1
    assert client.generate_cache_key(SERIES, {}, use_mock=True) != (
        client.generate_cache_key(SERIES, {}, use_mock=False)
    )


def test_offset_parameter_cache_isolation(transport):
    """Explicit pages miss separately; reordered identical parameters hit."""
    client = EIAApiClient(api_key=AUTH_MARKER)
    first = {"offset": 0, "length": 2}
    second = {"offset": 2, "length": 2}
    transport.replies.extend([page([1, 2]), page([3])])
    assert client.generate_cache_key(SERIES, first) != client.generate_cache_key(
        SERIES, second
    )
    first_records = client.fetch_series(SERIES, first)
    second_records = client.fetch_series(SERIES, second)
    assert [record["value"] for record in first_records] == [1.0, 2.0]
    assert [record["value"] for record in second_records] == [3.0]
    reordered = {"length": 2, "offset": 0}
    assert client.generate_cache_key(SERIES, reordered) == client.generate_cache_key(
        SERIES, first
    )
    assert client.fetch_series(SERIES, reordered) is first_records
    assert client.fetch_series(SERIES, second) is second_records
    assert [query["offset"] for _, query, _ in transport.calls] == [0, 2]
    assert all(query["length"] == 2 for _, query, _ in transport.calls)
    assert first == {"offset": 0, "length": 2}
    assert second == {"offset": 2, "length": 2}


@pytest.mark.parametrize("use_mock", [False, True])
def test_cache_ttl_boundary(transport, use_mock):
    """Synthetic TTL 2 seconds: hit at +1, expire at +1+1 = +2."""
    client = EIAApiClient(api_key=AUTH_MARKER, cache_ttl=2)
    transport.replies.extend([page([1]), page([2])])
    initial = client.fetch_series(SERIES, use_mock=use_mock)
    transport.clock.now += 1
    assert client.fetch_series(SERIES, use_mock=use_mock) is initial
    transport.clock.now += 1
    refreshed = client.fetch_series(SERIES, use_mock=use_mock)
    assert refreshed is not initial
    assert client.fetch_series(SERIES, use_mock=use_mock) is refreshed
    assert len(transport.calls) == (0 if use_mock else 2)


def test_success_and_explicit_empty_data(transport):
    client = EIAApiClient(api_key=AUTH_MARKER, base_url="https://example.invalid/v2/")
    transport.replies.extend([page([1]), page([])])
    assert client.fetch_series(SERIES) == [
        {"period": "synthetic-period", "value": 1.0, "unit": "unit"}
    ]
    assert client.fetch_series(SERIES, {"offset": 2}) == []
    assert client.fetch_series(SERIES, {"offset": 2}) == []
    assert len(transport.calls) == 2
    url, query, timeout = transport.calls[0]
    assert url == f"https://example.invalid/v2/seriesid/{SERIES}"
    assert query == {"api_key": AUTH_MARKER}
    # Existing transport contract: 30-second timeout, not a rate calculation.
    assert timeout == 30


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"response": {}},
        {"response": None},
        {"response": []},
        {"response": {"data": None}},
        {"response": {"data": {}}},
        {"response": {"data": BODY_MARKER}},
        [],
        ValueError(BODY_MARKER),
    ],
)
def test_malformed_success_never_cached(transport, payload, caplog):
    client = EIAApiClient(api_key=AUTH_MARKER)
    transport.replies.extend([FakeResponse(payload), page([])])
    with pytest.raises(EIAApiError) as caught:
        client.fetch_series(SERIES)
    assert client.cache.get(client.generate_cache_key(SERIES, {})) is None
    diagnostic = "".join(traceback.format_exception(caught.value)) + caplog.text
    assert AUTH_MARKER not in diagnostic
    assert BODY_MARKER not in diagnostic
    assert client.fetch_series(SERIES) == []
    assert client.fetch_series(SERIES) == []
    assert len(transport.calls) == 2


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (HTTPStatus.TOO_MANY_REQUESTS, EIARateLimitError),
        (HTTPStatus.BAD_REQUEST, EIAApiError),
        (HTTPStatus.UNAUTHORIZED, EIAApiError),
        (HTTPStatus.INTERNAL_SERVER_ERROR, EIAApiError),
    ],
)
def test_transport_status_contract(transport, caplog, status, error):
    client = EIAApiClient(api_key=AUTH_MARKER)
    transport.replies.extend([FakeResponse({}, status), page([])])
    with pytest.raises(error) as caught:
        client.fetch_series(SERIES)
    diagnostic = "".join(traceback.format_exception(caught.value)) + caplog.text
    assert AUTH_MARKER not in diagnostic
    assert BODY_MARKER not in diagnostic
    assert client.cache.get(client.generate_cache_key(SERIES, {})) is None
    assert client.fetch_series(SERIES) == []
    assert client.fetch_series(SERIES) == []
    assert len(transport.calls) == 2


@pytest.mark.parametrize("exception", [requests.Timeout, requests.ConnectionError])
def test_transport_exception_never_cached(transport, caplog, exception):
    client = EIAApiClient(api_key=AUTH_MARKER)
    transport.replies.extend([exception(f"{AUTH_MARKER} {BODY_MARKER}"), page([])])
    with pytest.raises(EIAApiError) as caught:
        client.fetch_series(SERIES)
    diagnostic = "".join(traceback.format_exception(caught.value)) + caplog.text
    assert AUTH_MARKER not in diagnostic
    assert BODY_MARKER not in diagnostic
    assert client.cache.get(client.generate_cache_key(SERIES, {})) is None
    assert client.fetch_series(SERIES) == []
    assert client.fetch_series(SERIES) == []
    assert len(transport.calls) == 2


def test_configured_request_spacing(transport):
    """Independent hand calculation: interval 1 second, wait 0.75 seconds."""
    client = EIAApiClient(api_key=AUTH_MARKER, rate_limit_per_hour=3600)
    transport.replies.extend([page([1]), page([2])])
    client.fetch_series(SERIES, {"offset": 0})
    assert transport.clock.sleeps == []
    transport.clock.now += 0.25
    client.fetch_series(SERIES, {"offset": 2})
    assert transport.clock.sleeps == [0.75]
    assert transport.clock.now == 11.0  # Synthetic origin 10 + interval 1.
    assert len(transport.calls) == 2
