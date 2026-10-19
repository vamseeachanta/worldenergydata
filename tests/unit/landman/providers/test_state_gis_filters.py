"""SQL literal regressions for GIS request filters.

Source: ArcGIS Pro SQL reference, latest online edition, "Strings", accessed
2026-10-19: a single quotation mark inside a string is escaped by doubling it.
https://doc.esri.com/en/arcgis-pro/latest/help/mapping/navigation/sql-reference-for-elements-used-in-query-expressions.html
All input values are synthetic; expected clauses are written independently.
"""

from http import HTTPStatus

import httpx
import pytest

from worldenergydata.landman.exceptions import RecordNotFoundError
from worldenergydata.landman.providers.state_gis import StateGISProvider


@pytest.fixture
def captured_query():
    provider = StateGISProvider(rate_limit_delay=0)  # No delay in mock transport.
    clauses = []

    def respond(request):
        clauses.append(request.url.params["where"])
        # RFC 9110 (2022), section 15.3.1: successful HTTP transport.
        return httpx.Response(HTTPStatus.OK, json={"features": []})

    provider._client = httpx.Client(transport=httpx.MockTransport(respond))
    yield provider, clauses
    provider.close()


def test_location_values_escape_quotes(captured_query):
    """Each embedded quote becomes two; uppercasing applies only to county."""
    provider, clauses = captured_query
    provider.search_wells_by_location(
        "TX", "test'county", section="s'", township="t'", range_="r'"
    )
    assert clauses == [
        (
            "UPPER(COUNTY) = 'TEST''COUNTY' AND SECTION = 's''' "
            "AND TOWNSHIP = 't''' AND RANGE = 'r'''"
        )
    ]


def test_operator_values_escape_quotes(captured_query):
    """Quote doubling keeps an injection-shaped value inside the LIKE literal."""
    provider, clauses = captured_query
    provider.search_by_operator("test' OR 'a'='a", "TX")
    assert clauses == ["UPPER(OPERATOR) LIKE '%TEST'' OR ''A''=''A%'"]


def test_permit_values_escape_quotes(captured_query):
    """The existing tautology and partial-match wildcards are retained."""
    provider, clauses = captured_query
    provider.search_permits("TX", county="test'county", operator="test'operator")
    # 1=1 is the existing unconditional predicate, not an acceptance limit.
    assert clauses == [
        (
            "1=1 AND UPPER(COUNTY) = 'TEST''COUNTY' "
            "AND UPPER(OPERATOR) LIKE '%TEST''OPERATOR%'"
        )
    ]


def test_detail_values_escape_quotes(captured_query):
    """Both the supplied identifier and its hyphen-free alias are escaped."""
    provider, clauses = captured_query
    with pytest.raises(RecordNotFoundError):
        provider.get_well_detail("test'-id", "TX")
    assert clauses == ["API_NUMBER = 'test''-id' OR API_NUMBER = 'test''id'"]


def test_operator_wildcards_keep_partial_match_semantics(captured_query):
    """Percent and underscore remain LIKE wildcards; only quotes are escaped."""
    provider, clauses = captured_query
    provider.search_by_operator("test%_", "TX")
    assert clauses == ["UPPER(OPERATOR) LIKE '%TEST%_%'"]
