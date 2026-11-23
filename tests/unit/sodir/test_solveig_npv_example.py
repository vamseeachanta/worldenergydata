"""Tests for Solveig NPV example combining forecasting and NPV."""

import pytest

from worldenergydata.sodir.examples.solveig_npv_example import (
    run_solveig_npv_analysis,
)


class TestSolveigNPVExample:
    """Tests for the Solveig NPV analysis example."""

    @pytest.fixture
    def result(self):
        return run_solveig_npv_analysis()

    def test_returns_dict(self, result):
        assert isinstance(result, dict)

    def test_has_npv(self, result):
        assert "npv" in result

    def test_npv_is_numeric(self, result):
        assert isinstance(result["npv"], (int, float))

    def test_has_irr(self, result):
        assert "irr" in result

    def test_irr_is_plausible(self, result):
        # IRR should be a reasonable percentage or None
        if result["irr"] is not None:
            assert -1.0 <= result["irr"] <= 5.0

    def test_has_field_name(self, result):
        assert result["field_name"] == "SOLVEIG"

    def test_has_proxy_field(self, result):
        assert result["proxy_field"] == "EDVARD GRIEG"

    def test_has_production_forecast(self, result):
        assert "production_forecast" in result

    def test_production_forecast_has_values(self, result):
        assert len(result["production_forecast"]) > 0

    def test_has_cash_flows(self, result):
        assert "cash_flows" in result
