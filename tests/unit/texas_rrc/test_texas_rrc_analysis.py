"""Tests for Texas RRC analysis router module."""

import pytest

from worldenergydata.texas_rrc.analysis.texas_rrc_analysis import TexasRRCAnalysis

# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


class TestTexasRRCAnalysisInit:
    def test_defaults(self):
        analysis = TexasRRCAnalysis()
        assert analysis._production_processor is None
        assert analysis._well_processor is None
        assert analysis._permit_processor is None

    def test_lazy_production_processor(self):
        analysis = TexasRRCAnalysis()
        proc = analysis.production_processor
        assert proc is not None
        # Should return same instance on second access
        assert analysis.production_processor is proc

    def test_lazy_well_processor(self):
        analysis = TexasRRCAnalysis()
        proc = analysis.well_processor
        assert proc is not None
        assert analysis.well_processor is proc

    def test_lazy_permit_processor(self):
        analysis = TexasRRCAnalysis()
        proc = analysis.permit_processor
        assert proc is not None
        assert analysis.permit_processor is proc


# ---------------------------------------------------------------------------
# _summary_analysis
# ---------------------------------------------------------------------------


class TestSummaryAnalysis:
    def test_empty_data(self):
        analysis = TexasRRCAnalysis()
        result = analysis._summary_analysis({})
        assert result["data_types_available"] == []
        assert result["statistics"] == {}

    def test_with_file_path(self):
        analysis = TexasRRCAnalysis()
        data = {"production": {"file_path": "/tmp/data.csv", "status": "downloaded"}}
        result = analysis._summary_analysis(data)
        assert "production" in result["statistics"]
        assert result["statistics"]["production"]["status"] == "downloaded"

    def test_with_results(self):
        analysis = TexasRRCAnalysis()
        data = {"wells": {"results": [{"id": 1}, {"id": 2}]}}
        result = analysis._summary_analysis(data)
        assert result["statistics"]["wells"]["result_count"] == 2

    def test_multiple_data_types(self):
        analysis = TexasRRCAnalysis()
        data = {
            "production": {"file_path": "/tmp/prod.csv", "status": "ok"},
            "wells": {"results": [{"id": 1}]},
        }
        result = analysis._summary_analysis(data)
        assert "production" in result["data_types_available"]
        assert "wells" in result["data_types_available"]


# ---------------------------------------------------------------------------
# _trend_analysis
# ---------------------------------------------------------------------------


class TestTrendAnalysis:
    def test_returns_not_implemented(self):
        analysis = TexasRRCAnalysis()
        result = analysis._trend_analysis({}, {})
        assert result["status"] == "not_implemented"


# ---------------------------------------------------------------------------
# _run_analysis
# ---------------------------------------------------------------------------


class TestRunAnalysis:
    def test_summary(self):
        analysis = TexasRRCAnalysis()
        result = analysis._run_analysis("summary", {}, "district", {})
        assert "data_types_available" in result

    def test_trends(self):
        analysis = TexasRRCAnalysis()
        result = analysis._run_analysis("trends", {}, "district", {})
        assert result["status"] == "not_implemented"

    def test_unknown(self):
        analysis = TexasRRCAnalysis()
        result = analysis._run_analysis("unknown_type", {}, "district", {})
        assert "error" in result

    def test_production_file_path(self):
        analysis = TexasRRCAnalysis()
        data = {"production": {"file_path": "/tmp/data.csv"}}
        result = analysis._run_analysis("production", data, "district", {})
        assert result["status"] == "file_downloaded"

    def test_production_no_records(self):
        analysis = TexasRRCAnalysis()
        data = {"production": {}}
        result = analysis._run_analysis("production", data, "district", {})
        assert "error" in result

    def test_wells_file_path(self):
        analysis = TexasRRCAnalysis()
        data = {"wells": {"file_path": "/tmp/wells.csv"}}
        result = analysis._run_analysis("wells", data, "district", {})
        assert result["status"] == "file_downloaded"

    def test_wells_no_records(self):
        analysis = TexasRRCAnalysis()
        data = {"wells": {}}
        result = analysis._run_analysis("wells", data, "district", {})
        assert "error" in result

    def test_permits_file_path(self):
        analysis = TexasRRCAnalysis()
        data = {"drilling_permits": {"file_path": "/tmp/permits.csv"}}
        result = analysis._run_analysis("permits", data, "district", {})
        assert result["status"] == "file_downloaded"

    def test_permits_no_records(self):
        analysis = TexasRRCAnalysis()
        data = {"drilling_permits": {}}
        result = analysis._run_analysis("permits", data, "district", {})
        assert "error" in result


# ---------------------------------------------------------------------------
# router
# ---------------------------------------------------------------------------


class TestRouter:
    def test_default_summary(self):
        analysis = TexasRRCAnalysis()
        cfg = {}
        data = {}
        result = analysis.router(cfg, data)
        assert result is cfg  # Returns updated cfg

    def test_with_analysis_types(self):
        analysis = TexasRRCAnalysis()
        cfg = {"analysis": {"types": ["summary", "trends"]}}
        result = analysis.router(cfg, {})
        # No exception raised

    def test_with_basename(self):
        analysis = TexasRRCAnalysis()
        cfg = {
            "basename": "texas_rrc",
            "texas_rrc": {},
            "analysis": {"types": ["summary"]},
        }
        result = analysis.router(cfg, {})
        assert "analysis" in result["texas_rrc"]
        assert "completed" in result["texas_rrc"]["analysis"]

    def test_error_handling(self):
        analysis = TexasRRCAnalysis()
        cfg = {"analysis": {"types": ["unknown"]}}
        result = analysis.router(cfg, {})
        # No exception, unknown types return error dict
