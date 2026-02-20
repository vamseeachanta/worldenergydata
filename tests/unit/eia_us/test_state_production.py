"""Tests for US state-level crude production loader."""

import pandas as pd
import pytest

from worldenergydata.eia_us.production.state_production import (
    StateProductionLoader,
    MAJOR_PRODUCING_STATES,
    STATE_SERIES_ID,
)


def make_mock_state_response(state: str, n_months: int = 12):
    """Create mock EIA API response for state production."""
    records = []
    for i in range(n_months):
        year = 2023 + i // 12
        month = (i % 12) + 1
        records.append({
            "period": f"{year}-{month:02d}",
            "value": 1000.0 + i * 10,
            "series-description": f"{state} Field Production of Crude Oil",
            "unit": "Thousand Barrels",
            "state": state,
        })
    return records


class TestMajorProducingStates:
    def test_at_least_10_major_states(self):
        assert len(MAJOR_PRODUCING_STATES) >= 10

    def test_texas_in_major_states(self):
        assert "TX" in MAJOR_PRODUCING_STATES

    def test_north_dakota_in_major_states(self):
        assert "ND" in MAJOR_PRODUCING_STATES

    def test_new_mexico_in_major_states(self):
        assert "NM" in MAJOR_PRODUCING_STATES

    def test_colorado_in_major_states(self):
        assert "CO" in MAJOR_PRODUCING_STATES

    def test_alaska_in_major_states(self):
        assert "AK" in MAJOR_PRODUCING_STATES

    def test_wyoming_in_major_states(self):
        assert "WY" in MAJOR_PRODUCING_STATES


class TestStateSeriesId:
    def test_texas_series_id_format(self):
        series_id = STATE_SERIES_ID("TX")
        assert "TX" in series_id
        assert series_id.startswith("PET.")

    def test_alaska_series_id(self):
        series_id = STATE_SERIES_ID("AK")
        assert "AK" in series_id

    def test_series_id_uppercase(self):
        series_id = STATE_SERIES_ID("nd")
        assert "ND" in series_id


class TestStateProductionLoader:
    @pytest.fixture
    def loader(self):
        return StateProductionLoader()

    def test_load_returns_dataframe(self, loader):
        raw = make_mock_state_response("TX", 12)
        df = loader.load(raw, state="TX")
        assert isinstance(df, pd.DataFrame)

    def test_load_has_required_columns(self, loader):
        raw = make_mock_state_response("TX", 12)
        df = loader.load(raw, state="TX")
        for col in ["state", "year", "month", "crude_bbl"]:
            assert col in df.columns, f"Missing column: {col}"

    def test_load_state_column_uppercase(self, loader):
        raw = make_mock_state_response("tx", 12)
        df = loader.load(raw, state="tx")
        assert df["state"].iloc[0] == "TX"

    def test_load_converts_thousand_barrels_to_bbl(self, loader):
        raw = [{"period": "2024-01", "value": 10.0, "state": "TX", "unit": "Thousand Barrels"}]
        df = loader.load(raw, state="TX")
        assert df["crude_bbl"].iloc[0] == pytest.approx(10_000.0)

    def test_load_empty_returns_empty_dataframe(self, loader):
        df = loader.load([], state="TX")
        assert df.empty
        assert "crude_bbl" in df.columns

    def test_load_handles_null_values(self, loader):
        raw = [{"period": "2024-01", "value": None, "state": "TX", "unit": "Thousand Barrels"}]
        df = loader.load(raw, state="TX")
        assert pd.isna(df["crude_bbl"].iloc[0]) or df["crude_bbl"].iloc[0] == 0.0

    def test_annual_total_correct(self, loader):
        raw = make_mock_state_response("TX", 12)
        df = loader.load(raw, state="TX")
        annual = loader.annual_total(df)
        assert "crude_bbl" in annual.columns
        assert annual["year"].iloc[0] == 2023

    def test_filter_by_year(self, loader):
        raw = make_mock_state_response("TX", 24)
        df = loader.load(raw, state="TX")
        filtered = loader.filter_year(df, 2023)
        assert all(filtered["year"] == 2023)

    def test_load_10_states_returns_10_frames(self, loader):
        results = {}
        for state in MAJOR_PRODUCING_STATES[:10]:
            raw = make_mock_state_response(state, 6)
            results[state] = loader.load(raw, state=state)
        assert len(results) == 10
        for state, df in results.items():
            assert not df.empty
