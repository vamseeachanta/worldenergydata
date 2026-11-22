"""Permit date-filter regressions for #1259; no live services are queried.

The issue explicitly allows raising when date filtering is unsupported. The
expected behavior is the truth table: either bound supplied -> error and no
request; neither bound supplied -> existing undated search. No numerical model,
coefficient, tolerance, or external engineering reference applies.
"""

from datetime import date
from unittest.mock import Mock

import pytest

from worldenergydata.landman.exceptions import ProviderError, StateNotSupportedError
from worldenergydata.landman.providers.state_gis import StateGISProvider

# Source: #1259's reproduction uses these calendar bounds (2026 issue revision).
START_DATE = date.fromisoformat("2025-01-01")
END_DATE = date.fromisoformat("2025-12-31")


@pytest.mark.parametrize("state", ["TX", "NM", "OK", "ND", "CO", "WY", "LA", "UT"])
@pytest.mark.parametrize(
    ("start_date", "end_date"),
    [(START_DATE, None), (None, END_DATE), (START_DATE, END_DATE)],
    ids=["start-only", "end-only", "both-bounds"],
)
def test_dated_permit_search_fails_before_request(
    monkeypatch, state, start_date, end_date
):
    """By #1259, each requested bound must be applied or explicitly rejected.

    States come from StateGISProvider.SUPPORTED_STATES in the repository; both
    ESRI services and the custom/sonris branches must reject unsupported dates.
    """
    provider = StateGISProvider()
    get_json = Mock(return_value={"features": []})
    monkeypatch.setattr(provider, "_get_json", get_json)

    with pytest.raises(
        ProviderError, match="Permit date filtering is not supported"
    ) as exc:
        provider.search_permits(state, start_date=start_date, end_date=end_date)

    assert exc.value.error_code == "PERMIT_DATE_FILTER_UNSUPPORTED"
    assert exc.value.details == {
        "module": "landman",
        "provider": "state_gis",
        "state": state,
    }
    get_json.assert_not_called()


def test_dated_permit_search_normalizes_state(monkeypatch):
    """The existing state lookup accepts lowercase; the error uses its canonical code."""
    provider = StateGISProvider()
    get_json = Mock()
    monkeypatch.setattr(provider, "_get_json", get_json)

    with pytest.raises(ProviderError) as exc:
        provider.search_permits("tx", start_date=START_DATE)

    assert exc.value.details["state"] == "TX"
    get_json.assert_not_called()


def test_dated_permit_search_preserves_unsupported_state_error(monkeypatch):
    """An unsupported state still fails the existing state validation first."""
    provider = StateGISProvider()
    get_json = Mock()
    monkeypatch.setattr(provider, "_get_json", get_json)

    with pytest.raises(StateNotSupportedError):
        provider.search_permits("ZZ", end_date=END_DATE)

    get_json.assert_not_called()


@pytest.mark.parametrize("state", ["TX", "NM"])
@pytest.mark.parametrize(
    ("filters", "expected_where"),
    [
        ({}, "1=1"),
        ({"county": "Example County"}, "1=1 AND UPPER(COUNTY) = 'EXAMPLE COUNTY'"),
        (
            {"operator": "Example Operator"},
            "1=1 AND UPPER(OPERATOR) LIKE '%EXAMPLE OPERATOR%'",
        ),
        (
            {"county": "Example County", "operator": "Example Operator"},
            (
                "1=1 AND UPPER(COUNTY) = 'EXAMPLE COUNTY' "
                "AND UPPER(OPERATOR) LIKE '%EXAMPLE OPERATOR%'"
            ),
        ),
    ],
    ids=["unfiltered", "county", "operator", "county-and-operator"],
)
def test_undated_esri_permit_search_preserves_query(
    monkeypatch, state, filters, expected_where
):
    """Hand trace: one identified fixture feature -> one parsed permit -> counts of one.

    Query expectations follow search_permits at the base revision: join the
    always-true predicate with supplied county/operator predicates using AND.
    The layer index and default result limit below are that existing API
    contract, not new engineering constants.
    """
    provider = StateGISProvider()
    attrs = {"PERMIT_NUMBER": "PERMIT-A", "COUNTY": "EXAMPLE COUNTY"}
    get_json = Mock(return_value={"features": [{"attributes": attrs}]})
    monkeypatch.setattr(provider, "_get_json", get_json)

    result = provider.search_permits(state, start_date=None, end_date=None, **filters)

    # Source: StateGISProvider.SUPPORTED_STATES and search_permits at the base revision.
    urls = {
        "TX": "https://gis.rrc.texas.gov/arcgis/rest/services/GIS/OGpermit/MapServer/0/query",
        "NM": "https://gis.emnrd.nm.gov/arcgis/rest/services/Permits/MapServer/0/query",
    }
    get_json.assert_called_once_with(
        urls[state],
        params={
            "where": expected_where,
            "outFields": "*",
            "returnGeometry": "true",
            "f": "json",
            "resultRecordCount": 100,
        },
        record_keys=("features",),
    )
    assert result.total_count == result.returned_count == 1
    assert [permit.permit_number for permit in result.permits] == ["PERMIT-A"]
    assert result.permits[0].raw_data == attrs
    assert result.source == f"state_gis:{state}"


@pytest.mark.parametrize("state", ["OK", "ND", "CO", "WY", "LA", "UT"])
def test_undated_custom_permit_search_rejects_unimplemented_service(monkeypatch, state):
    """An unimplemented search cannot establish the absence of records (#1256)."""
    provider = StateGISProvider()
    get_json = Mock()
    monkeypatch.setattr(provider, "_get_json", get_json)

    with pytest.raises(ProviderError) as caught:
        provider.search_permits(state)

    assert caught.value.error_code == "SEARCH_UNSUPPORTED"
    get_json.assert_not_called()
