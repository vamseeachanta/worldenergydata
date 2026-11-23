"""Tests for SODIR analysis module."""

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from worldenergydata.sodir.analysis import (
    AnalysisConfig,
    CrossRegionalComparison,
    FieldAnalysisResult,
    FieldAnalyzer,
    MetricsCalculator,
    PortfolioAnalyzer,
    ProductionForecast,
    SodirAnalysis,
    SodirDataLoader,
    TemporalAnalyzer,
)

# ---------------------------------------------------------------------------
# AnalysisConfig dataclass
# ---------------------------------------------------------------------------


class TestAnalysisConfig:
    def test_defaults(self):
        c = AnalysisConfig(input_path="/data", output_path="/out")
        assert c.start_date == "2020-01-01"
        assert c.end_date == "2024-12-31"
        assert c.analysis_type == "comprehensive"
        assert c.discount_rate == 0.08
        assert c.oil_price_scenario == "mid"
        assert c.max_workers == 4
        assert c.fields == []

    def test_custom(self):
        c = AnalysisConfig(
            input_path="/in",
            output_path="/out",
            fields=["Troll", "Ekofisk"],
            include_npv=True,
        )
        assert len(c.fields) == 2
        assert c.include_npv is True

    def test_to_dict(self):
        c = AnalysisConfig(input_path="/in", output_path="/out")
        d = c.to_dict()
        assert d["input_path"] == "/in"
        assert d["temporal_resolution"] == "yearly"


# ---------------------------------------------------------------------------
# FieldAnalysisResult dataclass
# ---------------------------------------------------------------------------


class TestFieldAnalysisResult:
    def test_summary(self):
        r = FieldAnalysisResult(
            field_name="Troll",
            metrics={
                "recovery_efficiency": 0.45,
                "production_maturity": 0.8,
                "economic_viability": 0.9,
            },
        )
        s = r.summary()
        assert s["field_name"] == "Troll"
        assert s["key_metrics"]["recovery_efficiency"] == 0.45
        assert "timestamp" in s

    def test_summary_missing_metrics(self):
        r = FieldAnalysisResult(field_name="Empty", metrics={})
        s = r.summary()
        assert s["key_metrics"]["recovery_efficiency"] == 0
        assert s["key_metrics"]["economic_viability"] == 0


# ---------------------------------------------------------------------------
# CrossRegionalComparison dataclass
# ---------------------------------------------------------------------------


class TestCrossRegionalComparison:
    def test_init(self):
        c = CrossRegionalComparison(
            sodir_metrics={"total_fields": 10},
            bsee_metrics={"total_fields": 20},
            comparison_results={"diff": 10},
        )
        assert c.sodir_metrics["total_fields"] == 10
        assert c.statistical_tests is None


# ---------------------------------------------------------------------------
# SodirDataLoader
# ---------------------------------------------------------------------------


class TestSodirDataLoader:
    def test_init(self, tmp_path):
        config = AnalysisConfig(input_path=str(tmp_path), output_path=str(tmp_path))
        loader = SodirDataLoader(config)
        assert loader.data_path == tmp_path

    def test_load_empty_directory(self, tmp_path):
        config = AnalysisConfig(input_path=str(tmp_path), output_path=str(tmp_path))
        loader = SodirDataLoader(config)
        data = loader.load_data()
        assert data == {}

    def test_load_csv_fallback(self, tmp_path):
        config = AnalysisConfig(input_path=str(tmp_path), output_path=str(tmp_path))
        # Write a CSV file
        csv_path = tmp_path / "sodir_fields.csv"
        pd.DataFrame({"field_name": ["Troll"]}).to_csv(csv_path, index=False)
        loader = SodirDataLoader(config)
        data = loader.load_data(["fields"])
        assert "fields" in data
        assert data["fields"]["field_name"].iloc[0] == "Troll"


# ---------------------------------------------------------------------------
# SodirAnalysis - init
# ---------------------------------------------------------------------------


