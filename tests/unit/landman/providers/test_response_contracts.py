"""Response and cache contracts from #1260, using independent hand counts.

An explicit empty list has zero records. A missing list or any error member
cannot establish that count. Federal results/records aliases are the existing
adapter contract, not a claim about live service schemas. Mock HTTP statuses
use httpx's named RFC 9110 (2022), section 15.3.1 success code.
"""

import httpx
import pytest

from worldenergydata.landman.exceptions import ParsingError, RecordNotFoundError
from worldenergydata.landman.providers.blm import BLMProvider
from worldenergydata.landman.providers.state_gis import StateGISProvider


@pytest.fixture(params=["wells", "permits", "claims", "leases"])
def adapter(request):
    """Each synthetic list has one identified record, so both counts equal one."""
    kind = request.param
    provider_type = StateGISProvider if kind in {"wells", "permits"} else BLMProvider
    with provider_type(max_retries=0, rate_limit_delay=0) as provider:
        if kind == "wells":
            parse = lambda data: provider._parse_esri_wells(data, {})
            search = lambda: provider.search_wells_by_location("TX", "Synthetic")
            key, record, identifier = (
                "features",
                {"attributes": {"API_NUMBER": "WELL-A"}},
                "WELL-A",
            )
        elif kind == "permits":
            parse = lambda data: provider._parse_esri_permits(data, "TX")
            search = lambda: provider.search_permits("TX")
            key, record, identifier = (
                "features",
                {"attributes": {"PERMIT_NUMBER": "PERMIT-A"}},
                "PERMIT-A",
            )
        elif kind == "claims":
            parse = lambda data: provider._parse_mining_claims(data, "NM")
            search = lambda: provider.search_mining_claims("NM")
            key, record, identifier = "results", {"case_nr": "CLAIM-A"}, "CLAIM-A"
        else:
            parse = lambda data: provider._parse_fluid_minerals(data, "NM")
            search = lambda: provider.search_fluid_minerals("NM")
            key, record, identifier = "results", {"case_nr": "LEASE-A"}, "LEASE-A"
        yield provider, parse, search, key, record, identifier, kind


@pytest.mark.parametrize(
    "bad",
    [
        "missing",
        "error",
        "error-with-list",
        "null-error",
        "null-list",
        "object-list",
        "string-list",
        "bad-row",
        "null-envelope",
        "array-envelope",
    ],
)
def test_parsers_reject_invalid_envelopes(adapter, bad):
    """No accepted list exists in any of these manually specified envelopes."""
    _, parse, _, key, _, _, _ = adapter
    data = {
        "missing": {},
        "error": {"error": {"message": "Synthetic rejection"}},
        "error-with-list": {"error": {}, key: []},
        "null-error": {"error": None, key: []},
        "null-list": {key: None},
        "object-list": {key: {}},
        "string-list": {key: "invalid"},
        "bad-row": {key: [None]},
        "null-envelope": None,
        "array-envelope": [],
    }[bad]
    with pytest.raises(ParsingError):
        parse(data)


@pytest.mark.parametrize("key", ["results", "records"])
def test_federal_aliases_and_explicit_empty_lists(key):
    """Hand count: [] contains zero records; each fixture row contains one."""
    with BLMProvider() as provider:
        for parse in (provider._parse_mining_claims, provider._parse_fluid_minerals):
            assert parse({key: []}, "NM") == []
            (record,) = parse({key: [{"case_nr": "CASE-A"}]}, "NM")
            assert record.case_number == "CASE-A"
            # Existing precedence: results, when present, wins over records.
            assert (
                parse({"results": [], "records": [{"case_nr": "CASE-B"}]}, "NM") == []
            )
            with pytest.raises(ParsingError):
                parse({"results": None, "records": []}, "NM")


@pytest.mark.parametrize("failure", ["missing", "error", "invalid-json", "bad-row"])
def test_failed_response_is_not_cached_then_good_response_is(adapter, failure):
    """Hand trace: rejected request -> zero cache entries; recovery -> one.

    Three calls consume exactly two HTTP responses: bad, good, cached good.
    The good list contains one record with the independently specified ID.
    """
    provider, _, search, key, record, identifier, kind = adapter
    requests = []

    def respond(request):
        requests.append(request)
        if len(requests) == 1:
            if failure == "invalid-json":
                return httpx.Response(httpx.codes.OK, text="not json")
            bad = {"missing": {}, "error": {"error": {}}, "bad-row": {key: [None]}}[
                failure
            ]
            return httpx.Response(httpx.codes.OK, json=bad)
        return httpx.Response(httpx.codes.OK, json={key: [record]})

    provider._client = httpx.Client(transport=httpx.MockTransport(respond))
    with pytest.raises(ParsingError):
        search()
    assert provider.cache_stats()["entries"] == 0
    for _ in range(2):
        result = search()
        assert result.total_count == result.returned_count == 1
        (row,) = getattr(result, kind)
        attr = {"wells": "api_number", "permits": "permit_number"}.get(
            kind, "case_number"
        )
        assert getattr(row, attr) == identifier
        assert provider.cache_stats()["entries"] == 1
    assert len(requests) == 2


def test_explicit_empty_search_is_cacheable(adapter):
    """Hand trace: two calls, one empty response, one cache entry, zero records."""
    provider, _, search, key, _, _, kind = adapter
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(httpx.codes.OK, json={key: []})

    provider._client = httpx.Client(transport=httpx.MockTransport(respond))
    for _ in range(2):
        result = search()
        assert result.total_count == result.returned_count == 0
        assert getattr(result, kind) == []
    assert len(requests) == 1
    assert provider.cache_stats()["entries"] == 1


@pytest.mark.parametrize("kind", ["well", "case"])
def test_detail_error_envelope_is_not_not_found(kind):
    """An error plus an apparent record is still unavailable, never not-found."""
    provider_type = StateGISProvider if kind == "well" else BLMProvider
    with provider_type(max_retries=0, rate_limit_delay=0) as provider:
        payload = {"error": {}, "features": [], "case_nr": "CASE-A"}
        provider._client = httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(httpx.codes.OK, json=payload)
            )
        )
        with pytest.raises(ParsingError) as caught:
            if kind == "well":
                provider.get_well_detail("WELL-A", "TX")
            else:
                provider.get_case_detail("CASE-A", "NM")
        assert not isinstance(caught.value, RecordNotFoundError)
        assert provider.cache_stats()["entries"] == 0


def test_json_cache_hits_preserve_original_expiry(adapter):
    """Hand trace: two valid searches reuse the original response and expiry.

    The JSON validation path retains the existing fixed TTL contract rather
    than restarting the lifetime on each cache hit. No wall-clock wait or
    numerical expiration tolerance is needed: the cache entry is unchanged.
    """
    provider, _, search, key, record, _, _ = adapter
    provider._client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(httpx.codes.OK, json={key: [record]})
        )
    )
    search()
    (entry,) = provider._cache._cache.values()
    search()
    (cached,) = provider._cache._cache.values()
    assert cached is entry
