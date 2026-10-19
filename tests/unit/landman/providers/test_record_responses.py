"""Record-list contract regressions for #1260 (2026).

Synthetic counts are hand enumerated: a rejected response creates no cache
entry; failure followed by success requires two requests; a repeated successful
search uses the cached response. An empty list contains zero records.
No physical constants, coefficients, or engineering acceptance limits are used.
"""

from functools import partial
from http import HTTPStatus

import httpx
import pytest

from worldenergydata.landman.exceptions import ParsingError, RecordNotFoundError
from worldenergydata.landman.providers.blm import BLMProvider
from worldenergydata.landman.providers.state_gis import StateGISProvider


@pytest.fixture(
    params=["location", "operator", "permits", "detail", "claims", "leases"]
)
def query(request):
    """Return each public query, its parser and an independently built record."""
    if request.param in {"claims", "leases"}:
        provider = BLMProvider(rate_limit_delay=0)  # No delay in mock transport.
        key = "results"
        record = {"case_nr": "TEST"}
        if request.param == "claims":
            action = partial(provider.search_mining_claims, "NM")
            parse = partial(provider._parse_mining_claims, state="NM")
        else:
            action = partial(provider.search_fluid_minerals, "NM")
            parse = partial(provider._parse_fluid_minerals, state="NM")
    else:
        provider = StateGISProvider(rate_limit_delay=0)  # No mock transport delay.
        key = "features"
        record = {"attributes": {"API_NUMBER": "TEST"}}
        parse = partial(
            provider._parse_esri_wells, config=provider._get_state_config("TX")
        )
        if request.param == "location":
            action = partial(provider.search_wells_by_location, "TX", "TEST")
        elif request.param == "operator":
            action = partial(provider.search_by_operator, "TEST", "TX")
        elif request.param == "detail":
            action = partial(provider.get_well_detail, "TEST", "TX")
        else:
            record = {"attributes": {"PERMIT_NUMBER": "TEST"}}
            action = partial(provider.search_permits, "TX")
            parse = partial(provider._parse_esri_permits, state="TX")
    yield provider, action, parse, key, record, request.param
    provider.close()


@pytest.mark.parametrize(
    "shape",
    [
        "missing",
        "error",
        "error_with_records",
        "null",
        "mapping",
        "text",
        "scalar",
        "bad_item",
        "top_list",
    ],
)
def test_invalid_record_response_is_visible_and_not_cached(query, shape):
    """Hand count: failure + recovery = two requests, then cached searches."""
    provider, action, parse, key, record, name = query
    payloads = {
        "missing": {},
        "error": {"error": {"message": "synthetic failure"}},
        "error_with_records": {"error": {}, key: []},
        "null": {key: None},
        "mapping": {key: {}},
        "text": {key: "invalid"},
        "scalar": {key: False},
        "bad_item": {key: [None]},
        "top_list": [],
    }
    invalid = payloads[shape]
    with pytest.raises(ParsingError):
        parse(invalid)

    requests = []

    def respond(request):
        requests.append(request)
        payload = invalid if len(requests) == 1 else {key: [record]}
        # RFC 9110 (2022), section 15.3.1: successful HTTP transport.
        return httpx.Response(HTTPStatus.OK, json=payload)

    provider._client = httpx.Client(transport=httpx.MockTransport(respond))
    with pytest.raises(ParsingError):
        action()
    assert provider.cache_stats()["entries"] == 0
    assert action() is not None
    assert len(requests) == 2
    if name != "detail":
        action()
        assert len(requests) == 2
        assert provider.cache_stats()["entries"] == 1


def test_explicit_empty_list_is_success(query):
    """Hand count: [] gives zero records, and only detail lookup is not found."""
    provider, action, parse, key, _, name = query
    assert parse({key: []}) == []
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(HTTPStatus.OK, json={key: []})

    provider._client = httpx.Client(transport=httpx.MockTransport(respond))
    if name == "detail":
        with pytest.raises(RecordNotFoundError):
            action()
        assert provider.cache_stats()["entries"] == 0
    else:
        result = action()
        assert result.total_count == result.returned_count == 0
        action()
        assert len(requests) == 1


def test_invalid_json_is_visible_and_not_cached(query):
    """A broken JSON body then a successful response requires two requests."""
    provider, action, _, key, record, _ = query
    requests = []

    def respond(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(HTTPStatus.OK, text="not JSON")
        return httpx.Response(HTTPStatus.OK, json={key: [record]})

    provider._client = httpx.Client(transport=httpx.MockTransport(respond))
    with pytest.raises(ParsingError):
        action()
    assert provider.cache_stats()["entries"] == 0
    action()
    assert len(requests) == 2


@pytest.mark.parametrize("parser", ["_parse_mining_claims", "_parse_fluid_minerals"])
def test_blm_record_alias_and_precedence(parser):
    """Hand count: either alias gives one record; present results takes priority."""
    provider = BLMProvider()
    parse = partial(getattr(provider, parser), state="NM")
    record = {"case_nr": "TEST"}
    assert len(parse({"records": [record]})) == 1
    assert len(parse({"results": [record]})) == 1
    assert parse({"results": [], "records": [record]}) == []
    with pytest.raises(ParsingError):
        parse({"results": None, "records": []})