class TestSodirAnalysisInit:
    def test_from_config(self, tmp_path):
        config = AnalysisConfig(input_path=str(tmp_path), output_path=str(tmp_path))
        analysis = SodirAnalysis(config)
        assert analysis.config.analysis_type == "comprehensive"

    def test_from_dict(self, tmp_path):
        analysis = SodirAnalysis(
            {
                "input_path": str(tmp_path),
                "output_path": str(tmp_path),
            }
        )
        assert analysis.config.analysis_type == "comprehensive"

    def test_from_dict_with_output_dir(self, tmp_path):
        analysis = SodirAnalysis({"output_dir": str(tmp_path)})
        assert analysis.config.output_path == str(tmp_path)

    def test_processors_initialized(self, tmp_path):
        config = AnalysisConfig(input_path=str(tmp_path), output_path=str(tmp_path))
        analysis = SodirAnalysis(config)
        assert "field_analyzer" in analysis.processors
        assert "metrics_calculator" in analysis.processors


# ---------------------------------------------------------------------------
# SodirAnalysis - analyze_field
# ---------------------------------------------------------------------------


def _make_field_data():
    return pd.DataFrame(
        {
            "field_name": ["Troll"],
            "recoverable_oil_mmbbl": [1000.0],
            "recoverable_gas_bcf": [5000.0],
            "water_depth_m": [300.0],
            "recovery_factor": [0.5],
            "discovery_year": [1979],
            "status": ["PRODUCING"],
            "production_start": [1995],
        }
    )


class TestSodirAnalysisField:
    def test_no_data_raises(self, tmp_path):
        analysis = SodirAnalysis(
            AnalysisConfig(input_path=str(tmp_path), output_path=str(tmp_path))
        )
        with pytest.raises(ValueError, match="No data loaded"):
            analysis.analyze_field("Troll")

    def test_field_not_found_raises(self, tmp_path):
        analysis = SodirAnalysis(
            AnalysisConfig(input_path=str(tmp_path), output_path=str(tmp_path))
        )
        analysis.data = {"fields": _make_field_data()}
        with pytest.raises(KeyError, match="Field not found"):
            analysis.analyze_field("NonExistent")

    def test_analyze_field_basic(self, tmp_path):
        analysis = SodirAnalysis(
            AnalysisConfig(input_path=str(tmp_path), output_path=str(tmp_path))
        )
        analysis.data = {"fields": _make_field_data()}
        result = analysis.analyze_field("Troll")
        assert result.field_name == "Troll"
        assert isinstance(result.reserves, dict)


# ---------------------------------------------------------------------------
# SodirAnalysis - analyze_portfolio
# ---------------------------------------------------------------------------


class TestSodirAnalysisPortfolio:
    def test_no_data_raises(self, tmp_path):
        analysis = SodirAnalysis(
            AnalysisConfig(input_path=str(tmp_path), output_path=str(tmp_path))
        )
        with pytest.raises(ValueError, match="No field data loaded"):
            analysis.analyze_portfolio()

    def test_portfolio_basic(self, tmp_path):
        analysis = SodirAnalysis(
            AnalysisConfig(input_path=str(tmp_path), output_path=str(tmp_path))
        )
        analysis.data = {
            "fields": pd.DataFrame(
                {
                    "field_name": ["Troll", "Ekofisk"],
                    "recoverable_oil_mmbbl": [1000.0, 500.0],
                    "recoverable_gas_bcf": [5000.0, 2000.0],
                    "water_depth_m": [300.0, 70.0],
                    "recovery_factor": [0.5, 0.45],
                    "status": ["PRODUCING", "PRODUCING"],
                }
            )
        }
        result = analysis.analyze_portfolio()
        assert result["total_fields"] == 2
        assert result["total_recoverable_oil"] == 1500.0


# ---------------------------------------------------------------------------
# SodirAnalysis - analyze_temporal_trends
# ---------------------------------------------------------------------------


