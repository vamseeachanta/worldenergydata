"""Tests for canada.analysis.analysis CanadaAnalysis."""

import pytest

from worldenergydata.canada.analysis.analysis import CanadaAnalysis


class TestCanadaAnalysisInit:
    def test_module_name(self):
        ca = CanadaAnalysis()
        assert ca.module_name == "canada_analysis"


class TestRouter:
    def test_summary_analysis(self):
        ca = CanadaAnalysis()
        cfg = {"analysis": {"type": "summary"}, "canada": {}}
        data = {
            "alberta": {"wells": [{"id": 1}, {"id": 2}]},
            "bc": {"wells": [{"id": 3}]},
        }
        result = ca.router(cfg, data)
        assert result["canada"]["analysis_status"] == "completed"
        results = result["canada"]["analysis_results"]
        assert "alberta" in results["provinces_included"]
        assert "bc" in results["provinces_included"]

    def test_default_analysis_type(self):
        ca = CanadaAnalysis()
        cfg = {"canada": {}}
        data = {}
        result = ca.router(cfg, data)
        assert result["canada"]["analysis_status"] == "completed"

    def test_custom_basename(self):
        ca = CanadaAnalysis()
        cfg = {"basename": "my_canada", "my_canada": {}, "analysis": {"type": "summary"}}
        data = {}
        result = ca.router(cfg, data)
        assert "analysis_results" in result["my_canada"]

    def test_error_handling(self):
        ca = CanadaAnalysis()
        # _run_analysis raises => error path; but error handler also needs cfg["canada"]
        cfg = {"analysis": {"type": "summary"}, "canada": {}}
        # Provide data that causes an error in _analyze_summary logic
        # by using a non-dict province_data that still enters the loop
        data = {"bad_province": "not_a_dict"}
        result = ca.router(cfg, data)
        # Should still complete since summary handles non-dict gracefully
        assert result["canada"]["analysis_status"] == "completed"


class TestAnalyzeSummary:
    def test_with_province_data(self):
        ca = CanadaAnalysis()
        data = {
            "alberta": {"wells": [{"id": 1}], "production": [{"vol": 100}]},
            "bc": {"wells": [{"id": 2}]},
        }
        result = ca._analyze_summary({}, data)
        assert "alberta" in result["provinces_included"]
        assert "bc" in result["provinces_included"]
        assert "wells" in result["data_types"]
        assert "production" in result["data_types"]
        assert result["record_counts"]["alberta_wells"] == 1
        assert result["record_counts"]["alberta_production"] == 1

    def test_empty_data(self):
        ca = CanadaAnalysis()
        result = ca._analyze_summary({}, {})
        assert result["provinces_included"] == []
        assert result["data_types"] == []
        assert result["record_counts"] == {}

    def test_skips_error_entries(self):
        ca = CanadaAnalysis()
        data = {"alberta": {"error": "connection failed"}}
        result = ca._analyze_summary({}, data)
        assert "alberta" not in result["provinces_included"]


class TestAnalysisMethods:
    def test_production_comparison(self):
        ca = CanadaAnalysis()
        result = ca._analyze_production_comparison({}, {})
        assert result["analysis_type"] == "production_comparison"
        assert result["status"] == "pending_implementation"

    def test_trend_analysis(self):
        ca = CanadaAnalysis()
        result = ca._analyze_trends({}, {})
        assert result["analysis_type"] == "trend_analysis"

    def test_operator_portfolio(self):
        ca = CanadaAnalysis()
        result = ca._analyze_operator_portfolio({}, {})
        assert result["analysis_type"] == "operator_portfolio"

    def test_well_performance(self):
        ca = CanadaAnalysis()
        result = ca._analyze_well_performance({}, {})
        assert result["analysis_type"] == "well_performance"


class TestCompareProduction:
    def test_basic_comparison(self):
        ca = CanadaAnalysis()
        result = ca.compare_production([], [], metric="oil_volume")
        assert result["metric"] == "oil_volume"
        assert result["period"] == "monthly"
        assert "aer_total" in result
        assert "bcer_total" in result

    def test_custom_period(self):
        ca = CanadaAnalysis()
        result = ca.compare_production([], [], period="quarterly")
        assert result["period"] == "quarterly"


class TestGetTopProducers:
    def test_returns_list(self):
        ca = CanadaAnalysis()
        result = ca.get_top_producers({}, limit=5)
        assert isinstance(result, list)
        assert result == []
