"""Literal queries derived by hand from Esri's SQL reference, Searching strings.

Online edition accessed 2026-10-22:
https://doc.esri.com/en/arcgis-pro/latest/help/mapping/navigation/sql-reference-for-elements-used-in-query-expressions.html
Embedded apostrophes are doubled within a quoted SQL string. UPPER and LIKE
retain the existing case-insensitive partial-match behavior; percent and
underscore remain wildcards. Expected clauses below are literal hand oracles.
"""

import httpx
import pytest

from worldenergydata.landman.providers.state_gis import StateGISProvider


@pytest.mark.parametrize(
    ("operator", "expected"),
    [
        ("Test's Energy", "UPPER(OPERATOR) LIKE '%TEST''S ENERGY%'"),
        ("x' OR '1'='1", "UPPER(OPERATOR) LIKE '%X'' OR ''1''=''1%'"),
        ("Test_%", "UPPER(OPERATOR) LIKE '%TEST_%%'"),
    ],
)
@pytest.mark.parametrize("method", ["operator", "permits"])
def test_operator_remains_a_single_sql_literal(operator, expected, method):
    """Double each quote, then enclose the whole value inside the LIKE pattern."""
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(httpx.codes.OK, json={"features": []})

    with StateGISProvider(max_retries=0, rate_limit_delay=0) as provider:
        provider._client = httpx.Client(transport=httpx.MockTransport(respond))
        if method == "operator":
            provider.search_by_operator(operator, "TX")
        else:
            provider.search_permits("TX", operator=operator)
            expected = "1=1 AND " + expected
    (request,) = requests
    assert request.url.params["where"] == expected


def test_all_location_values_are_quoted(monkeypatch):
    """Hand query: uppercase county only; double quotes in each of four values."""
    queries = []

    def respond(url, **kwargs):
        queries.append(kwargs["params"]["where"])
        return {"features": []}

    with StateGISProvider() as provider:
        monkeypatch.setattr(provider, "_get_json", respond)
        provider.search_wells_by_location(
            "TX", "Test's County", section="s'", township="t'", range_="r'"
        )
        provider.search_permits("TX", county="Test's County")
    assert queries == [
        (
            "UPPER(COUNTY) = 'TEST''S COUNTY' AND SECTION = 's''' "
            "AND TOWNSHIP = 't''' AND RANGE = 'r'''"
        ),
        "1=1 AND UPPER(COUNTY) = 'TEST''S COUNTY'",
    ]


def test_detail_quotes_original_and_cleaned_identifiers(monkeypatch):
    """Hand query: remove the dash for the second ID, then double both quotes."""
    queries = []

    def respond(url, **kwargs):
        queries.append(kwargs["params"]["where"])
        return {"features": [{"attributes": {"API_NUMBER": "synthetic-api"}}]}

    with StateGISProvider() as provider:
        monkeypatch.setattr(provider, "_get_json", respond)
        assert provider.get_well_detail("a-b'", "TX").api_number == "synthetic-api"
    assert queries == ["API_NUMBER = 'a-b''' OR API_NUMBER = 'ab'''"]
