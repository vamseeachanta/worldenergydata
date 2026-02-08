# ABOUTME: Statistical analysis module for hatch, door, and opening maloperation incidents.
# ABOUTME: Provides location stats, consequence stats, severity distribution, trends, and time series.

"""
Hatch Maloperation Statistics Module

This module provides statistical analysis capabilities including:
- Location-based statistics
- Consequence-based statistics
- Severity distribution
- Time series data generation
- Trend calculation
- Recommendation aggregation
"""

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List

from .hatch_analysis import HatchAnalyzer


class HatchStatistics:
    """
    Statistical analysis for hatch maloperation incidents.

    Provides aggregation and trending capabilities across incident datasets.
    """

    def __init__(self, analyzer: HatchAnalyzer = None):
        """
        Initialize the HatchStatistics.

        Args:
            analyzer: Optional HatchAnalyzer instance. Creates one if not provided.
        """
        self.analyzer = analyzer or HatchAnalyzer()

    def get_location_statistics(
        self, incidents: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Generate location-based statistics for incidents.

        Args:
            incidents: List of incident dictionaries

        Returns:
            Dictionary with location type counts
        """
        location_counts = Counter()

        for incident in incidents:
            location_type = self.analyzer.classify_location(incident)
            location_counts[location_type] += 1

        stats = dict(location_counts)
        stats["total"] = len(incidents)

        return stats

    def get_consequence_statistics(
        self, incidents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate consequence-based statistics.

        Args:
            incidents: List of incident dictionaries

        Returns:
            Dictionary with consequence statistics
        """
        consequence_counts = Counter()
        total_fatalities = 0
        total_injuries = 0

        for incident in incidents:
            consequences = self.analyzer.analyze_consequences(incident)
            for consequence in consequences:
                consequence_counts[consequence] += 1

            total_fatalities += incident.get("fatalities", 0)
            total_injuries += incident.get("injuries", 0)

        return {
            **dict(consequence_counts),
            "total_incidents": len(incidents),
            "total_fatalities": total_fatalities,
            "total_injuries": total_injuries,
        }

    def get_severity_distribution(
        self, incidents: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Generate severity distribution statistics.

        Args:
            incidents: List of incident dictionaries

        Returns:
            Dictionary with severity level counts
        """
        severity_counts = Counter()

        for incident in incidents:
            severity = incident.get("severity", "Unknown")
            severity_counts[severity] += 1

        return dict(severity_counts)

    def get_time_series_data(
        self, incidents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate time series data for incident trending.

        Args:
            incidents: List of incident dictionaries

        Returns:
            List of time series data points
        """
        # Group incidents by month
        monthly_counts = defaultdict(int)

        for incident in incidents:
            incident_date = incident.get("date")
            if incident_date:
                # Create month key (YYYY-MM)
                if isinstance(incident_date, datetime):
                    month_key = incident_date.strftime("%Y-%m")
                else:
                    # Handle date objects
                    month_key = f"{incident_date.year:04d}-{incident_date.month:02d}"

                monthly_counts[month_key] += 1

        # Convert to sorted list of dictionaries
        time_series = [
            {"period": month, "count": count}
            for month, count in sorted(monthly_counts.items())
        ]

        return time_series

    def calculate_trends(self, incidents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate trending information from incident data.

        Args:
            incidents: List of incident dictionaries

        Returns:
            Dictionary with trend analysis
        """
        if not incidents:
            return {"direction": "stable", "change_rate": 0}

        # Get time series
        time_series = self.get_time_series_data(incidents)

        if len(time_series) < 2:
            return {"direction": "stable", "change_rate": 0}

        # Simple trend: compare first half to second half
        midpoint = len(time_series) // 2
        first_half_avg = sum(d["count"] for d in time_series[:midpoint]) / midpoint
        second_half_avg = sum(d["count"] for d in time_series[midpoint:]) / (
            len(time_series) - midpoint
        )

        change_rate = (
            ((second_half_avg - first_half_avg) / first_half_avg * 100)
            if first_half_avg > 0
            else 0
        )

        if change_rate > 10:
            direction = "increasing"
        elif change_rate < -10:
            direction = "decreasing"
        else:
            direction = "stable"

        return {
            "direction": direction,
            "change_rate": round(change_rate, 2),
            "first_half_avg": round(first_half_avg, 2),
            "second_half_avg": round(second_half_avg, 2),
        }

    def aggregate_recommendations(
        self, incidents: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Aggregate recommendations from multiple incidents.

        Args:
            incidents: List of incident dictionaries

        Returns:
            Dictionary with recommendation text and frequency count
        """
        recommendation_counts = Counter()

        for incident in incidents:
            recommendations = self.analyzer.generate_recommendations(incident)
            for rec in recommendations:
                recommendation_counts[rec] += 1

        return dict(recommendation_counts)

    def analyze_contributing_factors(
        self, incidents: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Analyze distribution of contributing factors across incidents.

        Args:
            incidents: List of incident dictionaries

        Returns:
            Dictionary with factor type counts
        """
        factor_counts = Counter()

        for incident in incidents:
            factors = self.analyzer.identify_contributing_factors(incident)
            for factor in factors:
                factor_counts[factor] += 1

        return dict(factor_counts)

    def generate_risk_assessment(
        self, incidents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate overall risk assessment from incidents.

        Args:
            incidents: List of incident dictionaries

        Returns:
            Dictionary with risk assessment metrics
        """
        risk_scores = [self.analyzer.calculate_risk_score(inc) for inc in incidents]

        if not risk_scores:
            return {}

        return {
            "average_risk_score": round(sum(risk_scores) / len(risk_scores), 2),
            "highest_risk_score": max(risk_scores),
            "lowest_risk_score": min(risk_scores),
            "high_risk_incidents": len([s for s in risk_scores if s >= 70]),
            "moderate_risk_incidents": len([s for s in risk_scores if 40 <= s < 70]),
            "low_risk_incidents": len([s for s in risk_scores if s < 40]),
        }
