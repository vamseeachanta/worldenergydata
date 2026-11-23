"""Tests for Nigeria monthly blend/stream production loader."""

from unittest.mock import MagicMock, patch

import pytest

from worldenergydata.west_africa.nigeria.blend_production import (
    BlendProductionLoader,
    BlendRecord,
    aggregate_by_blend,
    filter_by_period,
)

SAMPLE_RECORDS = [
    BlendRecord(blend="BONNY LIGHT", volume_kbd=152.3, month=1, year=2024),
    BlendRecord(blend="BONNY LIGHT", volume_kbd=148.7, month=2, year=2024),
    BlendRecord(blend="QUAT IBOE", volume_kbd=52.1, month=1, year=2024),
    BlendRecord(blend="FORCADOS", volume_kbd=78.4, month=1, year=2024),
    BlendRecord(blend="FORCADOS", volume_kbd=81.2, month=2, year=2024),
]


class TestBlendRecord:
    def test_blend_record_creation(self):
        r = BlendRecord(blend="BONNY LIGHT", volume_kbd=150.0, month=1, year=2024)
        assert r.blend == "BONNY LIGHT"
        assert r.volume_kbd == 150.0
        assert r.month == 1
        assert r.year == 2024

    def test_volume_cannot_be_negative(self):
        with pytest.raises(ValueError):
            BlendRecord(blend="TEST", volume_kbd=-10.0, month=1, year=2024)

    def test_month_range_validation(self):
        with pytest.raises(ValueError):
            BlendRecord(blend="TEST", volume_kbd=10.0, month=13, year=2024)
        with pytest.raises(ValueError):
            BlendRecord(blend="TEST", volume_kbd=10.0, month=0, year=2024)

    def test_year_reasonable_range(self):
        with pytest.raises(ValueError):
            BlendRecord(blend="TEST", volume_kbd=10.0, month=1, year=1950)


class TestAggregateByBlend:
    def test_returns_dict(self):
        result = aggregate_by_blend(SAMPLE_RECORDS)
        assert isinstance(result, dict)

    def test_sums_volumes_correctly(self):
        result = aggregate_by_blend(SAMPLE_RECORDS)
        assert result["BONNY LIGHT"] == pytest.approx(152.3 + 148.7, abs=0.01)

    def test_all_blends_present(self):
        result = aggregate_by_blend(SAMPLE_RECORDS)
        assert "BONNY LIGHT" in result
        assert "QUAT IBOE" in result
        assert "FORCADOS" in result

    def test_empty_input_returns_empty_dict(self):
        result = aggregate_by_blend([])
        assert result == {}


class TestFilterByPeriod:
    def test_filter_by_year(self):
        result = filter_by_period(SAMPLE_RECORDS, year=2024)
        assert len(result) == 5

    def test_filter_by_year_and_month(self):
        result = filter_by_period(SAMPLE_RECORDS, year=2024, month=1)
        assert len(result) == 3

    def test_filter_no_match_returns_empty(self):
        result = filter_by_period(SAMPLE_RECORDS, year=2023)
        assert result == []

    def test_filter_returns_list(self):
        result = filter_by_period(SAMPLE_RECORDS, year=2024)
        assert isinstance(result, list)


class TestBlendProductionLoader:
    @patch("worldenergydata.west_africa.nigeria.blend_production" ".NuprcClient")
    def test_loader_initialises(self, mock_client_cls):
        loader = BlendProductionLoader()
        assert loader is not None

    @patch("worldenergydata.west_africa.nigeria.blend_production" ".NuprcClient")
    def test_load_returns_list(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.download_pdf.return_value = b""
        mock_client_cls.return_value = mock_client

        loader = BlendProductionLoader()
        result = loader.load(year=2024, month=1)
        assert isinstance(result, list)

    @patch("worldenergydata.west_africa.nigeria.blend_production" ".NuprcClient")
    def test_load_handles_missing_pdf_gracefully(self, mock_client_cls):
        from worldenergydata.west_africa.nigeria.nuprc_client import NuprcAPIError

        mock_client = MagicMock()
        mock_client.download_pdf.side_effect = NuprcAPIError("not found")
        mock_client_cls.return_value = mock_client

        loader = BlendProductionLoader()
        result = loader.load(year=2024, month=1)
        assert result == []

    def test_total_production_sums_volumes(self):
        loader = BlendProductionLoader.__new__(BlendProductionLoader)
        total = loader.total_production(SAMPLE_RECORDS)
        expected = 152.3 + 148.7 + 52.1 + 78.4 + 81.2
        assert total == pytest.approx(expected, abs=0.01)

    def test_total_production_empty_list(self):
        loader = BlendProductionLoader.__new__(BlendProductionLoader)
        assert loader.total_production([]) == 0.0