class TestSodirAnalysisTemporal:
    def test_no_data_raises(self, tmp_path):
        analysis = SodirAnalysis(
            AnalysisConfig(input_path=str(tmp_path), output_path=str(tmp_path))
        )
        with pytest.raises(ValueError, match="No data loaded"):
            analysis.analyze_temporal_trends()

    def test_with_production(self, tmp_path):
        analysis = SodirAnalysis(
            AnalysisConfig(input_path=str(tmp_path), output_path=str(tmp_path))
        )
        analysis.data = {
            "production": pd.DataFrame(
                {
                    "year": [2020, 2021, 2022],
                    "oil_production_mmbbl": [100, 95, 90],
                    "gas_production_bcf": [200, 210, 220],
                }
            )
        }
        result = analysis.analyze_temporal_trends()
        assert "production_trends" in result

    def test_with_discovery_timeline(self, tmp_path):
        analysis = SodirAnalysis(
            AnalysisConfig(input_path=str(tmp_path), output_path=str(tmp_path))
        )
        analysis.data = {
            "fields": pd.DataFrame(
                {
                    "discovery_year": [1990, 1990, 2000, 2010],
                }
            )
        }
        result = analysis.analyze_temporal_trends()
        assert result["discovery_timeline"][1990] == 2


# ---------------------------------------------------------------------------
# FieldAnalyzer
# ---------------------------------------------------------------------------


class TestFieldAnalyzer:
    def test_analyze_characteristics(self):
        analyzer = FieldAnalyzer()
        field_data = pd.DataFrame(
            {
                "water_depth_m": [300.0],
                "discovery_year": [1979],
                "status": ["PRODUCING"],
            }
        )
        chars = analyzer._analyze_characteristics(field_data)
        assert chars["water_depth_m"] == 300.0

    def test_analyze_drilling_empty(self):
        analyzer = FieldAnalyzer()
        result = analyzer._analyze_drilling(pd.DataFrame())
        assert result == {}

    def test_analyze_drilling_with_data(self):
        analyzer = FieldAnalyzer()
        wb = pd.DataFrame({"depth_m": [3000, 4000], "drilling_days": [30, 40]})
        result = analyzer._analyze_drilling(wb)
        assert result["total_wells"] == 2

    def test_analyze_production_empty(self):
        analyzer = FieldAnalyzer()
        result = analyzer._analyze_production(pd.DataFrame())
        assert result == {}

    def test_analyze_production_with_data(self):
        analyzer = FieldAnalyzer()
        prod = pd.DataFrame(
            {
                "year": [2020, 2021],
                "oil_production_mmbbl": [100, 95],
                "gas_production_bcf": [200, 210],
            }
        )
        result = analyzer._analyze_production(prod)
        assert result["peak_oil_rate"] == 100
        assert result["years_producing"] == 2


# ---------------------------------------------------------------------------
# PortfolioAnalyzer
# ---------------------------------------------------------------------------


def _portfolio_fields():
    return pd.DataFrame(
        {
            "field_name": ["F1", "F2", "F3"],
            "recoverable_oil_mmbbl": [100, 500, 1000],
            "recoverable_gas_bcf": [200, 1000, 3000],
            "water_depth_m": [80, 600, 1800],
            "recovery_factor": [0.2, 0.45, 0.6],
            "status": ["PRODUCING", "IDLE", "PRODUCING"],
            "production_start": [1990, 2000, 2010],
        }
    )


