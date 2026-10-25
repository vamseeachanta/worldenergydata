"""Error/empty regression cases for #1256 using synthetic, offline responses.

The oracle is the repository contract in providers/base.py (_make_request and
_get_json) and exceptions.py: transport, HTTP and decoding failures are provider
errors. A successful empty search has len([]) = 0 records; an empty detail
lookup alone means RecordNotFoundError. No engineering coefficients are used.
"""

from dataclasses import dataclass
from typing import Any

import httpx
import pytest

from worldenergydata.landman.exceptions import (
    APIError,
    ParsingError,
    RateLimitError,
    RecordNotFoundError,
    TimeoutError,
)
from worldenergydata.landman.providers.blm import BLMProvider
from worldenergydata.landman.providers.state_gis import StateGISProvider


@dataclass
class Query:
    provider: Any
    method: str
    kwargs: dict
    collection: str | None = None

    def run(self):
        return getattr(self.provider, self.method)(**self.kwargs)


@pytest.fixture(
    params=[
        "location",
        "operator",
        "permits",
        "well_detail",
        "case_detail",
        "mining_claims",
        "fluid_minerals",
    ]
)
def query(request):
    # BaseProvider._make_request: zero retries exercises terminal failures
    # without sleeps; zero rate-limit delay removes throttling in offline tests.
    provider_type = (
        BLMProvider
        if request.param in {"case_detail", "mining_claims", "fluid_minerals"}
        else StateGISProvider
    )
    with provider_type(max_retries=0, rate_limit_delay=0) as provider:
        cases = {
            "location": Query(
                provider,
                "search_wells_by_location",
                {"state": "TX", "county": "SYNTHETIC"},
                "wells",
            ),
            "operator": Query(
                provider,
                "search_by_operator",
                {"state": "TX", "operator_name": "SYNTHETIC"},
                "wells",
            ),
            "permits": Query(provider, "search_permits", {"state": "TX"}, "permits"),
            "well_detail": Query(
                provider,
                "get_well_detail",
                {"state": "TX", "api_number": "synthetic-api"},
            ),
            "case_detail": Query(
                provider,
                "get_case_detail",
                {"state": "NM", "case_number": "synthetic-case"},
            ),
            "mining_claims": Query(
                provider, "search_mining_claims", {"state": "NM"}, "claims"
            ),
            "fluid_minerals": Query(
                provider, "search_fluid_minerals", {"state": "NM"}, "leases"
            ),
        }
        yield cases[request.param]


@pytest.mark.parametrize(
    ("failure", "expected_error"),
    [
        ("timeout", TimeoutError),
        ("connection", APIError),
        ("http", APIError),
        ("rate_limit", RateLimitError),
        ("invalid_json", ParsingError),
    ],
)
def test_transport_failure_is_visible(query, failure, expected_error):
    """BaseProvider's typed failure must reach each public query caller."""
    requests = []

    def respond(request):
        requests.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("Synthetic timeout", request=request)
        if failure == "connection":
            raise httpx.ConnectError("Synthetic connection failure", request=request)
        if failure == "http":
            return httpx.Response(httpx.codes.SERVICE_UNAVAILABLE)
        if failure == "rate_limit":
            return httpx.Response(httpx.codes.TOO_MANY_REQUESTS)
        return httpx.Response(httpx.codes.OK, text="not json")

    query.provider._client = httpx.Client(transport=httpx.MockTransport(respond))

    with pytest.raises(expected_error) as caught:
        query.run()

    assert requests
    if failure in {"http", "connection", "timeout"}:
        assert caught.value.details["url"] == str(
            requests[-1].url.copy_with(query=None)
        )
    if failure == "http":
        assert caught.value.details["status_code"] == httpx.codes.SERVICE_UNAVAILABLE


def test_provider_error_is_preserved(query, monkeypatch):
    """The error object and its structured context are preserved unchanged."""
    error = APIError(url="https://example.invalid/query", message="Synthetic failure")

    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(query.provider, "_get_json", fail)
    with pytest.raises(APIError) as caught:
        query.run()
    assert caught.value is error


def test_successful_empty_response(query):
    """Hand count: an empty feature list contains zero records.

    SearchResult counts must both equal zero; only detail lookups should raise
    RecordNotFoundError (exceptions.py, RecordNotFoundError contract).
    """
    query.provider._client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                httpx.codes.OK,
                json=(
                    {"results": []}
                    if isinstance(query.provider, BLMProvider)
                    else {"features": []}
                ),
            )
        )
    )

    if query.collection is None:
        with pytest.raises(RecordNotFoundError) as caught:
            query.run()
        identifier = query.kwargs.get("api_number") or query.kwargs["case_number"]
        assert caught.value.details["identifier"] == identifier
    else:
        result = query.run()
        # Independent hand count above: len([]) = 0.
        assert result.total_count == result.returned_count == 0
        assert getattr(result, query.collection) == []
        assert result.source == (
            f"blm:{query.method.removeprefix('search_')}:NM"
            if isinstance(query.provider, BLMProvider)
            else "state_gis:TX"
        )


def test_successful_record_response(query):
    """Hand count: the synthetic payload contains exactly one record.

    Identifiers are copied from the supplied record. Expected values do not
    depend on the provider parser or a live external service.
    """
    attrs = {"API_NUMBER": "synthetic-api", "PERMIT_NUMBER": "synthetic-permit"}
    if query.method == "get_case_detail":
        payload = {"case_nr": "synthetic-case"}
    elif isinstance(query.provider, BLMProvider):
        payload = {"results": [{"case_nr": "synthetic-case"}]}
    else:
        payload = {"features": [{"attributes": attrs}]}
    query.provider._client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(httpx.codes.OK, json=payload)
        )
    )

    result = query.run()
    if query.method == "get_case_detail":
        assert result == {"case_nr": "synthetic-case"}
    elif query.collection is None:
        assert result.api_number == "synthetic-api"
    else:
        # Independent hand count above: len([record]) = 1.
        assert result.total_count == result.returned_count == 1
        (record,) = getattr(result, query.collection)
        if query.collection == "permits":
            assert record.permit_number == "synthetic-permit"
        elif query.collection == "wells":
            assert record.api_number == "synthetic-api"
        else:
            assert record.case_number == "synthetic-case"


@pytest.mark.parametrize("failure", ["connection", "timeout", "http", "error-envelope"])
def test_federal_land_status_retains_explicit_error_result(failure):
    """The sixth federal fallback named in #1251 reports an explicit error.

    Unlike a fabricated zero-record search, its dictionary says unknown and
    includes an error member. This existing result contract remains visible;
    no error envelope is cached. The expected location echoes synthetic inputs.
    """

    def respond(request):
        if failure == "connection":
            raise httpx.ConnectError("Synthetic unavailable service", request=request)
        if failure == "timeout":
            raise httpx.ReadTimeout("Synthetic timeout", request=request)
        if failure == "http":
            return httpx.Response(httpx.codes.SERVICE_UNAVAILABLE)
        return httpx.Response(httpx.codes.OK, json={"error": {}})

    with BLMProvider(max_retries=0, rate_limit_delay=0) as provider:
        provider._client = httpx.Client(transport=httpx.MockTransport(respond))
        result = provider.get_land_status("NM", "T", "R", "S")
        assert result["status"] == "unknown"
        assert result["error"]
        assert {
            key: result[key] for key in ("state", "township", "range", "section")
        } == {"state": "NM", "township": "T", "range": "R", "section": "S"}
        assert provider.cache_stats()["entries"] == 0
