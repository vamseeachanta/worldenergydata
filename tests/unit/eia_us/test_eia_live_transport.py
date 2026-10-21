"""Offline contracts for the real transport path; no EIA credentials or network.

Source: EIA API Technical Documentation, APIv2 (accessed 2026-10-21),
"Parameters", "Length and offset", and "Understanding returned error codes":
https://www.eia.gov/opendata/documentation.php
HTTP statuses: RFC 9110 (2022), section 15; RFC 6585 (2012), section 4.
Numbers in synthetic fixtures are inputs, not observed energy measurements.
"""

from http import HTTPStatus
from unittest.mock import Mock

import pytest
import requests

from worldenergydata.eia_us.client import eia_api
from worldenergydata.eia_us.client.eia_api import (
    EIAApiClient,
    EIAApiError,
    EIARateLimitError,
)

SERIES = "PET.MCRFPUS2.M"
LIVE_ROWS = [{"period": "2024-01", "value": "7", "unit": "synthetic"}]
PARSED_ROWS = [{"period": "2024-01", "value": 7.0, "unit": "synthetic"}]


@pytest.fixture(autouse=True)
def transport(monkeypatch):
    """Every transport call is intercepted, including unexpected ones."""
    get = Mock(return_value=Mock(status_code=HTTPStatus.OK))
    get.return_value.json.return_value = {"response": {"data": LIVE_ROWS}}
    monkeypatch.setattr(requests, "get", get)
    return get


