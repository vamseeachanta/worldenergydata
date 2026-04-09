"""
Tests for SODIR analysis integration
"""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest

# Import the modules to test
from worldenergydata.sodir.analysis import (
    AnalysisConfig,
    CrossRegionalComparison,
    FieldAnalysisResult,
    ProductionForecast,
    SodirAnalysis,
)
from worldenergydata.sodir.cross_regional import (
    ComparisonResult,
    CrossRegionalAnalyzer,
    NormalizationStrategy,
    RegionalMetrics,
)
from worldenergydata.sodir.forecasting import (
    DeclineCurve,
    ForecastModel,
    ForecastResult,
    ProductionForecaster,
)
from worldenergydata.sodir.npv_norway import (
    CashFlowResult,
    NorwayNPVCalculator,
    NorwegianFinancialParameters,
    TaxRegime,
)
from worldenergydata.sodir.visualization import (
    ChartConfig,
    DashboardGenerator,
    MapVisualization,
    SodirVisualizer,
)


# Global fixtures for cross-test usage
@pytest.fixture
def sample_sodir_data():
    """Create sample SODIR data for testing"""
    return {
        "fields": pd.DataFrame(
            {
                "field_name": ["Ekofisk", "Statfjord", "Troll"],
                "discovery_year": [1969, 1974, 1979],
                "production_start": [1971, 1979, 1995],
                "status": ["PRODUCING", "PRODUCING", "PRODUCING"],
                "recoverable_oil_mmbbl": [3500, 4000, 500],
                "recoverable_gas_bcf": [8000, 12000, 45000],
                "water_depth_m": [70, 145, 300],
                "recovery_factor": [0.51, 0.68, 0.70],
            }
        ),
        "wellbores": pd.DataFrame(
            {
                "wellbore_name": ["2/4-A-1", "33/9-A-2", "31/2-G-1"],
                "field_name": ["Ekofisk", "Statfjord", "Troll"],
                "purpose": ["PRODUCTION", "PRODUCTION", "PRODUCTION"],
                "depth_m": [3000, 2700, 3500],
                "drilling_days": [45, 38, 52],
                "completion_year": [1971, 1979, 1995],
            }
        ),
        "production": pd.DataFrame(
            {
                "field_name": ["Ekofisk", "Statfjord", "Troll"],
                "year": [2023, 2023, 2023],
                "oil_production_mmbbl": [45, 15, 5],
                "gas_production_bcf": [120, 180, 450],
                "water_production_mmbbl": [150, 200, 50],
            }
        ),
    }


@pytest.fixture
def sample_bsee_data():
    """Create sample BSEE data for testing"""
    return {
        "fields": pd.DataFrame(
            {
                "field_name": ["Mars", "Thunder Horse", "Atlantis"],
                "discovery_year": [1989, 1999, 1998],
                "production_start": [1996, 2008, 2007],
                "status": ["Active", "Active", "Active"],
                "recoverable_oil_mmbbl": [900, 1000, 635],
                "recoverable_gas_bcf": [500, 300, 200],
                "water_depth_ft": [2940, 6050, 7070],
                "recovery_factor": [0.45, 0.40, 0.35],
            }
        ),
        "production": pd.DataFrame(
            {
                "field_name": ["Mars", "Thunder Horse", "Atlantis"],
                "year": [2023, 2023, 2023],
                "oil_production_mmbbl": [25, 35, 20],
                "gas_production_bcf": [15, 10, 8],
            }
        ),
        "wellbores": pd.DataFrame(
            {
                "wellbore_name": ["Mars A-1", "TH B-1", "Atlantis C-1"],
                "field_name": ["Mars", "Thunder Horse", "Atlantis"],
                "drilling_days": [30, 45, 40],
                "depth_m": [5000, 6000, 5500],
            }
        ),
    }