class TestPortfolioAnalyzer:
    def test_portfolio_metrics(self):
        analyzer = PortfolioAnalyzer()
        result = analyzer._calculate_portfolio_metrics(_portfolio_fields())
        assert result["total_fields"] == 3

    def test_concentration(self):
        analyzer = PortfolioAnalyzer()
        result = analyzer._calculate_concentration(_portfolio_fields())
        assert 0 < result <= 1

    def test_concentration_zero_total(self):
        analyzer = PortfolioAnalyzer()
        df = pd.DataFrame(
            {
                "recoverable_oil_mmbbl": [0, 0],
                "recoverable_gas_bcf": [0, 0],
            }
        )
        assert analyzer._calculate_concentration(df) == 0

    def test_risk_profile_deep_water(self):
        analyzer = PortfolioAnalyzer()
        fields = pd.DataFrame(
            {
                "water_depth_m": [1500, 2000],
                "production_start": [2010, 2015],
            }
        )
        risk = analyzer._assess_risk_profile(fields)
        assert risk["water_depth_risk"] == "high"

    def test_maturity_risk_unknown(self):
        analyzer = PortfolioAnalyzer()
        fields = pd.DataFrame({"water_depth_m": [300]})
        risk = analyzer._assess_maturity_risk(fields)
        assert risk == "unknown"

    def test_opportunities_low_recovery(self):
        analyzer = PortfolioAnalyzer()
        opps = analyzer._identify_opportunities(_portfolio_fields())
        assert any("EOR" in o for o in opps)

    def test_opportunities_idle_fields(self):
        analyzer = PortfolioAnalyzer()
        opps = analyzer._identify_opportunities(_portfolio_fields())
        assert any("Reactivation" in o for o in opps)


# ---------------------------------------------------------------------------
# TemporalAnalyzer
# ---------------------------------------------------------------------------


class TestTemporalAnalyzer:
    def test_production_trends_empty(self):
        analyzer = TemporalAnalyzer()
        result = analyzer._analyze_production_trends(None)
        assert result == {}

    def test_production_trends_declining(self):
        analyzer = TemporalAnalyzer()
        prod = pd.DataFrame(
            {
                "year": [2020, 2021, 2022, 2023],
                "oil_production_mmbbl": [100, 90, 80, 70],
                "gas_production_bcf": [200, 210, 220, 230],
            }
        )
        result = analyzer._analyze_production_trends(prod)
        assert result["oil_trend"] == "declining"
        assert result["gas_trend"] == "stable"

    def test_discovery_trends(self):
        analyzer = TemporalAnalyzer()
        fields = pd.DataFrame({"discovery_year": [1975, 1983, 1995, 2005]})
        result = analyzer._analyze_discovery_trends(fields)
        assert result["discoveries_by_decade"][1970] == 1
        assert result["discoveries_by_decade"][1980] == 1

    def test_discovery_trends_empty(self):
        analyzer = TemporalAnalyzer()
        result = analyzer._analyze_discovery_trends(None)
        assert result == {}

    def test_activity_trends(self):
        analyzer = TemporalAnalyzer()
        wb = pd.DataFrame({"completion_year": [2010, 2010, 2011, 2012, 2012, 2012]})
        result = analyzer._analyze_activity_trends(wb)
        assert result["peak_drilling_year"] == 2012
        assert result["peak_wells_count"] == 3

    def test_activity_trends_missing_col(self):
        analyzer = TemporalAnalyzer()
        result = analyzer._analyze_activity_trends(pd.DataFrame({"other": [1]}))
        assert result == {}


# ---------------------------------------------------------------------------
# MetricsCalculator
# ---------------------------------------------------------------------------


