"""Offline response-contract regressions.

Source: EIA API Technical Documentation, APIv2 (accessed 2026-10-19),
"Understanding returned error codes" and "Parameters":
https://www.eia.gov/opendata/documentation.php
These are structural fixtures, not measured production data or calculations.
"""

from http import HTTPStatus
from unittest.mock import Mock

import pytest
import requests

from worldenergydata.eia_us.client.eia_api import EIAApiClient, EIAApiError

INVALID_RESPONSES = [
    {},
    {"error": "Invalid frequency"},
    {"response": {}},
    {"response": None},
    {"response": []},
    {"response": {"data": None}},
    {"response": {"data": {}}},
    {"response": {"data": ""}},
    [],
]


@pytest.mark.parametrize("raw", INVALID_RESPONSES)
def test_parser_rejects_missing_or_non_list_data(raw):
    """Contract derivation: absent/non-array data cannot be a series array."""
    client = EIAApiClient(api_key="TEST_KEY")

    with pytest.raises(EIAApiError, match=r"response\.data"):
        client.parse_series_response(raw)


@pytest.mark.parametrize("raw", INVALID_RESPONSES)
def test_invalid_response_is_not_cached_and_next_fetch_recovers(monkeypatch, raw):
    """Independent state trace: miss -> error -> miss -> valid [] -> hit.

    The explicit empty array has no records by construction. After the error,
    the same query must consume the next HTTP response, then cache that array.
    HTTPStatus.OK is defined by RFC 9110 (2022), section 15.3.1.
    """
    client = EIAApiClient(api_key="TEST_KEY")
    responses = iter([raw, {"response": {"data": []}}])

    def get_response(*args, **kwargs):
        return Mock(status_code=HTTPStatus.OK, json=lambda: next(responses))

    monkeypatch.setattr(requests, "get", get_response)
    monkeypatch.setattr(client, "_apply_rate_limit", lambda: None)
    series_id = "PET.MCRFPUS2.M"
    cache_key = client.generate_cache_key(series_id, {})

    with pytest.raises(EIAApiError, match=r"response\.data"):
        client.fetch_series(series_id)
    assert client.cache.get(cache_key) is None

    assert client.fetch_series(series_id) == []
    assert client.cache.get(cache_key) == []
    # The iterator is exhausted: another transport call would fail this fetch.
    assert client.fetch_series(series_id) == []