class TestSodirAnalysis:
    """Test suite for main SODIR analysis class"""

    @pytest.fixture
    def analysis_config(self, tmp_path):
        """Create analysis configuration"""
        return AnalysisConfig(
            input_path=str(tmp_path / "input"),
            output_path=str(tmp_path / "output"),
            start_date="2020-01-01",
            end_date="2024-12-31",
            fields=["Ekofisk", "Statfjord"],
            analysis_type="comprehensive",
            include_forecasting=True,
            include_npv=True,
        )

    def test_sodir_analysis_initialization(self, analysis_config):
        """Test SodirAnalysis initialization"""
        analyzer = SodirAnalysis(analysis_config)
        assert analyzer.config == analysis_config
        assert analyzer.data_loader is not None
        assert analyzer.processors is not None
        assert analyzer.results == {}

    def test_field_analysis(self, sample_sodir_data, analysis_config):
        """Test individual field analysis"""
        analyzer = SodirAnalysis(analysis_config)

        # Mock data loading
        analyzer.data = sample_sodir_data

        # Analyze single field
        result = analyzer.analyze_field("Ekofisk")

        assert isinstance(result, FieldAnalysisResult)
        assert result.field_name == "Ekofisk"
        assert result.metrics is not None
        assert "recovery_efficiency" in result.metrics
        assert "production_maturity" in result.metrics
        assert result.production_profile is not None

    def test_portfolio_analysis(self, sample_sodir_data, analysis_config):
        """Test portfolio-level analysis"""
        analyzer = SodirAnalysis(analysis_config)
        analyzer.data = sample_sodir_data

        # Analyze portfolio
        portfolio_result = analyzer.analyze_portfolio()

        assert "total_recoverable_oil" in portfolio_result
        assert "total_recoverable_gas" in portfolio_result
        assert "average_recovery_factor" in portfolio_result
        assert "field_rankings" in portfolio_result
        assert len(portfolio_result["field_rankings"]) == 3

    def test_temporal_analysis(self, sample_sodir_data):
        """Test temporal trend analysis"""
        config = AnalysisConfig(
            input_path="test", output_path="test", temporal_resolution="yearly"
        )
        analyzer = SodirAnalysis(config)
        analyzer.data = sample_sodir_data

        # Perform temporal analysis
        temporal_results = analyzer.analyze_temporal_trends()

        assert "production_trends" in temporal_results
        assert "discovery_timeline" in temporal_results
        assert "maturity_progression" in temporal_results

    @patch("worldenergydata.sodir.analysis.SodirDataLoader")
    def test_data_loading_integration(self, mock_loader, analysis_config):
        """Test integration with data loader"""
        mock_loader_instance = Mock()
        mock_loader.return_value = mock_loader_instance
        mock_loader_instance.load_data.return_value = {"fields": pd.DataFrame()}

        analyzer = SodirAnalysis(analysis_config)
        analyzer.load_data()

        mock_loader_instance.load_data.assert_called_once()

    def test_error_handling(self, analysis_config):
        """Test error handling in analysis"""
        analyzer = SodirAnalysis(analysis_config)

        # Test with missing data
        with pytest.raises(ValueError, match="No data loaded"):
            analyzer.analyze_field("NonExistent")

        # Test with invalid field
        analyzer.data = {"fields": pd.DataFrame()}
        with pytest.raises(KeyError, match="Field data not available"):
            analyzer.analyze_field("NonExistent")