class TestMetricsCalculator:
    def test_field_metrics_recovery(self):
        calc = MetricsCalculator()
        field = pd.DataFrame(
            {
                "recovery_factor": [0.5],
                "production_start": [2000],
                "recoverable_oil_mmbbl": [500],
            }
        )
        result = calc.calculate_field_metrics(field, pd.DataFrame(), pd.DataFrame())
        assert result["recovery_efficiency"] == 0.5
        assert result["economic_viability"] == 0.5

    def test_field_metrics_large_reserves(self):
        calc = MetricsCalculator()
        field = pd.DataFrame({"recoverable_oil_mmbbl": [1500]})
        result = calc.calculate_field_metrics(field, pd.DataFrame(), pd.DataFrame())
        assert result["economic_viability"] == 0.9

    def test_field_metrics_small_reserves(self):
        calc = MetricsCalculator()
        field = pd.DataFrame({"recoverable_oil_mmbbl": [50]})
        result = calc.calculate_field_metrics(field, pd.DataFrame(), pd.DataFrame())
        assert result["economic_viability"] == 0.3

    def test_drilling_efficiency_metric(self):
        calc = MetricsCalculator()
        wb = pd.DataFrame({"drilling_days": [30, 60]})
        result = calc.calculate_field_metrics(pd.DataFrame(), wb, pd.DataFrame())
        # efficiency = 1 / (avg_days/30)
        assert "drilling_efficiency" in result

    def test_portfolio_metrics(self):
        calc = MetricsCalculator()
        fields = pd.DataFrame(
            {
                "recoverable_oil_mmbbl": [100, 200],
                "recoverable_gas_bcf": [300, 600],
                "water_depth_m": [100, 500],
                "recovery_factor": [0.3, 0.5],
            }
        )
        result = calc.calculate_portfolio_metrics(fields)
        assert result["total_oil_reserves_mmbbl"] == 300
        assert result["total_gas_reserves_bcf"] == 900

    def test_gini_coefficient_equal(self):
        calc = MetricsCalculator()
        values = pd.Series([100, 100, 100])
        gini = calc._calculate_gini_coefficient(values)
        assert gini == pytest.approx(0.0, abs=0.01)

    def test_gini_coefficient_unequal(self):
        calc = MetricsCalculator()
        values = pd.Series([0, 0, 0, 1000])
        gini = calc._calculate_gini_coefficient(values)
        assert gini > 0.5

    def test_gini_coefficient_empty(self):
        calc = MetricsCalculator()
        assert calc._calculate_gini_coefficient(pd.Series(dtype=float)) == 0


# ---------------------------------------------------------------------------
# SodirAnalysis - _calculate_reserves
# ---------------------------------------------------------------------------


class TestCalculateReserves:
    def test_without_production(self, tmp_path):
        analysis = SodirAnalysis(
            AnalysisConfig(input_path=str(tmp_path), output_path=str(tmp_path))
        )
        analysis.data = {"fields": _make_field_data()}
        result = analysis.analyze_field("Troll")
        assert result.reserves["original_oil_mmbbl"] == 1000.0
        assert result.reserves["original_gas_bcf"] == 5000.0
        assert "cumulative_oil_mmbbl" not in result.reserves

    def test_with_production(self, tmp_path):
        analysis = SodirAnalysis(
            AnalysisConfig(input_path=str(tmp_path), output_path=str(tmp_path))
        )
        fields = _make_field_data()
        production = pd.DataFrame(
            {
                "field_name": ["Troll", "Troll", "Troll"],
                "oil_production_mmbbl": [100.0, 150.0, 120.0],
                "gas_production_bcf": [500.0, 600.0, 400.0],
                "year": [2020, 2021, 2022],
            }
        )
        analysis.data = {"fields": fields, "production": production}
        result = analysis.analyze_field("Troll")
        assert result.reserves["cumulative_oil_mmbbl"] == 370.0
        assert result.reserves["cumulative_gas_bcf"] == 1500.0
        assert result.reserves["remaining_oil_mmbbl"] == pytest.approx(630.0)
        assert result.reserves["depletion_percentage"] == pytest.approx(37.0)


# ---------------------------------------------------------------------------
# SodirAnalysis - _calculate_economics
# ---------------------------------------------------------------------------


