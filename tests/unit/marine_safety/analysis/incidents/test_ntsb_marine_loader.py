"""
Tests for ntsb_marine_loader.py — NTSB CAROL API taxonomy pipeline loader.

All tests use mocked HTTP responses; no live network calls are made.

Covers:
- NTSBMarineLoader.fetch_marine_accidents with mocked session
- Column mapping via NTSB_COLUMN_MAP to canonical schema
- Empty DataFrame returned on API failure
- TaxonomyRecord generation (fetch_to_records)
- load_dataframe_as_ntsb in-memory path
- fetch_ntsb_marine convenience function
- CAROL response parsing helpers (_extract_results, _extract_total_count, _map_carol_record)
- Pagination: stops when results < page_size
- Pagination: stops when total count reached
"""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from worldenergydata.marine_safety.analysis.incidents.incident_taxonomy import (
    RootCauseType,
    TaxonomyRecord,
)
from worldenergydata.marine_safety.analysis.incidents.ntsb_marine_loader import (
    NTSBMarineLoader,
    _extract_results,
    _extract_total_count,
    _first_float,
    _first_int,
    _first_value,
    _map_carol_record,
    fetch_ntsb_marine,
    load_dataframe_as_ntsb,
)

# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_carol_record(
    event_id: str = "MAR20AB001",
    event_date: str = "2020-06-15",
    vessel_name: str = "MV Ocean Star",
    vessel_type: str = "Cargo Ship",
    incident_type: str = "Grounding",
    narrative: str = "Vessel grounded on sandbank",
    probable_cause: str = "Operator error led to grounding",
    fatalities: int = 0,
    injuries: int = 1,
    latitude: float = 29.5,
    longitude: float = -94.8,
) -> Dict[str, Any]:
    """Build a minimal CAROL API record dict."""
    return {
        "EventId": event_id,
        "EventDate": event_date,
        "VesselName": vessel_name,
        "VesselType": vessel_type,
        "IncidentType": incident_type,
        "Narrative": narrative,
        "ProbableCause": probable_cause,
        "FatalCount": fatalities,
        "InjuryCount": injuries,
        "Latitude": latitude,
        "Longitude": longitude,
    }


