"""Tests for water injection support in FieldProcessor."""

import pytest

from worldenergydata.sodir.processors.field_processor import FieldProcessor


class TestFieldProcessorWaterInjection:
    """Tests for water_injected_sm3 extraction in FieldProcessor."""

    @pytest.fixture
    def processor(self):
        return FieldProcessor()

    @pytest.fixture
    def field_data_with_water_injection(self):
        return {
            "fldName": "EKOFISK",
            "fldNpdidField": "43506",
            "fldStatus": "PRODUCING",
            "fldOperatorName": "ConocoPhillips",
            "fldDiscoveryYear": 1969,
            "fldProductionStartYear": 1971,
            "fldCumulativeOilProduction": 100.0,
            "fldCumulativeGasProduction": 50.0,
            "fldCumulativeWaterInjection": 120.5,
        }

    @pytest.fixture
    def field_data_without_water_injection(self):
        return {
            "fldName": "SMALL FIELD",
            "fldNpdidField": "99999",
            "fldStatus": "PRODUCING",
        }

    def test_process_extracts_water_injected_sm3(
        self, processor, field_data_with_water_injection
    ):
        result = processor.process(field_data_with_water_injection)
        assert result is not None
        assert "cumulative_water_injected_sm3" in result

    def test_water_injected_value_is_correct(
        self, processor, field_data_with_water_injection
    ):
        result = processor.process(field_data_with_water_injection)
        # Input is in million Sm3 from SODIR, stored as-is
        assert result["cumulative_water_injected_sm3"] == pytest.approx(120.5)

    def test_water_injected_none_when_missing(
        self, processor, field_data_without_water_injection
    ):
        result = processor.process(field_data_without_water_injection)
        assert result is not None
        assert result["cumulative_water_injected_sm3"] is None

    def test_water_injected_handles_zero(self, processor):
        data = {
            "fldName": "DRY FIELD",
            "fldCumulativeWaterInjection": 0.0,
        }
        result = processor.process(data)
        assert result["cumulative_water_injected_sm3"] == 0.0

    def test_water_injected_handles_string_value(self, processor):
        data = {
            "fldName": "STRING FIELD",
            "fldCumulativeWaterInjection": "75.3",
        }
        result = processor.process(data)
        assert result["cumulative_water_injected_sm3"] == pytest.approx(75.3)

    def test_water_injected_handles_invalid_string(self, processor):
        data = {
            "fldName": "BAD DATA FIELD",
            "fldCumulativeWaterInjection": "not_a_number",
        }
        result = processor.process(data)
        assert result["cumulative_water_injected_sm3"] is None
