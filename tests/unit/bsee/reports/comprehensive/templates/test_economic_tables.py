"""Tests for economic sensitivity analysis tables."""

import pytest

from worldenergydata.bsee.reports.comprehensive.templates.economic_tables import (
    generate_sensitivity_analysis_tables,
)


class TestGenerateSensitivityAnalysisTablesEmpty:
    def test_empty_context_returns_error(self):
        result = generate_sensitivity_analysis_tables({})
        assert "error" in result

    def test_none_context_returns_error(self):
        result = generate_sensitivity_analysis_tables(None)
        assert "error" in result


def _make_context(**overrides):
    defaults = {
        "oil_price": 75.0,
        "gas_price": 3.50,
        "annual_oil_bbl": 100000,
        "annual_gas_mcf": 500000,
        "operating_costs": 2500000,
        "initial_capex": 10000000,
        "decline_rate": 0.08,
    }
    defaults.update(overrides)
    return defaults


class TestOilPriceSensitivity:
    def test_table_present(self):
        result = generate_sensitivity_analysis_tables(_make_context())
        assert "oil_price_sensitivity" in result

    def test_table_is_html(self):
        result = generate_sensitivity_analysis_tables(_make_context())
        assert "<table" in result["oil_price_sensitivity"]

    def test_table_has_caption(self):
        result = generate_sensitivity_analysis_tables(_make_context())
        assert "Oil Price Sensitivity" in result["oil_price_sensitivity"]

    def test_table_has_rows(self):
        result = generate_sensitivity_analysis_tables(_make_context())
        html = result["oil_price_sensitivity"]
        # 6 oil price scenarios: 50, 60, 70, 80, 90, 100
        assert "$50" in html
        assert "$100" in html


class TestGasPriceSensitivity:
    def test_table_present(self):
        result = generate_sensitivity_analysis_tables(_make_context())
        assert "gas_price_sensitivity" in result

    def test_table_is_html(self):
        result = generate_sensitivity_analysis_tables(_make_context())
        assert "<table" in result["gas_price_sensitivity"]

    def test_table_has_caption(self):
        result = generate_sensitivity_analysis_tables(_make_context())
        assert "Gas Price Sensitivity" in result["gas_price_sensitivity"]


class TestScenarioMatrix:
    def test_matrix_present(self):
        result = generate_sensitivity_analysis_tables(_make_context())
        assert "scenario_matrix" in result

    def test_matrix_is_html(self):
        result = generate_sensitivity_analysis_tables(_make_context())
        assert "<table" in result["scenario_matrix"]

    def test_matrix_has_oil_rows(self):
        result = generate_sensitivity_analysis_tables(_make_context())
        html = result["scenario_matrix"]
        assert "$60/bbl" in html
        assert "$75/bbl" in html
        assert "$90/bbl" in html

    def test_matrix_has_gas_columns(self):
        result = generate_sensitivity_analysis_tables(_make_context())
        html = result["scenario_matrix"]
        assert "$2.5/mcf" in html
        assert "$3.5/mcf" in html
        assert "$4.5/mcf" in html


class TestNPVValues:
    def test_high_price_positive_npv(self):
        result = generate_sensitivity_analysis_tables(
            _make_context(annual_oil_bbl=200000, initial_capex=5000000)
        )
        html = result["oil_price_sensitivity"]
        # High production + low capex = positive NPV, shown in green
        assert "green" in html

    def test_low_production_negative_npv(self):
        result = generate_sensitivity_analysis_tables(
            _make_context(annual_oil_bbl=1000, annual_gas_mcf=1000, initial_capex=50000000)
        )
        html = result["oil_price_sensitivity"]
        # Very low production + high capex = negative NPV, shown in red
        assert "red" in html

    def test_returns_three_tables(self):
        result = generate_sensitivity_analysis_tables(_make_context())
        assert len(result) == 3


class TestWithDefaultValues:
    def test_minimal_context_uses_defaults(self):
        # Pass context with just a flag to trigger non-empty path
        result = generate_sensitivity_analysis_tables({"custom_flag": True})
        # Should use defaults and still produce all tables
        assert "oil_price_sensitivity" in result
        assert "gas_price_sensitivity" in result
        assert "scenario_matrix" in result
