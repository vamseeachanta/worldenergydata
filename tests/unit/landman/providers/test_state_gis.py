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


@pytest.mark.parametrize(
    ("bounds", "expected_date_clause"),
    [
        ({"start_date": START_DATE}, "ISSUED_AT >= TIMESTAMP '2025-01-01'"),
        ({"end_date": END_DATE}, "ISSUED_AT < TIMESTAMP '2026-01-01'"),
        (
            {"start_date": START_DATE, "end_date": END_DATE},
            "ISSUED_AT >= TIMESTAMP '2025-01-01' AND ISSUED_AT < TIMESTAMP '2026-01-01'",
        ),
        (
            {"start_date": END_DATE, "end_date": END_DATE},
            "ISSUED_AT >= TIMESTAMP '2025-12-31' AND ISSUED_AT < TIMESTAMP '2026-01-01'",
        ),
    ],
    ids=["start-only", "end-only", "both", "same-day"],
)
@pytest.mark.parametrize("state", ["TX", "NM"])
def test_verified_permit_date_field_reaches_query(
    monkeypatch, bounds, expected_date_clause, state
):
    """Hand calculation: inclusive Dec 31 ends just before Jan 1 of the next year.

    Bounds are issue #1259's example, not measured data. TIMESTAMP literals follow
    Esri SQL reference, 'Date-time syntax for geodatabases' (accessed 2026-10-22).
    ISSUED_AT is a synthetic field supplied explicitly, never a live schema claim.
    """
    with StateGISProvider(permit_date_fields={state: "ISSUED_AT"}) as provider:
        get_json = Mock(return_value={"features": []})
        monkeypatch.setattr(provider, "_get_json", get_json)
        result = provider.search_permits(state, county="Synthetic", **bounds)

    assert get_json.call_args.kwargs["params"]["where"] == (
        "1=1 AND UPPER(COUNTY) = 'SYNTHETIC' AND " + expected_date_clause
    )
    get_json.assert_called_once()
    assert result.permits == []


@pytest.mark.parametrize("date_fields", [None, {"TX": "ISSUED_AT"}])
def test_inverted_permit_dates_fail_before_request(monkeypatch, date_fields):
    """Hand comparison of #1259's bounds: Dec 31 is after Jan 1 in the same year."""
    with StateGISProvider(permit_date_fields=date_fields) as provider:
        get_json = Mock()
        monkeypatch.setattr(provider, "_get_json", get_json)
        with pytest.raises(ValueError, match="start_date.*end_date"):
            provider.search_permits("TX", start_date=END_DATE, end_date=START_DATE)
        get_json.assert_not_called()


def test_permit_date_field_requires_plain_identifier():
    """A configuration field must not inject a SQL expression into the query."""
    with pytest.raises(ValueError, match="date field"):
        StateGISProvider(permit_date_fields={"TX": "ISSUED_AT OR TRUE"})


def test_permit_date_upper_bound_overflow_is_explicit(monkeypatch):
    """date.max has no following calendar day; silently dropping it is invalid."""
    with StateGISProvider(permit_date_fields={"TX": "ISSUED_AT"}) as provider:
        get_json = Mock()
        monkeypatch.setattr(provider, "_get_json", get_json)
        with pytest.raises(ValueError, match="end_date"):
            provider.search_permits("TX", end_date=date.max)
        get_json.assert_not_called()


def test_rejected_date_query_is_not_an_empty_success(monkeypatch):
    """A service error object has no features but is not a matching empty set.

    Source: #1259 requires an error if the service cannot filter by date.
    The stub's error envelope is synthetic; no live service is contacted.
    """
    with StateGISProvider(permit_date_fields={"TX": "ISSUED_AT"}) as provider:
        get_json = Mock(return_value={"error": {"message": "Unsupported predicate"}})
        monkeypatch.setattr(provider, "_get_json", get_json)
        with pytest.raises(ProviderError) as caught:
            provider.search_permits("TX", start_date=START_DATE)
    assert caught.value.error_code == "PERMIT_QUERY_ERROR"
    assert caught.value.details == {
        "module": "landman",
        "provider": "state_gis",
        "state": "TX",
    }


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
    )
    assert result.total_count == result.returned_count == 1
    assert [permit.permit_number for permit in result.permits] == ["PERMIT-A"]
    assert result.permits[0].raw_data == attrs
    assert result.source == f"state_gis:{state}"


@pytest.mark.parametrize("state", ["OK", "ND", "CO", "WY", "LA", "UT"])
def test_undated_custom_permit_search_rejects_unsupported_query(monkeypatch, state):
    """An unimplemented service cannot establish an empty matching record set."""
    provider = StateGISProvider()
    get_json = Mock()
    monkeypatch.setattr(provider, "_get_json", get_json)

    with pytest.raises(ProviderError) as caught:
        provider.search_permits(state)
    assert caught.value.error_code == "SEARCH_UNSUPPORTED"
    assert caught.value.details["state"] == state
    get_json.assert_not_called()