class TestCalculateEconomics:
    def test_economics_mid_price(self, tmp_path):
        analysis = SodirAnalysis(
            AnalysisConfig(
                input_path=str(tmp_path),
                output_path=str(tmp_path),
                include_npv=True,
                oil_price_scenario="mid",
            )
        )
        analysis.data = {"fields": _make_field_data()}
        result = analysis.analyze_field("Troll")
        assert result.economics is not None
        assert result.economics["oil_price_assumption"] == 80

    def test_economics_low_price(self, tmp_path):
        analysis = SodirAnalysis(
            AnalysisConfig(
                input_path=str(tmp_path),
                output_path=str(tmp_path),
                include_npv=True,
                oil_price_scenario="low",
            )
        )
        analysis.data = {"fields": _make_field_data()}
        result = analysis.analyze_field("Troll")
        assert result.economics["oil_price_assumption"] == 60

    def test_economics_high_price(self, tmp_path):
        analysis = SodirAnalysis(
            AnalysisConfig(
                input_path=str(tmp_path),
                output_path=str(tmp_path),
                include_npv=True,
                oil_price_scenario="high",
            )
        )
        analysis.data = {"fields": _make_field_data()}
        result = analysis.analyze_field("Troll")
        assert result.economics["oil_price_assumption"] == 100

    def test_economics_with_production(self, tmp_path):
        analysis = SodirAnalysis(
            AnalysisConfig(
                input_path=str(tmp_path),
                output_path=str(tmp_path),
                include_npv=True,
                oil_price_scenario="mid",
            )
        )
        fields = _make_field_data()
        production = pd.DataFrame(
            {
                "field_name": ["Troll"],
                "oil_production_mmbbl": [200.0],
                "gas_production_bcf": [500.0],
                "year": [2022],
            }
        )
        analysis.data = {"fields": fields, "production": production}
        result = analysis.analyze_field("Troll")
        assert result.economics["future_revenue_mmusd"] == pytest.approx(800.0 * 80)


# ---------------------------------------------------------------------------
# SodirAnalysis - _summarize_results and router
# ---------------------------------------------------------------------------


class TestSummarizeResults:
    def test_empty_results(self, tmp_path):
        analysis = SodirAnalysis(
            AnalysisConfig(input_path=str(tmp_path), output_path=str(tmp_path))
        )
        summary = analysis._summarize_results({})
        assert summary["fields_analyzed"] == 0
        assert "analysis_timestamp" in summary

    def test_with_portfolio(self, tmp_path):
        analysis = SodirAnalysis(
            AnalysisConfig(input_path=str(tmp_path), output_path=str(tmp_path))
        )
        results = {
            "Troll": "field_result",
            "portfolio": {
                "total_fields": 5,
                "total_recoverable_oil": 3000.0,
                "total_recoverable_gas": 12000.0,
            },
        }
        summary = analysis._summarize_results(results)
        assert summary["fields_analyzed"] == 1
        assert summary["portfolio_size"] == 5
        assert summary["total_reserves_boe"] == pytest.approx(3000.0 + 12000.0 / 6)


class TestRouter:
    def test_router_with_fields(self, tmp_path):
        analysis = SodirAnalysis(
            AnalysisConfig(input_path=str(tmp_path), output_path=str(tmp_path))
        )
        analysis.data = {"fields": _make_field_data()}
        cfg = {
            "basename": "sodir",
            "sodir": {},
            "analysis": {"fields": ["Troll"]},
        }
        result = analysis.router(cfg, analysis.data)
        assert result["sodir"]["analysis"]["completed"] is True

    def test_router_with_portfolio(self, tmp_path):
        analysis = SodirAnalysis(
            AnalysisConfig(input_path=str(tmp_path), output_path=str(tmp_path))
        )
        analysis.data = {
            "fields": pd.DataFrame(
                {
                    "field_name": ["F1", "F2"],
                    "recoverable_oil_mmbbl": [100, 200],
                    "recoverable_gas_bcf": [500, 1000],
                    "water_depth_m": [100, 300],
                    "recovery_factor": [0.3, 0.5],
                    "status": ["PRODUCING", "PRODUCING"],
                }
            )
        }
        cfg = {
            "basename": "sodir",
            "sodir": {},
            "analysis": {"portfolio": True},
        }
        result = analysis.router(cfg, analysis.data)
        assert result["sodir"]["analysis"]["completed"] is True

    def test_router_with_temporal(self, tmp_path):
        analysis = SodirAnalysis(
            AnalysisConfig(input_path=str(tmp_path), output_path=str(tmp_path))
        )
        analysis.data = {
            "production": pd.DataFrame(
                {
                    "year": [2020, 2021],
                    "oil_production_mmbbl": [100, 90],
                    "gas_production_bcf": [200, 210],
                }
            )
        }
        cfg = {
            "basename": "sodir",
            "sodir": {},
            "analysis": {"temporal": True},
        }
        result = analysis.router(cfg, analysis.data)
        assert result["sodir"]["analysis"]["completed"] is True


