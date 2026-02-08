"""
SODIR analysis module for comprehensive field and portfolio analysis.

This module provides analysis capabilities for SODIR data,
including field-level metrics, portfolio analysis, and temporal trends.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class AnalysisConfig:
    """Configuration for SODIR analysis"""

    input_path: str
    output_path: str
    start_date: str = "2020-01-01"
    end_date: str = "2024-12-31"
    fields: List[str] = field(default_factory=list)
    analysis_type: str = "comprehensive"  # comprehensive, field, portfolio
    include_forecasting: bool = False
    include_npv: bool = False
    temporal_resolution: str = "yearly"  # yearly, quarterly, monthly

    # Processing options
    use_cache: bool = True
    parallel_processing: bool = True
    max_workers: int = 4

    # Analysis parameters
    discount_rate: float = 0.08
    oil_price_scenario: str = "mid"  # low, mid, high

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "input_path": self.input_path,
            "output_path": self.output_path,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "fields": self.fields,
            "analysis_type": self.analysis_type,
            "include_forecasting": self.include_forecasting,
            "include_npv": self.include_npv,
            "temporal_resolution": self.temporal_resolution,
            "use_cache": self.use_cache,
            "parallel_processing": self.parallel_processing,
            "max_workers": self.max_workers,
            "discount_rate": self.discount_rate,
            "oil_price_scenario": self.oil_price_scenario,
        }


@dataclass
class FieldAnalysisResult:
    """Results from individual field analysis"""

    field_name: str
    metrics: Dict[str, float]
    production_profile: Optional[pd.DataFrame] = None
    reserves: Optional[Dict[str, float]] = None
    economics: Optional[Dict[str, float]] = None
    risk_factors: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def summary(self) -> Dict[str, Any]:
        """Get summary of analysis results"""
        return {
            "field_name": self.field_name,
            "key_metrics": {
                "recovery_efficiency": self.metrics.get("recovery_efficiency", 0),
                "production_maturity": self.metrics.get("production_maturity", 0),
                "economic_viability": self.metrics.get("economic_viability", 0),
            },
            "reserves_status": self.reserves,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class CrossRegionalComparison:
    """Results from cross-regional comparison"""

    sodir_metrics: Dict[str, Any]
    bsee_metrics: Dict[str, Any]
    comparison_results: Dict[str, Any]
    statistical_tests: Optional[Dict[str, Any]] = None
    visualizations: Optional[List[Any]] = None


@dataclass
class ProductionForecast:
    """Production forecast results"""

    field_name: str
    forecast_period: Tuple[str, str]
    oil_forecast: pd.DataFrame
    gas_forecast: pd.DataFrame
    confidence_intervals: Dict[str, pd.DataFrame]
    model_parameters: Dict[str, Any]


class SodirDataLoader:
    """Data loader for SODIR analysis"""

    def __init__(self, config: AnalysisConfig):
        self.config = config
        self.data_path = Path(config.input_path)

    def load_data(
        self, data_types: Optional[List[str]] = None
    ) -> Dict[str, pd.DataFrame]:
        """Load SODIR data for analysis"""
        if data_types is None:
            data_types = ["fields", "wellbores", "production", "discoveries"]

        data = {}
        for data_type in data_types:
            file_path = self.data_path / f"sodir_{data_type}.parquet"
            if file_path.exists():
                data[data_type] = pd.read_parquet(file_path)
            else:
                # Try CSV as fallback
                csv_path = self.data_path / f"sodir_{data_type}.csv"
                if csv_path.exists():
                    data[data_type] = pd.read_csv(csv_path)

        return data


class SodirAnalysis:
    """Main SODIR analysis orchestrator"""

    def __init__(self, config: Union[AnalysisConfig, Dict[str, Any]]):
        """
        Initialize SODIR analysis component.

        Args:
            config: Analysis configuration (AnalysisConfig object or dict)
        """
        # Convert dict to AnalysisConfig if necessary
        if isinstance(config, dict):
            # Provide defaults for missing required fields
            config_dict = {
                "input_path": config.get(
                    "input_path", config.get("output_dir", "./data")
                ),
                "output_path": config.get(
                    "output_path", config.get("output_dir", "./output")
                ),
                "analysis_type": config.get("analysis_type", "comprehensive"),
            }
            # Add optional fields if present
            if "start_date" in config:
                config_dict["start_date"] = config["start_date"]
            if "end_date" in config:
                config_dict["end_date"] = config["end_date"]
            config = AnalysisConfig(**config_dict)

        self.config = config
        self.data_loader = SodirDataLoader(config)
        self.data = {}
        self.results = {}
        self.processors = self._initialize_processors()

        logger.info(f"Initialized SodirAnalysis with config: {config.analysis_type}")

    def _initialize_processors(self) -> Dict[str, Any]:
        """Initialize data processors"""
        return {
            "field_analyzer": FieldAnalyzer(),
            "portfolio_analyzer": PortfolioAnalyzer(),
            "temporal_analyzer": TemporalAnalyzer(),
            "metrics_calculator": MetricsCalculator(),
        }

    def load_data(self) -> None:
        """Load data using configured data loader"""
        self.data = self.data_loader.load_data()
        logger.info(f"Loaded data: {list(self.data.keys())}")

    def analyze_field(self, field_name: str) -> FieldAnalysisResult:
        """
        Analyze individual field.

        Args:
            field_name: Name of field to analyze

        Returns:
            FieldAnalysisResult with comprehensive metrics
        """
        if not self.data:
            raise ValueError("No data loaded. Call load_data() first.")

        if "fields" not in self.data or self.data["fields"].empty:
            raise KeyError("Field data not available")

        field_data = self.data["fields"][
            self.data["fields"]["field_name"] == field_name
        ]
        if field_data.empty:
            raise KeyError(f"Field not found: {field_name}")

        # Calculate field metrics
        metrics = self.processors["metrics_calculator"].calculate_field_metrics(
            field_data,
            self.data.get("wellbores", pd.DataFrame()),
            self.data.get("production", pd.DataFrame()),
        )

        # Get production profile if available
        production_profile = None
        if "production" in self.data:
            field_production = self.data["production"][
                self.data["production"]["field_name"] == field_name
            ]
            if not field_production.empty:
                production_profile = field_production

        # Calculate reserves
        reserves = self._calculate_reserves(field_data, production_profile)

        # Economic analysis if requested
        economics = None
        if self.config.include_npv:
            economics = self._calculate_economics(field_data, production_profile)

        return FieldAnalysisResult(
            field_name=field_name,
            metrics=metrics,
            production_profile=production_profile,
            reserves=reserves,
            economics=economics,
        )

    def analyze_portfolio(self) -> Dict[str, Any]:
        """
        Analyze entire portfolio of fields.

        Returns:
            Dictionary with portfolio-level metrics and rankings
        """
        if not self.data or "fields" not in self.data:
            raise ValueError("No field data loaded")

        fields_df = self.data["fields"]

        # Calculate portfolio metrics
        portfolio_metrics = {
            "total_fields": len(fields_df),
            "total_recoverable_oil": fields_df["recoverable_oil_mmbbl"].sum(),
            "total_recoverable_gas": fields_df["recoverable_gas_bcf"].sum(),
            "average_recovery_factor": fields_df["recovery_factor"].mean(),
            "average_water_depth": fields_df["water_depth_m"].mean(),
            "fields_by_status": fields_df.groupby("status").size().to_dict(),
        }

        # Rank fields by various criteria
        rankings = {
            "by_oil_reserves": fields_df.nlargest(10, "recoverable_oil_mmbbl")[
                ["field_name", "recoverable_oil_mmbbl"]
            ].to_dict("records"),
            "by_gas_reserves": fields_df.nlargest(10, "recoverable_gas_bcf")[
                ["field_name", "recoverable_gas_bcf"]
            ].to_dict("records"),
            "by_recovery_factor": fields_df.nlargest(10, "recovery_factor")[
                ["field_name", "recovery_factor"]
            ].to_dict("records"),
        }

        portfolio_metrics["field_rankings"] = rankings

        return portfolio_metrics

    def analyze_temporal_trends(self) -> Dict[str, Any]:
        """
        Analyze temporal trends in the data.

        Returns:
            Dictionary with temporal analysis results
        """
        if not self.data:
            raise ValueError("No data loaded")

        results = {}

        # Production trends
        if "production" in self.data:
            production_df = self.data["production"]
            if "year" in production_df.columns:
                results["production_trends"] = {
                    "oil_trend": production_df.groupby("year")["oil_production_mmbbl"]
                    .sum()
                    .to_dict(),
                    "gas_trend": production_df.groupby("year")["gas_production_bcf"]
                    .sum()
                    .to_dict(),
                }

        # Discovery timeline
        if "fields" in self.data and "discovery_year" in self.data["fields"].columns:
            fields_df = self.data["fields"]
            results["discovery_timeline"] = (
                fields_df.groupby("discovery_year").size().to_dict()
            )

        # Maturity progression
        if "fields" in self.data:
            fields_df = self.data["fields"]
            if "production_start" in fields_df.columns:
                current_year = datetime.now().year
                fields_df["years_producing"] = (
                    current_year - fields_df["production_start"]
                )

                results["maturity_progression"] = {
                    "early": len(fields_df[fields_df["years_producing"] < 10]),
                    "mature": len(
                        fields_df[
                            (fields_df["years_producing"] >= 10)
                            & (fields_df["years_producing"] < 30)
                        ]
                    ),
                    "late": len(fields_df[fields_df["years_producing"] >= 30]),
                }

        return results

    def _calculate_reserves(
        self, field_data: pd.DataFrame, production_data: Optional[pd.DataFrame]
    ) -> Dict[str, float]:
        """Calculate remaining reserves"""
        reserves = {
            "original_oil_mmbbl": field_data["recoverable_oil_mmbbl"].iloc[0],
            "original_gas_bcf": field_data["recoverable_gas_bcf"].iloc[0],
        }

        if production_data is not None and not production_data.empty:
            cumulative_oil = production_data["oil_production_mmbbl"].sum()
            cumulative_gas = production_data["gas_production_bcf"].sum()

            reserves["cumulative_oil_mmbbl"] = cumulative_oil
            reserves["cumulative_gas_bcf"] = cumulative_gas
            reserves["remaining_oil_mmbbl"] = (
                reserves["original_oil_mmbbl"] - cumulative_oil
            )
            reserves["remaining_gas_bcf"] = (
                reserves["original_gas_bcf"] - cumulative_gas
            )
            reserves["depletion_percentage"] = (
                cumulative_oil / reserves["original_oil_mmbbl"]
            ) * 100

        return reserves

    def _calculate_economics(
        self, field_data: pd.DataFrame, production_data: Optional[pd.DataFrame]
    ) -> Dict[str, float]:
        """Calculate economic metrics"""
        # Simplified economic calculation
        oil_price = {"low": 60, "mid": 80, "high": 100}[self.config.oil_price_scenario]

        economics = {
            "oil_price_assumption": oil_price,
            "estimated_revenue_mmusd": field_data["recoverable_oil_mmbbl"].iloc[0]
            * oil_price,
        }

        if production_data is not None:
            future_production = (
                field_data["recoverable_oil_mmbbl"].iloc[0]
                - production_data["oil_production_mmbbl"].sum()
            )
            economics["future_revenue_mmusd"] = future_production * oil_price

        return economics

    def router(self, cfg: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route analysis based on configuration (backward compatibility).

        Args:
            cfg: Configuration dictionary
            data: Collected data from SODIR

        Returns:
            Updated configuration with analysis results
        """
        logger.info("Starting SODIR analysis")

        # Store data for analysis
        self.data = data

        analysis_config = cfg.get("analysis", {})
        results = {}

        # Perform configured analyses
        if analysis_config.get("fields"):
            for field in analysis_config["fields"]:
                try:
                    results[field] = self.analyze_field(field)
                    logger.info(f"Completed analysis for field: {field}")
                except Exception as e:
                    logger.error(f"Failed to analyze field {field}: {e}")

        if analysis_config.get("portfolio", False):
            results["portfolio"] = self.analyze_portfolio()
            logger.info("Completed portfolio analysis")

        if analysis_config.get("temporal", False):
            results["temporal"] = self.analyze_temporal_trends()
            logger.info("Completed temporal analysis")

        # Store results
        self.results = results
        cfg[cfg["basename"]]["analysis"] = {
            "completed": True,
            "results_summary": self._summarize_results(results),
        }

        return cfg

    def _summarize_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize analysis results"""
        summary = {
            "fields_analyzed": len(
                [k for k in results.keys() if k != "portfolio" and k != "temporal"]
            ),
            "analysis_timestamp": datetime.now().isoformat(),
        }

        if "portfolio" in results:
            summary["portfolio_size"] = results["portfolio"]["total_fields"]
            summary["total_reserves_boe"] = (
                results["portfolio"]["total_recoverable_oil"]
                + results["portfolio"]["total_recoverable_gas"] / 6
            )

        return summary


class FieldAnalyzer:
    """Analyzer for individual fields"""

    def analyze(
        self,
        field_data: pd.DataFrame,
        wellbore_data: pd.DataFrame,
        production_data: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Perform comprehensive field analysis"""
        return {
            "field_characteristics": self._analyze_characteristics(field_data),
            "drilling_efficiency": self._analyze_drilling(wellbore_data),
            "production_performance": self._analyze_production(production_data),
        }

    def _analyze_characteristics(self, field_data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze field characteristics"""
        return {
            "water_depth_m": field_data["water_depth_m"].iloc[0],
            "discovery_year": field_data["discovery_year"].iloc[0],
            "status": field_data["status"].iloc[0],
        }

    def _analyze_drilling(self, wellbore_data: pd.DataFrame) -> Dict[str, float]:
        """Analyze drilling efficiency"""
        if wellbore_data.empty:
            return {}

        return {
            "total_wells": len(wellbore_data),
            "average_depth_m": wellbore_data["depth_m"].mean(),
            "average_drilling_days": wellbore_data["drilling_days"].mean(),
        }

    def _analyze_production(self, production_data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze production performance"""
        if production_data.empty:
            return {}

        return {
            "peak_oil_rate": production_data["oil_production_mmbbl"].max(),
            "peak_gas_rate": production_data["gas_production_bcf"].max(),
            "years_producing": (
                len(production_data["year"].unique())
                if "year" in production_data
                else 0
            ),
        }


class PortfolioAnalyzer:
    """Analyzer for portfolio of fields"""

    def analyze(self, fields_data: pd.DataFrame) -> Dict[str, Any]:
        """Perform portfolio analysis"""
        return {
            "portfolio_metrics": self._calculate_portfolio_metrics(fields_data),
            "risk_profile": self._assess_risk_profile(fields_data),
            "optimization_opportunities": self._identify_opportunities(fields_data),
        }

    def _calculate_portfolio_metrics(
        self, fields_data: pd.DataFrame
    ) -> Dict[str, float]:
        """Calculate portfolio-level metrics"""
        return {
            "total_fields": len(fields_data),
            "average_field_size_mmboe": (
                fields_data["recoverable_oil_mmbbl"]
                + fields_data["recoverable_gas_bcf"] / 6
            ).mean(),
            "portfolio_concentration": self._calculate_concentration(fields_data),
        }

    def _calculate_concentration(self, fields_data: pd.DataFrame) -> float:
        """Calculate portfolio concentration (Herfindahl index)"""
        total_boe = (
            fields_data["recoverable_oil_mmbbl"]
            + fields_data["recoverable_gas_bcf"] / 6
        ).sum()

        if total_boe == 0:
            return 0

        market_shares = (
            fields_data["recoverable_oil_mmbbl"]
            + fields_data["recoverable_gas_bcf"] / 6
        ) / total_boe

        return (market_shares**2).sum()

    def _assess_risk_profile(self, fields_data: pd.DataFrame) -> Dict[str, Any]:
        """Assess portfolio risk profile"""
        return {
            "water_depth_risk": (
                "high" if fields_data["water_depth_m"].mean() > 1000 else "moderate"
            ),
            "maturity_risk": self._assess_maturity_risk(fields_data),
            "geographic_concentration": "norwegian_continental_shelf",
        }

    def _assess_maturity_risk(self, fields_data: pd.DataFrame) -> str:
        """Assess maturity risk of portfolio"""
        if "production_start" not in fields_data.columns:
            return "unknown"

        current_year = datetime.now().year
        avg_years = (current_year - fields_data["production_start"]).mean()

        if avg_years < 10:
            return "low"
        elif avg_years < 25:
            return "moderate"
        else:
            return "high"

    def _identify_opportunities(self, fields_data: pd.DataFrame) -> List[str]:
        """Identify optimization opportunities"""
        opportunities = []

        # Check for low recovery factors
        low_recovery = fields_data[fields_data["recovery_factor"] < 0.3]
        if not low_recovery.empty:
            opportunities.append(f"EOR potential in {len(low_recovery)} fields")

        # Check for idle fields
        if "status" in fields_data.columns:
            idle = fields_data[fields_data["status"] == "IDLE"]
            if not idle.empty:
                opportunities.append(f"Reactivation potential for {len(idle)} fields")

        return opportunities


class TemporalAnalyzer:
    """Analyzer for temporal trends"""

    def analyze(
        self, data: Dict[str, pd.DataFrame], resolution: str = "yearly"
    ) -> Dict[str, Any]:
        """Analyze temporal trends in data"""
        return {
            "production_trends": self._analyze_production_trends(
                data.get("production")
            ),
            "discovery_trends": self._analyze_discovery_trends(data.get("fields")),
            "activity_trends": self._analyze_activity_trends(data.get("wellbores")),
        }

    def _analyze_production_trends(
        self, production_data: Optional[pd.DataFrame]
    ) -> Dict[str, Any]:
        """Analyze production trends over time"""
        if production_data is None or production_data.empty:
            return {}

        return {
            "oil_trend": (
                "declining"
                if self._is_declining(production_data, "oil_production_mmbbl")
                else "stable"
            ),
            "gas_trend": (
                "declining"
                if self._is_declining(production_data, "gas_production_bcf")
                else "stable"
            ),
        }

    def _is_declining(self, data: pd.DataFrame, column: str) -> bool:
        """Check if a trend is declining"""
        if column not in data.columns or "year" not in data.columns:
            return False

        yearly = data.groupby("year")[column].sum()
        if len(yearly) < 3:
            return False

        # Simple linear regression trend
        x = np.arange(len(yearly))
        y = yearly.values
        slope = np.polyfit(x, y, 1)[0]

        return slope < 0

    def _analyze_discovery_trends(
        self, fields_data: Optional[pd.DataFrame]
    ) -> Dict[str, Any]:
        """Analyze discovery trends"""
        if fields_data is None or "discovery_year" not in fields_data.columns:
            return {}

        discoveries_by_decade = {}
        for year in fields_data["discovery_year"]:
            decade = (year // 10) * 10
            discoveries_by_decade[decade] = discoveries_by_decade.get(decade, 0) + 1

        return {"discoveries_by_decade": discoveries_by_decade}

    def _analyze_activity_trends(
        self, wellbore_data: Optional[pd.DataFrame]
    ) -> Dict[str, Any]:
        """Analyze drilling activity trends"""
        if wellbore_data is None or "completion_year" not in wellbore_data.columns:
            return {}

        wells_by_year = wellbore_data.groupby("completion_year").size()

        return {
            "peak_drilling_year": wells_by_year.idxmax(),
            "peak_wells_count": wells_by_year.max(),
            "average_wells_per_year": wells_by_year.mean(),
        }


class MetricsCalculator:
    """Calculator for various field and portfolio metrics"""

    def calculate_field_metrics(
        self,
        field_data: pd.DataFrame,
        wellbore_data: pd.DataFrame,
        production_data: pd.DataFrame,
    ) -> Dict[str, float]:
        """Calculate comprehensive field metrics"""
        metrics = {}

        # Recovery efficiency
        if "recovery_factor" in field_data.columns:
            metrics["recovery_efficiency"] = field_data["recovery_factor"].iloc[0]

        # Production maturity
        if "production_start" in field_data.columns:
            years_producing = (
                datetime.now().year - field_data["production_start"].iloc[0]
            )
            expected_life = 30  # Typical field life
            metrics["production_maturity"] = min(years_producing / expected_life, 1.0)

        # Economic viability (simplified)
        if "recoverable_oil_mmbbl" in field_data.columns:
            oil_reserves = field_data["recoverable_oil_mmbbl"].iloc[0]
            # Simplified viability score based on size
            if oil_reserves > 1000:
                metrics["economic_viability"] = 0.9
            elif oil_reserves > 500:
                metrics["economic_viability"] = 0.7
            elif oil_reserves > 100:
                metrics["economic_viability"] = 0.5
            else:
                metrics["economic_viability"] = 0.3

        # Drilling efficiency
        if not wellbore_data.empty and "drilling_days" in wellbore_data.columns:
            metrics["drilling_efficiency"] = 1.0 / (
                wellbore_data["drilling_days"].mean() / 30
            )

        # Production efficiency
        if not production_data.empty:
            if "oil_production_mmbbl" in production_data.columns:
                metrics["average_oil_rate"] = production_data[
                    "oil_production_mmbbl"
                ].mean()
            if "gas_production_bcf" in production_data.columns:
                metrics["average_gas_rate"] = production_data[
                    "gas_production_bcf"
                ].mean()

        return metrics

    def calculate_portfolio_metrics(
        self, fields_data: pd.DataFrame
    ) -> Dict[str, float]:
        """Calculate portfolio-level metrics"""
        metrics = {}

        # Size metrics
        metrics["total_oil_reserves_mmbbl"] = fields_data["recoverable_oil_mmbbl"].sum()
        metrics["total_gas_reserves_bcf"] = fields_data["recoverable_gas_bcf"].sum()
        metrics["total_boe_mmboe"] = (
            metrics["total_oil_reserves_mmbbl"] + metrics["total_gas_reserves_bcf"] / 6
        )

        # Efficiency metrics
        metrics["average_recovery_factor"] = fields_data["recovery_factor"].mean()
        metrics["weighted_recovery_factor"] = np.average(
            fields_data["recovery_factor"], weights=fields_data["recoverable_oil_mmbbl"]
        )

        # Risk metrics
        metrics["water_depth_std"] = fields_data["water_depth_m"].std()
        metrics["size_diversity"] = 1 - self._calculate_gini_coefficient(
            fields_data["recoverable_oil_mmbbl"]
        )

        return metrics

    def _calculate_gini_coefficient(self, values: pd.Series) -> float:
        """Calculate Gini coefficient for concentration measurement"""
        sorted_values = sorted(values)
        n = len(sorted_values)

        if n == 0:
            return 0

        cumsum = 0
        for i, value in enumerate(sorted_values):
            cumsum += (n - i) * value

        return (n + 1 - 2 * cumsum / sum(sorted_values)) / n
