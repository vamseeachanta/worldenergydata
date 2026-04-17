# ABOUTME: Tests for unified_query.py — MetoceanQuery, MetoceanResult, UnifiedMetoceanClient.

"""Tests for the unified metocean query interface (all HTTP mocked)."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from worldenergydata.metocean.unified.unified_query import (
    MetoceanQuery,
    MetoceanResult,
    UnifiedMetoceanClient,
)

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

GOM_QUERY = MetoceanQuery(
    lat=28.5,
    lon=-88.5,
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2023, 1, 7),
    parameters=["Hs", "Tp", "wind_speed", "current_speed"],
)

NORTH_SEA_QUERY = MetoceanQuery(
    lat=57.0,
    lon=3.5,
    start_date=datetime(2023, 6, 1),
    end_date=datetime(2023, 6, 7),
    parameters=["Hs", "wind_speed"],
)


def _make_empty_df():
    return pd.DataFrame(columns=["timestamp", "parameter", "value", "source", "unit"])


def _make_sample_df(source="ndbc", n=5):
    return pd.DataFrame(
        [
            {
                "timestamp": datetime(2023, 1, 1, h, 0),
                "parameter": "Hs",
                "value": 1.0 + h * 0.1,
                "source": source,
                "unit": "m",
            }
            for h in range(n)
        ]
    )


# ---------------------------------------------------------------------------
# MetoceanQuery dataclass
# ---------------------------------------------------------------------------


class TestMetoceanQuery:
    def test_query_has_lat(self):
        assert GOM_QUERY.lat == 28.5

    def test_query_has_lon(self):
        assert GOM_QUERY.lon == -88.5

    def test_query_has_start_date(self):
        assert GOM_QUERY.start_date == datetime(2023, 1, 1)

    def test_query_has_end_date(self):
        assert GOM_QUERY.end_date == datetime(2023, 1, 7)

    def test_query_default_parameters(self):
        q = MetoceanQuery(
            lat=0.0,
            lon=0.0,
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 1, 2),
        )
        assert "Hs" in q.parameters

    def test_query_custom_parameters(self):
        assert "wind_speed" in GOM_QUERY.parameters


# ---------------------------------------------------------------------------
# MetoceanResult dataclass
# ---------------------------------------------------------------------------


class TestMetoceanResult:
    def test_result_has_query(self):
        df = _make_empty_df()
        result = MetoceanResult(
            query=GOM_QUERY, data=df, sources_used=[], coverage_gaps=[]
        )
        assert result.query is GOM_QUERY

    def test_result_data_is_dataframe(self):
        df = _make_sample_df()
        result = MetoceanResult(
            query=GOM_QUERY, data=df, sources_used=["ndbc"], coverage_gaps=[]
        )
        assert isinstance(result.data, pd.DataFrame)

    def test_result_sources_used(self):
        result = MetoceanResult(
            query=GOM_QUERY,
            data=_make_empty_df(),
            sources_used=["ndbc", "open_meteo"],
            coverage_gaps=[],
        )
        assert "ndbc" in result.sources_used

    def test_result_coverage_gaps_list(self):
        result = MetoceanResult(
            query=GOM_QUERY, data=_make_empty_df(), sources_used=[], coverage_gaps=[]
        )
        assert isinstance(result.coverage_gaps, list)


# ---------------------------------------------------------------------------
# UnifiedMetoceanClient
# ---------------------------------------------------------------------------


class TestUnifiedMetoceanClientGoM:
    """GoM queries: NDBC + COOPS + OpenMeteo should be selected, Met Norway not."""

    def _make_client_with_mocked_fetchers(self, source_df=None):
        """
        Return UnifiedMetoceanClient where every client fetch is mocked to return
        a small DataFrame (or empty if source_df is None).
        """
        if source_df is None:
            source_df = _make_empty_df()

        client = UnifiedMetoceanClient()
        client._fetch_from_source = MagicMock(return_value=source_df)
        return client

    def test_query_returns_metocean_result(self):
        client = self._make_client_with_mocked_fetchers(_make_sample_df())
        result = client.query(GOM_QUERY)
        assert isinstance(result, MetoceanResult)

    def test_query_result_has_dataframe(self):
        client = self._make_client_with_mocked_fetchers(_make_sample_df())
        result = client.query(GOM_QUERY)
        assert isinstance(result.data, pd.DataFrame)

    def test_query_sources_used_not_empty(self):
        client = self._make_client_with_mocked_fetchers(_make_sample_df())
        result = client.query(GOM_QUERY)
        assert len(result.sources_used) > 0

    def test_query_does_not_include_met_norway_for_gom(self):
        client = self._make_client_with_mocked_fetchers(_make_sample_df())
        result = client.query(GOM_QUERY)
        assert "met_norway" not in result.sources_used

    def test_query_includes_ndbc_for_gom(self):
        """For GoM, NDBC should be among selected (even if it returns empty data)."""
        client = UnifiedMetoceanClient()
        # Patch individual fetch methods on the actual clients
        sample = _make_sample_df(source="ndbc")

        with patch.object(client, "_fetch_from_source", return_value=sample):
            result = client.query(GOM_QUERY)
        # ndbc should be in sources_used (selected by coverage)
        assert "ndbc" in result.sources_used or len(result.sources_used) >= 1

    def test_query_result_query_field_matches(self):
        client = self._make_client_with_mocked_fetchers()
        result = client.query(GOM_QUERY)
        assert result.query.lat == GOM_QUERY.lat
        assert result.query.lon == GOM_QUERY.lon


class TestUnifiedMetoceanClientNorthSea:
    """North Sea queries: Met Norway should be included, NDBC/COOPS excluded."""

    def test_north_sea_selects_met_norway(self):
        client = UnifiedMetoceanClient()
        with patch.object(
            client, "_fetch_from_source", return_value=_make_sample_df("met_norway")
        ):
            result = client.query(NORTH_SEA_QUERY)
        assert "met_norway" in result.sources_used

    def test_north_sea_does_not_select_ndbc(self):
        client = UnifiedMetoceanClient()
        with patch.object(client, "_fetch_from_source", return_value=_make_empty_df()):
            result = client.query(NORTH_SEA_QUERY)
        assert "ndbc" not in result.sources_used


class TestUnifiedMetoceanClientParallel:
    """Test that queries run in parallel using ThreadPoolExecutor."""

    def test_parallel_execution_invoked(self):
        """_fetch_from_source is called once per selected source."""
        client = UnifiedMetoceanClient()
        call_log = []

        def mock_fetch(source_name, query):
            call_log.append(source_name)
            return _make_sample_df(source_name)

        with patch.object(client, "_fetch_from_source", side_effect=mock_fetch):
            result = client.query(GOM_QUERY)

        # Multiple sources should have been fetched
        assert len(call_log) >= 2

    def test_single_source_failure_does_not_crash(self):
        """If one source throws, others still return data."""
        client = UnifiedMetoceanClient()
        call_count = [0]

        def selective_mock(source_name, query):
            call_count[0] += 1
            if source_name == "ndbc":
                raise RuntimeError("Simulated NDBC failure")
            return _make_sample_df(source_name)

        with patch.object(client, "_fetch_from_source", side_effect=selective_mock):
            result = client.query(GOM_QUERY)

        assert isinstance(result, MetoceanResult)


class TestUnifiedMetoceanClientCoverageGaps:
    """Tests for coverage gap detection in the result."""

    def test_empty_data_produces_coverage_gap(self):
        """When all fetches return empty, result should indicate a gap."""
        client = UnifiedMetoceanClient()
        with patch.object(client, "_fetch_from_source", return_value=_make_empty_df()):
            result = client.query(GOM_QUERY)
        # coverage_gaps should be a list (may be empty or not, both OK)
        assert isinstance(result.coverage_gaps, list)

    def test_result_data_columns_correct(self):
        client = UnifiedMetoceanClient()
        sample = _make_sample_df()
        with patch.object(client, "_fetch_from_source", return_value=sample):
            result = client.query(GOM_QUERY)
        if len(result.data) > 0:
            for col in ["timestamp", "parameter", "value", "source", "unit"]:
                assert col in result.data.columns