# ---------------------------------------------------------------------------
# SodirAnalysis - maturity_progression
# ---------------------------------------------------------------------------


class TestMaturityProgression:
    def test_with_production_start(self, tmp_path):
        analysis = SodirAnalysis(
            AnalysisConfig(input_path=str(tmp_path), output_path=str(tmp_path))
        )
        current_year = datetime.now().year
        analysis.data = {
            "fields": pd.DataFrame(
                {
                    "discovery_year": [1990, 2000, 2020],
                    "production_start": [
                        current_year - 5,
                        current_year - 20,
                        current_year - 35,
                    ],
                }
            )
        }
        result = analysis.analyze_temporal_trends()
        assert "maturity_progression" in result
        assert result["maturity_progression"]["early"] == 1
        assert result["maturity_progression"]["mature"] == 1
        assert result["maturity_progression"]["late"] == 1


# ---------------------------------------------------------------------------
# SodirAnalysis - from_dict with optional fields
# ---------------------------------------------------------------------------


class TestSodirAnalysisFromDictExtended:
    def test_with_start_and_end_date(self, tmp_path):
        analysis = SodirAnalysis(
            {
                "input_path": str(tmp_path),
                "output_path": str(tmp_path),
                "start_date": "2022-01-01",
                "end_date": "2023-12-31",
            }
        )
        assert analysis.config.start_date == "2022-01-01"
        assert analysis.config.end_date == "2023-12-31"

    def test_load_data_parquet(self, tmp_path):
        # Create a parquet file
        df = pd.DataFrame({"field_name": ["Troll"], "recoverable_oil_mmbbl": [1000]})
        df.to_parquet(tmp_path / "sodir_fields.parquet")
        config = AnalysisConfig(input_path=str(tmp_path), output_path=str(tmp_path))
        loader = SodirDataLoader(config)
        data = loader.load_data(["fields"])
        assert "fields" in data
        assert data["fields"]["field_name"].iloc[0] == "Troll"


# ---------------------------------------------------------------------------
# PortfolioAnalyzer - maturity risk variants
# ---------------------------------------------------------------------------


class TestPortfolioAnalyzerMaturityRisk:
    def test_low_maturity(self):
        analyzer = PortfolioAnalyzer()
        current_year = datetime.now().year
        fields = pd.DataFrame(
            {
                "water_depth_m": [100],
                "production_start": [current_year - 5],
            }
        )
        risk = analyzer._assess_maturity_risk(fields)
        assert risk == "low"

    def test_moderate_maturity(self):
        analyzer = PortfolioAnalyzer()
        current_year = datetime.now().year
        fields = pd.DataFrame(
            {
                "water_depth_m": [100],
                "production_start": [current_year - 20],
            }
        )
        risk = analyzer._assess_maturity_risk(fields)
        assert risk == "moderate"

    def test_high_maturity(self):
        analyzer = PortfolioAnalyzer()
        current_year = datetime.now().year
        fields = pd.DataFrame(
            {
                "water_depth_m": [100],
                "production_start": [current_year - 40],
            }
        )
        risk = analyzer._assess_maturity_risk(fields)
        assert risk == "high"
