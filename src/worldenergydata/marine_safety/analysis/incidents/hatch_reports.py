# ABOUTME: Report generation module for hatch, door, and opening maloperation incidents.
# ABOUTME: Generates comprehensive analysis reports combining all analytical features.

"""
Hatch Maloperation Reports Module

This module provides report generation capabilities including:
- Comprehensive analysis reports
- Summary statistics
- Case study compilation
- Trend reporting
"""

from typing import Any, Dict, List

from .hatch_analysis import HatchAnalyzer
from .hatch_detection import HatchDetector
from .hatch_statistics import HatchStatistics


class HatchReportGenerator:
    """
    Report generator for hatch maloperation incident analysis.

    Combines detection, analysis, and statistics into comprehensive reports.
    """

    def __init__(
        self,
        detector: HatchDetector = None,
        analyzer: HatchAnalyzer = None,
        statistics: HatchStatistics = None,
    ):
        """
        Initialize the HatchReportGenerator.

        Args:
            detector: Optional HatchDetector instance
            analyzer: Optional HatchAnalyzer instance
            statistics: Optional HatchStatistics instance
        """
        self.detector = detector or HatchDetector()
        self.analyzer = analyzer or HatchAnalyzer()
        self.statistics = statistics or HatchStatistics(self.analyzer)

    def generate_comprehensive_report(
        self, incidents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive analysis report combining all features.

        Args:
            incidents: List of incident dictionaries

        Returns:
            Comprehensive report dictionary
        """
        # Filter to only hatch incidents
        hatch_incidents = [
            inc
            for inc in incidents
            if self.detector.is_hatch_maloperation_incident(inc)
        ]

        if not hatch_incidents:
            return {"error": "No hatch maloperation incidents found in dataset"}

        # Collect dates for range calculation
        incident_dates = [
            inc["date"] for inc in hatch_incidents if inc.get("date")
        ]

        # Generate all analyses
        report = {
            "summary_statistics": {
                "total_incidents": len(hatch_incidents),
                "date_range": {
                    "earliest": min(incident_dates) if incident_dates else None,
                    "latest": max(incident_dates) if incident_dates else None,
                },
                "severity_distribution": self.statistics.get_severity_distribution(
                    hatch_incidents
                ),
            },
            "location_analysis": self.statistics.get_location_statistics(
                hatch_incidents
            ),
            "consequence_analysis": self.statistics.get_consequence_statistics(
                hatch_incidents
            ),
            "contributing_factors": self.statistics.analyze_contributing_factors(
                hatch_incidents
            ),
            "risk_assessment": self.statistics.generate_risk_assessment(
                hatch_incidents
            ),
            "recommendations": self.statistics.aggregate_recommendations(
                hatch_incidents
            ),
            "case_studies": [
                self.analyzer.extract_case_study(inc)
                for inc in hatch_incidents
                if self.analyzer.is_significant_incident(inc)
            ],
            "trends": self.statistics.calculate_trends(hatch_incidents),
        }

        return report

    def generate_summary_report(
        self, incidents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a brief summary report.

        Args:
            incidents: List of incident dictionaries

        Returns:
            Summary report dictionary
        """
        # Filter to only hatch incidents
        hatch_incidents = [
            inc
            for inc in incidents
            if self.detector.is_hatch_maloperation_incident(inc)
        ]

        if not hatch_incidents:
            return {"error": "No hatch maloperation incidents found in dataset"}

        consequence_stats = self.statistics.get_consequence_statistics(hatch_incidents)
        risk_assessment = self.statistics.generate_risk_assessment(hatch_incidents)

        return {
            "total_incidents": len(hatch_incidents),
            "total_fatalities": consequence_stats.get("total_fatalities", 0),
            "total_injuries": consequence_stats.get("total_injuries", 0),
            "average_risk_score": risk_assessment.get("average_risk_score", 0),
            "high_risk_count": risk_assessment.get("high_risk_incidents", 0),
            "trend": self.statistics.calculate_trends(hatch_incidents),
        }

    def generate_case_study_report(
        self, incidents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate a report focused on significant case studies.

        Args:
            incidents: List of incident dictionaries

        Returns:
            List of case study dictionaries
        """
        # Filter to only hatch incidents
        hatch_incidents = [
            inc
            for inc in incidents
            if self.detector.is_hatch_maloperation_incident(inc)
        ]

        # Extract case studies from significant incidents
        case_studies = [
            self.analyzer.extract_case_study(inc)
            for inc in hatch_incidents
            if self.analyzer.is_significant_incident(inc)
        ]

        return case_studies

    def generate_trend_report(
        self, incidents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a trend-focused report.

        Args:
            incidents: List of incident dictionaries

        Returns:
            Trend report dictionary
        """
        # Filter to only hatch incidents
        hatch_incidents = [
            inc
            for inc in incidents
            if self.detector.is_hatch_maloperation_incident(inc)
        ]

        if not hatch_incidents:
            return {"error": "No hatch maloperation incidents found in dataset"}

        return {
            "time_series": self.statistics.get_time_series_data(hatch_incidents),
            "trends": self.statistics.calculate_trends(hatch_incidents),
            "severity_distribution": self.statistics.get_severity_distribution(
                hatch_incidents
            ),
            "location_distribution": self.statistics.get_location_statistics(
                hatch_incidents
            ),
        }