def _make_session(records: List[Dict], total: int = None, status_code: int = 200):
    """Create a mock requests.Session that returns the given records."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    if status_code != 200:
        from requests.exceptions import HTTPError

        mock_resp.raise_for_status.side_effect = HTTPError(response=mock_resp)
    else:
        mock_resp.raise_for_status.return_value = None

    response_data: Dict[str, Any] = {"Results": records}
    if total is not None:
        response_data["TotalCount"] = total

    mock_resp.json.return_value = response_data

    session = MagicMock()
    session.post.return_value = mock_resp
    return session


# ---------------------------------------------------------------------------
# NTSBMarineLoader.fetch_marine_accidents
# ---------------------------------------------------------------------------


class TestFetchMarineAccidents:
    def test_returns_dataframe(self) -> None:
        records = [_make_carol_record("MAR20AB001")]
        loader = NTSBMarineLoader(session=_make_session(records, total=1))
        df = loader.fetch_marine_accidents(2020, 2020)
        assert isinstance(df, pd.DataFrame)

    def test_row_count_matches_records(self) -> None:
        records = [
            _make_carol_record("MAR20AB001"),
            _make_carol_record("MAR20AB002", vessel_name="SS Valiant"),
        ]
        loader = NTSBMarineLoader(session=_make_session(records, total=2))
        df = loader.fetch_marine_accidents(2020, 2020)
        assert len(df) == 2

    def test_report_id_column_present(self) -> None:
        records = [_make_carol_record("MAR20AB001")]
        loader = NTSBMarineLoader(session=_make_session(records, total=1))
        df = loader.fetch_marine_accidents(2020, 2020)
        assert "report_id" in df.columns
        assert "MAR20AB001" in df["report_id"].values

    def test_incident_date_column_present(self) -> None:
        records = [_make_carol_record("MAR20AB001", event_date="2020-06-15")]
        loader = NTSBMarineLoader(session=_make_session(records, total=1))
        df = loader.fetch_marine_accidents(2020, 2020)
        assert "incident_date" in df.columns
        assert "2020-06-15" in df["incident_date"].values

    def test_vessel_name_column_present(self) -> None:
        records = [_make_carol_record("MAR20AB001", vessel_name="MV Greenfield")]
        loader = NTSBMarineLoader(session=_make_session(records, total=1))
        df = loader.fetch_marine_accidents(2020, 2020)
        assert "vessel_name" in df.columns
        assert "MV Greenfield" in df["vessel_name"].values

    def test_source_column_is_ntsb(self) -> None:
        records = [_make_carol_record()]
        loader = NTSBMarineLoader(session=_make_session(records, total=1))
        df = loader.fetch_marine_accidents(2020, 2020)
        assert "source" in df.columns
        assert (df["source"] == "ntsb").all()

    def test_fatality_count_column_present(self) -> None:
        records = [_make_carol_record(fatalities=2)]
        loader = NTSBMarineLoader(session=_make_session(records, total=1))
        df = loader.fetch_marine_accidents(2020, 2020)
        assert "fatality_count" in df.columns

    def test_injury_count_column_present(self) -> None:
        records = [_make_carol_record(injuries=5)]
        loader = NTSBMarineLoader(session=_make_session(records, total=1))
        df = loader.fetch_marine_accidents(2020, 2020)
        assert "injury_count" in df.columns

    def test_latitude_column_present(self) -> None:
        records = [_make_carol_record(latitude=29.5)]
        loader = NTSBMarineLoader(session=_make_session(records, total=1))
        df = loader.fetch_marine_accidents(2020, 2020)
        assert "latitude" in df.columns

    def test_longitude_column_present(self) -> None:
        records = [_make_carol_record(longitude=-94.8)]
        loader = NTSBMarineLoader(session=_make_session(records, total=1))
        df = loader.fetch_marine_accidents(2020, 2020)
        assert "longitude" in df.columns

    def test_empty_dataframe_on_api_error(self) -> None:
        """API failures should return empty DataFrame, not raise."""
        session = MagicMock()
        from requests.exceptions import ConnectionError as ReqConnError

        session.post.side_effect = ReqConnError("connection refused")
        loader = NTSBMarineLoader(session=session)
        df = loader.fetch_marine_accidents(2020, 2020)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_empty_dataframe_on_empty_api_response(self) -> None:
        loader = NTSBMarineLoader(session=_make_session([], total=0))
        df = loader.fetch_marine_accidents(2020, 2020)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_pagination_stops_when_results_below_page_size(self) -> None:
        """If first page returns fewer records than page_size, only one POST is made."""
        records = [_make_carol_record(f"MAR20AB{i:03d}") for i in range(3)]
        session = _make_session(records)  # no total; 3 < page_size=100
        loader = NTSBMarineLoader(page_size=100, session=session)
        loader.fetch_marine_accidents(2020, 2020)
        assert session.post.call_count == 1

    def test_pagination_stops_when_total_count_reached(self) -> None:
        """Loader stops fetching pages once total_count records are accumulated."""
        records = [_make_carol_record(f"MAR20AB{i:03d}") for i in range(2)]
        session = _make_session(records, total=2)
        loader = NTSBMarineLoader(page_size=2, session=session)
        loader.fetch_marine_accidents(2020, 2020)
        # Only one page needed to reach total=2
        assert session.post.call_count == 1

    def test_year_range_used_in_payload(self) -> None:
        """Loader sends year-range filters in the POST body."""
        records = [_make_carol_record()]
        session = _make_session(records, total=1)
        loader = NTSBMarineLoader(session=session)
        loader.fetch_marine_accidents(2019, 2022)

        call_kwargs = session.post.call_args
        body = call_kwargs[1].get("json") or call_kwargs[0][1]  # positional or kwarg

        rules = body["QueryGroups"][0]["QueryRules"]
        rule_values = [r["RuleValue"] for r in rules]
        assert "2019-01-01" in rule_values
        assert "2022-12-31" in rule_values


# ---------------------------------------------------------------------------
# NTSBMarineLoader.fetch_to_records
# ---------------------------------------------------------------------------


class TestFetchToRecords:
    def test_returns_list(self) -> None:
        records = [_make_carol_record()]
        loader = NTSBMarineLoader(session=_make_session(records, total=1))
        result = loader.fetch_to_records(2020, 2020)
        assert isinstance(result, list)

    def test_each_item_is_taxonomy_record(self) -> None:
        records = [_make_carol_record()]
        loader = NTSBMarineLoader(session=_make_session(records, total=1))
        result = loader.fetch_to_records(2020, 2020)
        assert all(isinstance(r, TaxonomyRecord) for r in result)

    def test_source_is_ntsb(self) -> None:
        records = [_make_carol_record()]
        loader = NTSBMarineLoader(session=_make_session(records, total=1))
        result = loader.fetch_to_records(2020, 2020)
        assert all(r.source == "ntsb" for r in result)

    def test_root_cause_is_enum(self) -> None:
        records = [_make_carol_record()]
        loader = NTSBMarineLoader(session=_make_session(records, total=1))
        result = loader.fetch_to_records(2020, 2020)
        for r in result:
            assert isinstance(r.root_cause, RootCauseType)

    def test_human_error_classified_from_probable_cause(self) -> None:
        records = [
            _make_carol_record(probable_cause="Operator error and watchkeeping failure")
        ]
        loader = NTSBMarineLoader(session=_make_session(records, total=1))
        result = loader.fetch_to_records(2020, 2020)
        assert result[0].root_cause == RootCauseType.HUMAN_ERROR

    def test_equipment_failure_classified(self) -> None:
        records = [
            _make_carol_record(probable_cause="Steering failure caused loss of control")
        ]
        loader = NTSBMarineLoader(session=_make_session(records, total=1))
        result = loader.fetch_to_records(2020, 2020)
        assert result[0].root_cause == RootCauseType.EQUIPMENT_FAILURE

    def test_empty_on_api_failure(self) -> None:
        session = MagicMock()
        from requests.exceptions import Timeout

        session.post.side_effect = Timeout("timeout")
        loader = NTSBMarineLoader(session=session)
        result = loader.fetch_to_records(2020, 2020)
        assert result == []

    def test_fatality_count_propagated(self) -> None:
        records = [_make_carol_record(fatalities=3)]
        loader = NTSBMarineLoader(session=_make_session(records, total=1))
        result = loader.fetch_to_records(2020, 2020)
        assert result[0].fatality_count == 3

    def test_injury_count_propagated(self) -> None:
        records = [_make_carol_record(injuries=7)]
        loader = NTSBMarineLoader(session=_make_session(records, total=1))
        result = loader.fetch_to_records(2020, 2020)
        assert result[0].injury_count == 7


# ---------------------------------------------------------------------------
# load_dataframe_as_ntsb
# ---------------------------------------------------------------------------


class TestLoadDataframeAsNTSB:
    def test_in_memory_dataframe_classified(self) -> None:
        df = pd.DataFrame(
            {
                "EventId": ["MAR21AB001", "MAR21AB002"],
                "EventDate": ["2021-03-01", "2021-09-15"],
                "VesselName": ["SS Alpha", "MV Beta"],
                "VesselType": ["Tanker", "Cargo Ship"],
                "ProbableCause": ["Equipment failure", "Human error"],
                "FatalCount": [0, 1],
                "InjuryCount": [2, 0],
            }
        )
        records = load_dataframe_as_ntsb(df)
        assert len(records) == 2
        assert all(r.source == "ntsb" for r in records)

    def test_root_cause_equipment_failure(self) -> None:
        df = pd.DataFrame(
            {
                "EventId": ["MAR21AB001"],
                "ProbableCause": ["Machinery failure caused sinking"],
                "FatalCount": [0],
                "InjuryCount": [0],
            }
        )
        records = load_dataframe_as_ntsb(df)
        assert records[0].root_cause == RootCauseType.EQUIPMENT_FAILURE

    def test_empty_dataframe_returns_empty_list(self) -> None:
        records = load_dataframe_as_ntsb(pd.DataFrame())
        assert records == []


# ---------------------------------------------------------------------------
# fetch_ntsb_marine convenience function
# ---------------------------------------------------------------------------


class TestFetchNTSBMarine:
    def test_returns_dataframe(self) -> None:
        records = [_make_carol_record()]
        session = _make_session(records, total=1)
        with patch(
            "worldenergydata.marine_safety.analysis.incidents.ntsb_marine_loader."
            "NTSBMarineLoader._get_session",
            return_value=session,
        ):
            df = fetch_ntsb_marine(2020, 2020)
        assert isinstance(df, pd.DataFrame)


# ---------------------------------------------------------------------------
# CAROL response parsing helpers
# ---------------------------------------------------------------------------


class TestExtractResults:
    def test_list_response(self) -> None:
        data = [{"id": 1}, {"id": 2}]
        assert _extract_results(data) == data

    def test_results_key(self) -> None:
        data = {"Results": [{"id": 1}], "TotalCount": 1}
        assert _extract_results(data) == [{"id": 1}]

    def test_data_key(self) -> None:
        data = {"data": [{"id": 2}]}
        assert _extract_results(data) == [{"id": 2}]

    def test_items_key(self) -> None:
        data = {"Items": [{"id": 3}]}
        assert _extract_results(data) == [{"id": 3}]

    def test_records_key(self) -> None:
        data = {"records": [{"id": 4}]}
        assert _extract_results(data) == [{"id": 4}]

    def test_investigations_key(self) -> None:
        data = {"Investigations": [{"id": 5}]}
        assert _extract_results(data) == [{"id": 5}]

    def test_unknown_structure_returns_empty(self) -> None:
        data = {"unknownKey": "value"}
        assert _extract_results(data) == []

    def test_none_like_input_returns_empty(self) -> None:
        assert _extract_results({}) == []
        assert _extract_results("not a dict or list") == []


class TestExtractTotalCount:
    def test_total_count_key(self) -> None:
        assert _extract_total_count({"TotalCount": 150}) == 150

    def test_total_records_key(self) -> None:
        assert _extract_total_count({"TotalRecords": 200}) == 200

    def test_total_lower_key(self) -> None:
        assert _extract_total_count({"total": 50}) == 50

    def test_result_count_key(self) -> None:
        assert _extract_total_count({"ResultCount": 75}) == 75

    def test_pagination_nested(self) -> None:
        data = {"Pagination": {"TotalRecords": 300}}
        assert _extract_total_count(data) == 300

    def test_non_dict_returns_none(self) -> None:
        assert _extract_total_count([]) is None
        assert _extract_total_count("string") is None

    def test_invalid_value_returns_none(self) -> None:
        assert _extract_total_count({"TotalCount": "not-a-number"}) is None


class TestMapCarolRecord:
    def test_maps_event_id(self) -> None:
        raw = {"EventId": "MAR20AB001", "EventDate": "2020-01-01"}
        mapped = _map_carol_record(raw)
        assert mapped is not None
        assert mapped["EventId"] == "MAR20AB001"

    def test_returns_none_for_missing_id(self) -> None:
        raw = {"EventDate": "2020-01-01", "VesselName": "MV Test"}
        assert _map_carol_record(raw) is None

    def test_maps_event_date(self) -> None:
        raw = {"EventId": "MAR20AB001", "EventDate": "2020-06-15"}
        mapped = _map_carol_record(raw)
        assert mapped["EventDate"] == "2020-06-15"

    def test_maps_vessel_name(self) -> None:
        raw = {"EventId": "MAR20AB001", "VesselName": "SS Stormcrow"}
        mapped = _map_carol_record(raw)
        assert mapped["VesselName"] == "SS Stormcrow"

    def test_maps_probable_cause(self) -> None:
        raw = {"EventId": "MAR20AB001", "ProbableCause": "Watchkeeping failure"}
        mapped = _map_carol_record(raw)
        assert mapped["ProbableCause"] == "Watchkeeping failure"

    def test_maps_fatal_count(self) -> None:
        raw = {"EventId": "MAR20AB001", "FatalCount": 2}
        mapped = _map_carol_record(raw)
        assert mapped["FatalCount"] == 2

    def test_maps_injury_count(self) -> None:
        raw = {"EventId": "MAR20AB001", "InjuryCount": 5}
        mapped = _map_carol_record(raw)
        assert mapped["InjuryCount"] == 5

    def test_maps_coordinates(self) -> None:
        raw = {"EventId": "MAR20AB001", "Latitude": 29.3, "Longitude": -94.8}
        mapped = _map_carol_record(raw)
        assert mapped["Latitude"] == pytest.approx(29.3)
        assert mapped["Longitude"] == pytest.approx(-94.8)

    def test_none_values_excluded(self) -> None:
        raw = {"EventId": "MAR20AB001"}
        mapped = _map_carol_record(raw)
        assert None not in mapped.values()

    def test_ntsbid_alternative_key(self) -> None:
        """Should recognise NtsbNumber as the event identifier."""
        raw = {"NtsbNumber": "MAR20AB999", "EventDate": "2020-01-01"}
        mapped = _map_carol_record(raw)
        assert mapped is not None
        assert mapped["EventId"] == "MAR20AB999"


# ---------------------------------------------------------------------------
# _first_value, _first_float, _first_int helpers
# ---------------------------------------------------------------------------


class TestFirstValueHelper:
    def test_returns_first_non_empty(self) -> None:
        record = {"A": "", "B": "  ", "C": "hello"}
        assert _first_value(record, ["A", "B", "C"]) == "hello"

    def test_returns_none_when_all_empty(self) -> None:
        assert _first_value({"A": ""}, ["A", "B"]) is None

    def test_strips_whitespace(self) -> None:
        assert _first_value({"A": "  val  "}, ["A"]) == "val"


class TestFirstFloatHelper:
    def test_returns_first_parseable_float(self) -> None:
        record = {"lat": "51.5", "Lat": 52.0}
        assert _first_float(record, ["lat", "Lat"]) == pytest.approx(51.5)

    def test_skips_invalid_values(self) -> None:
        record = {"A": "not-a-float", "B": 3.14}
        assert _first_float(record, ["A", "B"]) == pytest.approx(3.14)

    def test_returns_none_when_no_valid_float(self) -> None:
        assert _first_float({"A": "xyz"}, ["A", "B"]) is None


class TestFirstIntHelper:
    def test_returns_first_parseable_int(self) -> None:
        record = {"fatal": 3}
        assert _first_int(record, ["fatal"]) == 3

    def test_coerces_float_string_to_int(self) -> None:
        record = {"count": "2.0"}
        assert _first_int(record, ["count"]) == 2

    def test_returns_none_when_no_valid_int(self) -> None:
        assert _first_int({"A": "abc"}, ["A"]) is None