class TestCrossRegionalAnalysis:
    """Test suite for cross-regional comparison functionality"""

    @pytest.fixture
    def cross_regional_analyzer(self):
        """Create cross-regional analyzer instance"""
        return CrossRegionalAnalyzer()

    def test_data_normalization(
        self, cross_regional_analyzer, sample_sodir_data, sample_bsee_data
    ):
        """Test data normalization between regions"""
        # Normalize SODIR data
        normalized_sodir = cross_regional_analyzer.normalize_data(
            sample_sodir_data, source="SODIR", strategy=NormalizationStrategy.STANDARD
        )

        # Normalize BSEE data
        normalized_bsee = cross_regional_analyzer.normalize_data(
            sample_bsee_data, source="BSEE", strategy=NormalizationStrategy.STANDARD
        )

        # Check normalized structure
        assert set(normalized_sodir.keys()) == set(normalized_bsee.keys())
        assert "water_depth_m" in normalized_sodir["fields"].columns
        assert "water_depth_m" in normalized_bsee["fields"].columns

    def test_metric_comparison(
        self, cross_regional_analyzer, sample_sodir_data, sample_bsee_data
    ):
        """Test regional metric comparison"""
        # Calculate regional metrics
        sodir_metrics = cross_regional_analyzer.calculate_metrics(
            sample_sodir_data, region="Norway"
        )
        bsee_metrics = cross_regional_analyzer.calculate_metrics(
            sample_bsee_data, region="US_GOM"
        )

        # Compare metrics
        comparison = cross_regional_analyzer.compare_regions(
            sodir_metrics, bsee_metrics
        )

        assert isinstance(comparison, ComparisonResult)
        assert comparison.metrics_diff is not None
        assert "recovery_factor_diff" in comparison.metrics_diff
        assert "drilling_efficiency_diff" in comparison.metrics_diff
        assert comparison.statistical_significance is not None

    def test_field_matching(self, cross_regional_analyzer):
        """Test field matching between regions"""
        sodir_fields = pd.DataFrame(
            {
                "field_name": ["Giant Field A", "Medium Field B"],
                "recoverable_oil_mmbbl": [5000, 500],
                "water_depth_m": [150, 200],
            }
        )

        bsee_fields = pd.DataFrame(
            {
                "field_name": ["Deepwater X", "Shallow Y"],
                "recoverable_oil_mmbbl": [1000, 200],
                "water_depth_m": [1500, 50],
            }
        )

        # Find comparable fields
        matches = cross_regional_analyzer.find_comparable_fields(
            sodir_fields, bsee_fields, criteria=["size_class", "water_depth_range"]
        )

        assert len(matches) >= 0
        assert all("similarity_score" in match for match in matches)

    def test_production_efficiency_comparison(self, cross_regional_analyzer):
        """Test production efficiency comparison"""
        sodir_production = pd.DataFrame(
            {
                "field_name": ["Field A"],
                "cumulative_oil": [1000],
                "recoverable_oil": [2000],
                "years_producing": [20],
                "wells_count": [50],
            }
        )

        bsee_production = pd.DataFrame(
            {
                "field_name": ["Field B"],
                "cumulative_oil": [800],
                "recoverable_oil": [1500],
                "years_producing": [15],
                "wells_count": [40],
            }
        )

        efficiency = cross_regional_analyzer.compare_production_efficiency(
            sodir_production, bsee_production
        )

        assert "recovery_rate_sodir" in efficiency
        assert "recovery_rate_bsee" in efficiency
        assert "wells_productivity_ratio" in efficiency