@pytest.fixture
def clock(monkeypatch):
    """A monotonic clock starting at zero; sleeping advances it without waiting."""
    now = [0.0]
    sleeps = []

    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    monkeypatch.setattr(eia_api.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(eia_api.time, "sleep", sleep)
    return now, sleeps


@pytest.mark.parametrize("mock_first", [True, False])
def test_cache_modes_are_isolated_in_both_orders(transport, clock, mock_first):
    """Trace: populate each mode, revisit each; only the first live call sends GET.

    The live value is float('7') = 7.0 by hand, unlike built-in mock records.
    """
    client = EIAApiClient(api_key="TEST_KEY")
    results = {}
    for mode in (mock_first, not mock_first, mock_first, not mock_first):
        rows = client.fetch_series(SERIES, use_mock=mode)
        if mode in results:
            assert rows == results[mode]
        results[mode] = rows
    assert results[False] == PARSED_ROWS
    assert results[True] != results[False]
    assert transport.call_count == 1
    assert clock[1] == []


def test_cache_key_namespace_and_parameter_order():
    """Same mapping -> same key; either a different mode or page -> another key."""
    client = EIAApiClient(api_key="TEST_KEY")
    params = {"offset": 0, "length": 2}
    live = client.generate_cache_key(SERIES, params)
    assert live == client.generate_cache_key(SERIES, {"length": 2, "offset": 0})
    assert live != client.generate_cache_key(SERIES, params, use_mock=True)
    assert live != client.generate_cache_key(SERIES, {"offset": 2, "length": 2})
    assert live != client.generate_cache_key(SERIES, {"offset": 0, "length": 1})


@pytest.mark.parametrize("use_mock", [True, False])
def test_cache_disabled_never_reads_or_writes(transport, use_mock):
    """Two uncached live fetches require two GETs; mock fetches require none."""
    client = EIAApiClient(
        api_key="TEST_KEY", cache_enabled=False, rate_limit_per_hour=0
    )
    cache_key = client.generate_cache_key(SERIES, {}, use_mock=use_mock)
    sentinel = [{"period": "sentinel", "value": None}]
    client.cache.set(cache_key, sentinel)
    for _ in range(2):
        assert client.fetch_series(SERIES, use_mock=use_mock) != sentinel
    assert client.cache.get(cache_key) == sentinel
    assert transport.call_count == (0 if use_mock else 2)


def test_request_spacing_and_first_call_at_clock_origin(transport, clock):
    """Hand calculation: configured R=1800/h gives 3600/R = 2 seconds.

    First request at t=0 needs no wait. At t=0.5, wait 2-0.5=1.5;
    the next request at t=4 is already 2 seconds after the previous one.
    This is a configured test policy, not an asserted EIA service quota.
    """
    now, sleeps = clock
    sent_at = []
    transport.side_effect = lambda *args, **kwargs: (
        sent_at.append(now[0]) or transport.return_value
    )
    client = EIAApiClient(
        api_key="TEST_KEY", cache_enabled=False, rate_limit_per_hour=1800
    )
    client.fetch_series(SERIES)
    assert sleeps == []
    now[0] += 0.5
    client.fetch_series(SERIES)
    now[0] += 2.0
    client.fetch_series(SERIES)
    assert sleeps == [1.5]
    assert sent_at == [0.0, 2.0, 4.0]


def test_cache_hits_skip_spacing_but_failed_attempts_consume_slots(transport, clock):
    """Hand trace with R=1800/h: GET at 0, cache hit at 0.5, timeout at 2.

    The next attempt waits until 4. Waits are 2-0.5=1.5 and 2-0=2;
    a cache hit must not shift the previous GET timestamp to 0.5.
    """
    now, sleeps = clock
    client = EIAApiClient(api_key="TEST_KEY", rate_limit_per_hour=1800)
    client.fetch_series(SERIES)
    now[0] += 0.5
    assert client.fetch_series(SERIES) == PARSED_ROWS
    transport.side_effect = requests.Timeout("synthetic timeout")
    with pytest.raises(EIAApiError):
        client.fetch_series(SERIES, {"offset": 2})
    transport.side_effect = None
    assert client.fetch_series(SERIES, {"offset": 2}) == PARSED_ROWS
    assert sleeps == [1.5, 2.0]
    assert now[0] == 4.0
    assert transport.call_count == 3


@pytest.mark.parametrize("rate", [0, -1])
def test_nonpositive_rate_disables_spacing(transport, clock, rate):
    """Configured nonpositive rates preserve the existing no-spacing policy."""
    client = EIAApiClient(
        api_key="TEST_KEY", cache_enabled=False, rate_limit_per_hour=rate
    )
    client.fetch_series(SERIES)
    client.fetch_series(SERIES)
    assert clock[1] == []
    assert transport.call_count == 2


def test_request_url_parameters_timeout_and_input_immutability(transport, clock):
    """EIA's offset=24,length=12 example is forwarded as one page unchanged.

    Timeout expectation comes from the existing client policy at f82ff2f,
    client/eia_api.py, _fetch_live; it is not an EIA acceptance limit.
    """
    client = EIAApiClient(api_key="TEST_KEY", base_url="https://example.invalid/v2/")
    params = {"offset": 24, "length": 12, "start": "2024-01"}
    assert client.fetch_series(SERIES, params) == PARSED_ROWS
    transport.assert_called_once_with(
        f"https://example.invalid/v2/seriesid/{SERIES}",
        params={"api_key": "TEST_KEY", **params},
        timeout=30,
    )
    assert params == {"offset": 24, "length": 12, "start": "2024-01"}


@pytest.mark.parametrize(
    "status,error",
    [
        (HTTPStatus.TOO_MANY_REQUESTS, EIARateLimitError),
        (HTTPStatus.BAD_REQUEST, EIAApiError),
        (HTTPStatus.UNAUTHORIZED, EIAApiError),
        (HTTPStatus.NOT_FOUND, EIAApiError),
        (HTTPStatus.INTERNAL_SERVER_ERROR, EIAApiError),
        (HTTPStatus.SERVICE_UNAVAILABLE, EIAApiError),
    ],
)
def test_http_errors_do_not_cache_and_next_call_recovers(
    transport, clock, status, error
):
    """Error -> cache miss -> successful retry by caller -> cache hit.

    No automatic retry is asserted; RFC status sources are in the module docstring.
    """
    client = EIAApiClient(api_key="TEST_KEY")
    transport.return_value.status_code = status
    transport.return_value.text = "synthetic error"
    with pytest.raises(error):
        client.fetch_series(SERIES)
    transport.return_value.json.assert_not_called()
    assert client.cache._store == {}
    assert transport.call_count == 1
    transport.return_value.status_code = HTTPStatus.OK
    assert client.fetch_series(SERIES) == PARSED_ROWS
    assert client.fetch_series(SERIES) == PARSED_ROWS
    assert transport.call_count == 2


@pytest.mark.parametrize(
    "exception", [requests.Timeout, requests.ConnectionError, requests.RequestException]
)
def test_transport_errors_are_api_errors_and_not_cached(transport, clock, exception):
    """A failed attempt never supplies records; the next caller may recover."""
    client = EIAApiClient(api_key="TEST_KEY")
    transport.side_effect = exception("synthetic transport failure")
    with pytest.raises(EIAApiError, match="request failed"):
        client.fetch_series(SERIES)
    assert client.cache._store == {}
    transport.side_effect = None
    assert client.fetch_series(SERIES) == PARSED_ROWS
    assert transport.call_count == 2


def test_invalid_json_is_api_error_and_not_cached(transport, clock):
    """A successful HTTP response still needs valid JSON before insertion."""
    client = EIAApiClient(api_key="TEST_KEY")
    transport.return_value.json.side_effect = ValueError("synthetic invalid JSON")
    with pytest.raises(EIAApiError, match="JSON"):
        client.fetch_series(SERIES)
    assert client.cache._store == {}
    transport.return_value.json.side_effect = None
    assert client.fetch_series(SERIES) == PARSED_ROWS


@pytest.mark.parametrize("row", [None, [], "invalid", 7])
def test_non_object_records_raise_api_error_without_cache(transport, clock, row):
    """EIA data rows are objects, so scalar/array/null rows cannot be parsed."""
    client = EIAApiClient(api_key="TEST_KEY")
    transport.return_value.json.return_value = {"response": {"data": [row]}}
    with pytest.raises(EIAApiError, match="object"):
        client.fetch_series(SERIES)
    assert client.cache._store == {}


def test_failed_live_response_preserves_mock_cache(transport, clock):
    """A missing-data live response cannot overwrite a successful mock entry."""
    client = EIAApiClient(api_key="TEST_KEY")
    mock_rows = client.fetch_series(SERIES, use_mock=True)
    transport.return_value.json.return_value = {"response": {}}
    with pytest.raises(EIAApiError, match=r"response\.data"):
        client.fetch_series(SERIES)
    assert client.fetch_series(SERIES, use_mock=True) == mock_rows
    assert client.cache.get(client.generate_cache_key(SERIES, {})) is None


@pytest.mark.parametrize("total", [None, "4"])
def test_explicit_page_boundaries_and_empty_page_cache(transport, clock, total):
    """Hand trace: four synthetic rows, length=2 -> offsets 0,2,4 yield 2,2,0.

    Offset/length semantics: EIA APIv2 "Length and offset". Even without total,
    each fetch is one request; no hidden loop or request for the next page.
    """
    pages = [
        [{"period": "2024-01", "value": "1"}, {"period": "2024-02", "value": "2"}],
        [{"period": "2024-03", "value": "3"}, {"period": "2024-04", "value": "4"}],
        [],
    ]
    responses = [{"data": rows} for rows in pages]
    if total is not None:
        for response in responses:
            response["total"] = total
    transport.side_effect = [
        Mock(status_code=HTTPStatus.OK, json=Mock(return_value={"response": response}))
        for response in responses
    ]
    client = EIAApiClient(api_key="TEST_KEY")
    actual = []
    for offset, values in ((0, [1.0, 2.0]), (2, [3.0, 4.0]), (4, [])):
        params = {"offset": offset, "length": 2}
        rows = client.fetch_series(SERIES, params)
        assert [row["value"] for row in rows] == values
        assert client.fetch_series(SERIES, params) == rows
        actual.extend(rows)
    assert [row["value"] for row in actual] == [1.0, 2.0, 3.0, 4.0]
    assert [call.kwargs["params"]["offset"] for call in transport.call_args_list] == [
        0,
        2,
        4,
    ]
    assert transport.call_count == 3


def test_documented_json_page_limit_is_forwarded_without_prefetch(transport, clock):
    """EIA APIv2 "Length and offset" specifies a 5,000-row JSON maximum.

    This checks forwarding, not service-side enforcement of that maximum.
    """
    client = EIAApiClient(api_key="TEST_KEY")
    client.fetch_series(SERIES, {"offset": 0, "length": 5000})
    assert transport.call_args.kwargs["params"]["length"] == 5000
    transport.assert_called_once()
