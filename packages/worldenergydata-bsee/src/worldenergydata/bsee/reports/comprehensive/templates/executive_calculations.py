"""
Executive Template Calculations.

This module provides trend analysis, performance scoring, strategic metrics,
and forecasting calculations for executive reporting.
"""

from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .executive_kpi_generator import KPIGenerator
from .executive_models import ExecutiveKPI, PerformanceScore, StrategicMetric


class ExecutiveCalculations:
    """
    Calculation engine for executive metrics and KPIs.

    Provides methods for generating KPIs, analyzing trends,
    calculating performance scores, and strategic forecasting.
    """

    def __init__(
        self, kpi_thresholds: Optional[Dict] = None, benchmarks: Optional[Dict] = None
    ):
        """
        Initialize calculations with thresholds and benchmarks.

        Args:
            kpi_thresholds: KPI threshold configurations
            benchmarks: Industry benchmark data
        """
        self.kpi_thresholds = kpi_thresholds or self._default_kpi_thresholds()
        self.benchmarks = benchmarks or self._default_benchmarks()
        self._kpi_generator = KPIGenerator(kpi_thresholds=self.kpi_thresholds)

    def _default_kpi_thresholds(self) -> Dict:
        """Get default KPI thresholds."""
        return {
            "uptime": {"green": 95, "yellow": 90},
            "efficiency": {"green": 85, "yellow": 80},
            "safety_trir": {"green": 0.5, "yellow": 1.0},
            "emissions_intensity": {"green": 15, "yellow": 20},
            "roi": {"green": 20, "yellow": 15},
            "npv": {"green": 0, "yellow": -1000000},
        }

    def _default_benchmarks(self) -> Dict:
        """Get default industry benchmarks."""
        return {
            "uptime": 92.0,
            "efficiency": 85.0,
            "safety_trir": 0.75,
            "emissions_intensity": 18.0,
            "operating_cost_per_boe": 28.0,
            "finding_cost_per_boe": 15.0,
        }

    # Delegate KPI generation to KPIGenerator
    def generate_executive_kpis(self, data: Dict) -> List[ExecutiveKPI]:
        """Generate executive KPIs from report data."""
        return self._kpi_generator.generate_executive_kpis(
            data, trend_calculator=self.calculate_trend
        )

    def determine_kpi_status(self, value: float, target: float) -> str:
        """Determine KPI status (green/yellow/red)."""
        return self._kpi_generator.determine_kpi_status(value, target)

    def determine_traffic_light_status(
        self, value: float, green_threshold: float, yellow_threshold: float
    ) -> str:
        """Determine traffic light status."""
        return self._kpi_generator.determine_traffic_light_status(
            value, green_threshold, yellow_threshold
        )

    # Trend analysis methods
    def calculate_trend(self, history: List[float]) -> str:
        """
        Calculate trend from historical data.

        Args:
            history: List of historical values

        Returns:
            Trend direction (up/down/stable)
        """
        if len(history) < 2:
            return "stable"

        # Simple linear trend
        recent = history[-3:] if len(history) >= 3 else history
        if len(recent) < 2:
            return "stable"

        avg_change = sum(recent[i] - recent[i - 1] for i in range(1, len(recent))) / (
            len(recent) - 1
        )

        if avg_change > 0.01 * recent[0]:  # More than 1% positive change
            return "up"
        elif avg_change < -0.01 * recent[0]:  # More than 1% negative change
            return "down"
        else:
            return "stable"

    def analyze_kpi_trend(self, values: List[float]) -> str:
        """Analyze KPI trend over time."""
        return self.calculate_trend(values)

    # Performance scoring
    def calculate_performance_score(self, kpis: List[ExecutiveKPI]) -> PerformanceScore:
        """
        Calculate overall performance score from KPIs.

        Args:
            kpis: List of ExecutiveKPI objects

        Returns:
            PerformanceScore object
        """
        category_scores = {}
        category_counts = {}

        for kpi in kpis:
            if kpi.target:
                score = min(100, kpi.get_performance_percentage())

                if kpi.category not in category_scores:
                    category_scores[kpi.category] = 0
                    category_counts[kpi.category] = 0

                category_scores[kpi.category] += score
                category_counts[kpi.category] += 1

        # Calculate average score per category
        for category in category_scores:
            if category_counts[category] > 0:
                category_scores[category] = round(
                    category_scores[category] / category_counts[category], 1
                )

        # Calculate overall score
        if category_scores:
            overall = round(sum(category_scores.values()) / len(category_scores), 1)
        else:
            overall = 0.0

        # Determine trend
        trend = "stable"
        if overall >= 85:
            trend = "up"
        elif overall < 70:
            trend = "down"

        return PerformanceScore(
            overall=overall,
            category_scores=category_scores,
            period=datetime.now().strftime("%B %Y"),
            trend=trend,
        )

    def rank_kpis_by_priority(self, kpis: List[ExecutiveKPI]) -> List[ExecutiveKPI]:
        """
        Rank KPIs by priority.

        Args:
            kpis: List of ExecutiveKPI objects

        Returns:
            Sorted list of KPIs by priority
        """
        # Define priority weights
        priority_weights = {
            "Revenue": 10,
            "Safety Score": 9,
            "Production Volume": 8,
            "EBITDA": 7,
            "Uptime": 6,
            "ROI": 5,
            "Efficiency": 4,
            "Emissions": 3,
        }

        # Sort by priority weight, then by performance
        def sort_key(kpi):
            weight = priority_weights.get(kpi.name, 1)
            performance = kpi.get_performance_percentage() if kpi.target else 0
            # Higher weight and lower performance = higher priority
            return (-weight, -performance if kpi.status == "red" else performance)

        return sorted(kpis, key=sort_key)

    # Strategic metrics
    def calculate_strategic_metrics(self, data: Dict) -> List[StrategicMetric]:
        """
        Calculate strategic business metrics.

        Args:
            data: Strategic data dictionary

        Returns:
            List of StrategicMetric objects
        """
        metrics = []

        if "current_period" not in data or "previous_period" not in data:
            return metrics

        current = data["current_period"]
        previous = data["previous_period"]
        targets = data.get("targets", {})

        metric_configs = [
            ("revenue", "Revenue", "$", "Current Quarter"),
            ("market_share", "Market Share", "%", "Current Quarter"),
            ("roi", "Return on Investment", "%", "Current Quarter"),
            ("production_growth", "Production Growth", "%", "YoY"),
            ("cost_reduction", "Cost Reduction", "%", "YoY"),
        ]

        for key, name, unit, period in metric_configs:
            if key in current:
                metrics.append(
                    StrategicMetric(
                        name=name,
                        current_value=current[key],
                        previous_value=previous.get(key),
                        target_value=targets.get(key),
                        unit=unit,
                        period=period,
                    )
                )

        return metrics

    def compare_with_benchmarks(self, data: Dict, benchmarks: Dict) -> Dict:
        """
        Compare KPIs with industry benchmarks.

        Args:
            data: Company data
            benchmarks: Industry benchmark data

        Returns:
            Comparison results dictionary
        """
        comparisons = {}

        for metric, benchmark_value in benchmarks.items():
            if metric in data.get("operational", {}):
                company_value = data["operational"][metric]
                comparisons[metric] = {
                    "company_value": company_value,
                    "benchmark": benchmark_value,
                    "vs_benchmark": company_value - benchmark_value,
                    "performance": (
                        "above" if company_value > benchmark_value else "below"
                    ),
                }

        return comparisons

    # Year-over-year analysis
    def analyze_year_over_year(self, data: Dict) -> Dict:
        """
        Analyze year-over-year metrics.

        Args:
            data: Multi-year data dictionary

        Returns:
            YoY analysis results
        """
        years = sorted(data.keys())

        if len(years) < 2:
            return {"error": "Insufficient data for YoY analysis"}

        latest_year = years[-1]
        previous_year = years[-2]

        # Calculate CAGR if more than 2 years
        cagr = self._calculate_cagr(data, years, latest_year)

        # Determine trend direction
        trend_direction = self._determine_revenue_trend(data, years)

        # Calculate volatility
        volatility = self._calculate_volatility(data, years)

        return {
            "cagr": cagr,
            "trend_direction": trend_direction,
            "volatility": volatility,
            "latest_year": latest_year,
            "comparison_year": previous_year,
        }

    def _calculate_cagr(self, data: Dict, years: List, latest_year) -> Optional[float]:
        """Calculate Compound Annual Growth Rate."""
        if len(years) <= 2:
            return None

        if "revenue" not in data[years[0]] or "revenue" not in data[latest_year]:
            return None

        start_value = float(data[years[0]]["revenue"])
        end_value = float(data[latest_year]["revenue"])
        num_years = len(years) - 1

        if start_value > 0:
            return ((end_value / start_value) ** (1 / num_years) - 1) * 100
        return None

    def _determine_revenue_trend(self, data: Dict, years: List) -> str:
        """Determine revenue trend direction."""
        revenue_trend = []
        for year in years:
            if "revenue" in data[year]:
                revenue_trend.append(float(data[year]["revenue"]))

        if len(revenue_trend) >= 2:
            if revenue_trend[-1] > revenue_trend[-2]:
                return "growth"
            elif revenue_trend[-1] < revenue_trend[-2]:
                return "decline"
        return "stable"

    def _calculate_volatility(self, data: Dict, years: List) -> float:
        """Calculate revenue volatility."""
        revenue_trend = []
        for year in years:
            if "revenue" in data[year]:
                revenue_trend.append(float(data[year]["revenue"]))

        if len(revenue_trend) > 1:
            changes = [
                abs(revenue_trend[i] - revenue_trend[i - 1]) / revenue_trend[i - 1]
                for i in range(1, len(revenue_trend))
            ]
            return sum(changes) / len(changes) * 100
        return 0

    # Forecasting
    def generate_strategic_forecast(
        self, historical_data: pd.DataFrame, periods: int = 3
    ) -> Dict:
        """
        Generate strategic forecast.

        Args:
            historical_data: Historical data DataFrame
            periods: Number of periods to forecast

        Returns:
            Forecast results dictionary
        """
        forecast = {}

        if "revenue" in historical_data.columns:
            forecast.update(self._forecast_metric(historical_data, "revenue", periods))

        if "production" in historical_data.columns:
            result = self._forecast_metric(historical_data, "production", periods)
            forecast["production_forecast"] = result.get("revenue_forecast", [])

        return forecast

    def _forecast_metric(self, data: pd.DataFrame, column: str, periods: int) -> Dict:
        """Generate forecast for a specific metric."""
        values = data[column].values
        x = np.arange(len(values))

        # Linear regression
        z = np.polyfit(x, values, 1)
        p = np.poly1d(z)

        # Generate forecast
        future_x = np.arange(len(values), len(values) + periods)
        forecast_values = p(future_x).tolist()

        # Calculate confidence interval (simplified)
        std_dev = np.std(values)
        confidence_interval = [(f - std_dev, f + std_dev) for f in forecast_values]

        return {
            f"{column}_forecast": forecast_values,
            "confidence_interval": confidence_interval,
        }

    # Goal tracking
    def track_strategic_goals(self, goals: List[Dict]) -> List[Dict]:
        """
        Track strategic goals progress.

        Args:
            goals: List of goal dictionaries

        Returns:
            List of tracking results
        """
        tracking_results = []

        for goal in goals:
            progress = (goal["current"] / goal["target"]) * 100 if goal["target"] else 0

            # Calculate days remaining
            deadline = datetime.strptime(goal["deadline"], "%Y-%m-%d")
            days_remaining = (deadline - datetime.now()).days

            # Determine if on track
            expected_progress = (
                (datetime.now() - datetime(2024, 1, 1)).days
                / (deadline - datetime(2024, 1, 1)).days
                * 100
            )
            on_track = progress >= expected_progress * 0.9  # 90% of expected progress

            tracking_results.append(
                {
                    "name": goal["name"],
                    "progress_percentage": round(progress, 1),
                    "on_track": on_track,
                    "days_remaining": days_remaining,
                    "current": goal["current"],
                    "target": goal["target"],
                    "deadline": goal["deadline"],
                }
            )

        return tracking_results