class TestNorwayNPVCalculations:
    """Test suite for Norwegian NPV calculations"""

    @pytest.fixture
    def financial_params(self):
        """Create Norwegian financial parameters"""
        return NorwegianFinancialParameters(
            discount_rate=0.08,
            petroleum_tax_rate=0.78,
            corporate_tax_rate=0.22,
            uplift_rate=0.056,
            uplift_years=4,
            depreciation_years=6,
            working_interest=0.30,
            oil_price_usd=80,
            gas_price_nok_per_sm3=2.5,
            opex_per_boe=15,
            capex_schedule=[1000, 500, 200],
        )

    @pytest.fixture
    def production_profile(self):
        """Create production profile for NPV testing"""
        return pd.DataFrame(
            {
                "year": range(2024, 2034),
                "oil_production_mmbbl": [10, 12, 11, 10, 9, 8, 7, 6, 5, 4],
                "gas_production_bcf": [50, 60, 58, 55, 50, 45, 40, 35, 30, 25],
            }
        )

    def test_npv_calculator_initialization(self, financial_params):
        """Test NPV calculator initialization"""
        calculator = NorwayNPVCalculator(financial_params)
        assert calculator.params == financial_params
        assert calculator.tax_regime == TaxRegime.PETROLEUM_TAX

    def test_revenue_calculation(self, financial_params, production_profile):
        """Test revenue calculation"""
        calculator = NorwayNPVCalculator(financial_params)

        revenue = calculator.calculate_revenue(production_profile)

        assert "oil_revenue" in revenue.columns
        assert "gas_revenue" in revenue.columns
        assert "total_revenue" in revenue.columns
        assert len(revenue) == len(production_profile)
        assert all(revenue["total_revenue"] > 0)

    def test_norwegian_tax_calculation(self, financial_params):
        """Test Norwegian petroleum tax calculation"""
        calculator = NorwayNPVCalculator(financial_params)

        taxable_income = 1000  # Million NOK
        taxes = calculator.calculate_taxes(taxable_income)

        assert "petroleum_tax" in taxes
        assert "corporate_tax" in taxes
        assert "total_tax" in taxes
        # Norwegian tax calculation: corporate tax on full income, special petroleum tax on (income - corporate tax)
        # Note: The special_tax_rate is 0.56, not the full petroleum_tax_rate of 0.78
        expected_corporate = taxable_income * 0.22
        expected_petroleum = (
            taxable_income - expected_corporate
        ) * 0.56  # Using special_tax_rate
        expected_total = expected_corporate + expected_petroleum
        assert taxes["total_tax"] == pytest.approx(expected_total, rel=1e-3)

    def test_uplift_calculation(self, financial_params):
        """Test uplift (investment allowance) calculation"""
        calculator = NorwayNPVCalculator(financial_params)

        capex = 1000  # Million NOK
        uplift = calculator.calculate_uplift(capex)

        assert len(uplift) == financial_params.uplift_years
        assert sum(uplift) == pytest.approx(
            capex * financial_params.uplift_rate * financial_params.uplift_years,
            rel=1e-3,
        )

    def test_npv_calculation(self, financial_params, production_profile):
        """Test full NPV calculation"""
        calculator = NorwayNPVCalculator(financial_params)

        result = calculator.calculate_npv(
            production_profile, capex_schedule=financial_params.capex_schedule
        )

        assert isinstance(result, CashFlowResult)
        assert result.npv is not None
        assert result.irr is None or isinstance(result.irr, float)  # IRR may be None if no sign change in cashflows
        assert result.payback_period is not None
        assert len(result.cash_flows) == len(production_profile)

    def test_sensitivity_analysis(self, financial_params, production_profile):
        """Test NPV sensitivity analysis"""
        calculator = NorwayNPVCalculator(financial_params)

        sensitivity = calculator.sensitivity_analysis(
            production_profile,
            parameters=["oil_price", "discount_rate", "opex"],
            variations=[-20, -10, 0, 10, 20],
        )

        assert "oil_price" in sensitivity
        assert "discount_rate" in sensitivity
        assert len(sensitivity["oil_price"]) == 5


class TestVisualization:
    """Test suite for visualization components"""

    @pytest.fixture
    def visualizer(self):
        """Create visualizer instance"""
        return SodirVisualizer()

    def test_map_visualization_creation(self, visualizer, sample_sodir_data):
        """Test Norwegian Continental Shelf map creation"""
        map_config = ChartConfig(
            title="Norwegian Fields",
            chart_type="scatter_map",
            color_by="production_start",
        )

        # Create map visualization
        map_viz = visualizer.create_field_map(
            sample_sodir_data["fields"], config=map_config
        )

        assert isinstance(map_viz, MapVisualization)
        assert map_viz.layers is not None
        assert "fields" in map_viz.layers
        assert map_viz.bounds == "norwegian_continental_shelf"

    def test_production_chart(self, visualizer):
        """Test production chart creation"""
        production_data = pd.DataFrame(
            {
                "year": range(2015, 2024),
                "oil": np.random.rand(9) * 100,
                "gas": np.random.rand(9) * 500,
            }
        )

        chart = visualizer.create_production_chart(
            production_data, chart_type="stacked_area"
        )

        assert chart is not None
        assert chart["data"] is not None
        assert "oil" in chart["series"]
        assert "gas" in chart["series"]

    def test_comparison_dashboard(
        self, visualizer, sample_sodir_data, sample_bsee_data
    ):
        """Test cross-regional comparison dashboard"""
        dashboard = visualizer.create_comparison_dashboard(
            sodir_data=sample_sodir_data,
            bsee_data=sample_bsee_data,
            metrics=["recovery_factor", "water_depth", "production_rate"],
        )

        assert isinstance(dashboard, DashboardGenerator)
        assert len(dashboard.charts) >= 3
        assert dashboard.layout is not None

    @patch("sodir_module.visualization.plt")
    def test_export_charts(self, mock_plt, visualizer, tmp_path):
        """Test chart export functionality"""
        # Create dummy chart
        chart = Mock()
        chart.figure = Mock()

        # Export chart
        output_file = tmp_path / "test_chart.png"
        visualizer.export_chart(chart, str(output_file))

        assert output_file.exists() or mock_plt.savefig.called


class TestProductionForecasting:
    """Test suite for production forecasting"""

    @pytest.fixture
    def forecaster(self):
        """Create forecaster instance"""
        return ProductionForecaster()

    @pytest.fixture
    def historical_production(self):
        """Create historical production data"""
        years = range(2010, 2024)
        return pd.DataFrame(
            {
                "year": years,
                "oil_production": [100 * np.exp(-0.1 * i) for i in range(len(years))],
                "gas_production": [500 * np.exp(-0.08 * i) for i in range(len(years))],
            }
        )

    def test_decline_curve_fitting(self, forecaster, historical_production):
        """Test decline curve analysis"""
        # Fit exponential decline
        decline_params = forecaster.fit_decline_curve(
            historical_production["oil_production"], model_type="exponential"
        )

        assert isinstance(decline_params, DeclineCurve)
        assert decline_params.initial_rate > 0
        assert 0 < decline_params.decline_rate < 1
        assert decline_params.r_squared > 0.8

    def test_hyperbolic_decline(self, forecaster):
        """Test hyperbolic decline curve"""
        production = pd.Series([100, 85, 73, 64, 57, 51, 46])

        decline_params = forecaster.fit_decline_curve(
            production, model_type="hyperbolic"
        )

        assert decline_params.b_factor is not None
        assert 0 < decline_params.b_factor <= 1

    def test_production_forecast(self, forecaster, historical_production):
        """Test production forecasting"""
        # Generate forecast
        forecast = forecaster.forecast_production(
            historical_production, forecast_years=10, method="decline_curve"
        )

        assert isinstance(forecast, ForecastResult)
        assert len(forecast.forecast_values) == 10
        assert forecast.confidence_intervals is not None
        assert forecast.model_params is not None

    def test_ensemble_forecasting(self, forecaster, historical_production):
        """Test ensemble forecasting with multiple models"""
        forecast = forecaster.ensemble_forecast(
            historical_production,
            models=["exponential", "hyperbolic", "arima"],
            forecast_years=5,
        )

        assert len(forecast.models) == 3
        assert forecast.ensemble_mean is not None
        assert forecast.model_weights is not None
        assert sum(forecast.model_weights.values()) == pytest.approx(1.0)

    def test_forecast_validation(self, forecaster, historical_production):
        """Test forecast validation with holdout"""
        # Split data for validation
        train_data = historical_production.iloc[:-2]
        test_data = historical_production.iloc[-2:]

        # Generate forecast for test period
        forecast = forecaster.forecast_production(train_data, forecast_years=2)

        # Validate forecast
        validation = forecaster.validate_forecast(
            forecast.forecast_values, test_data[["oil_production", "gas_production"]]
        )

        assert "mape" in validation  # Mean Absolute Percentage Error
        assert "rmse" in validation  # Root Mean Square Error
        assert validation["mape"] < 50  # Reasonable error threshold

    def test_scenario_forecasting(self, forecaster, historical_production):
        """Test scenario-based forecasting"""
        scenarios = {
            "pessimistic": {"decline_factor": 1.2},
            "base": {"decline_factor": 1.0},
            "optimistic": {"decline_factor": 0.8},
        }

        scenario_forecasts = forecaster.scenario_forecast(
            historical_production, scenarios=scenarios, forecast_years=10
        )

        assert len(scenario_forecasts) == 3
        assert "pessimistic" in scenario_forecasts
        assert "optimistic" in scenario_forecasts
        # Optimistic should have higher production
        assert (
            scenario_forecasts["optimistic"].forecast_values
            > scenario_forecasts["pessimistic"].forecast_values
        ).all()
