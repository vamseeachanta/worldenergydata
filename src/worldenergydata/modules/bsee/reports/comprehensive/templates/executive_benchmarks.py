"""
Executive Benchmarking and Competitive Analysis.

This module provides competitive positioning analysis, peer comparison,
and industry benchmark functionality for executive reporting.
"""

from typing import Any, Dict, List, Optional

from .executive_charts import create_benchmark_radar_chart


class ExecutiveBenchmarking:
    """
    Benchmarking engine for competitive analysis.

    Provides methods for analyzing competitive position, comparing
    with peers, and generating benchmark visualizations.
    """

    def __init__(self, industry_benchmarks: Optional[Dict] = None):
        """
        Initialize benchmarking with industry data.

        Args:
            industry_benchmarks: Industry benchmark data
        """
        self.industry_benchmarks = industry_benchmarks or self._default_benchmarks()

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

    def analyze_competitive_position(self, benchmark_data: Dict) -> Dict:
        """
        Analyze competitive positioning.

        Args:
            benchmark_data: Benchmark data dictionary with keys:
                - company_metrics: Dict of company metric values
                - industry_benchmarks: Dict with percentile values (p25, p50, p75, p90)
                - peer_companies: List of peer company data (optional)

        Returns:
            Competitive analysis results with:
                - percentile_rankings: Dict of metric percentiles
                - peer_comparison: Dict of peer comparisons
                - strengths: List of strong metrics
                - improvement_areas: List of weak metrics
        """
        positioning = {
            "percentile_rankings": {},
            "peer_comparison": {},
            "strengths": [],
            "improvement_areas": [],
        }

        company_metrics = benchmark_data.get("company_metrics", {})
        industry_benchmarks = benchmark_data.get("industry_benchmarks", {})

        # Calculate percentile rankings
        for metric, value in company_metrics.items():
            if metric in industry_benchmarks:
                benchmark = industry_benchmarks[metric]

                # Determine percentile
                if value <= benchmark.get("p25", value):
                    percentile = 25
                elif value <= benchmark.get("p50", value):
                    percentile = 50
                elif value <= benchmark.get("p75", value):
                    percentile = 75
                elif value <= benchmark.get("p90", value):
                    percentile = 90
                else:
                    percentile = 95

                positioning["percentile_rankings"][metric] = percentile

                # Identify strengths and weaknesses
                if percentile >= 75:
                    positioning["strengths"].append(metric)
                elif percentile <= 25:
                    positioning["improvement_areas"].append(metric)

        # Peer comparison
        peer_companies = benchmark_data.get("peer_companies", [])
        for peer in peer_companies:
            peer_name = peer["name"]
            positioning["peer_comparison"][peer_name] = {}

            for metric in ["production_efficiency", "safety_score"]:
                if metric in peer and metric in company_metrics:
                    positioning["peer_comparison"][peer_name][metric] = {
                        "peer_value": peer[metric],
                        "company_value": company_metrics[metric],
                        "difference": company_metrics[metric] - peer[metric],
                    }

        return positioning

    def generate_peer_ranking_table(
        self, peer_companies: List[Dict], company_data: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Generate peer ranking table.

        Args:
            peer_companies: List of peer company data dictionaries
            company_data: Our company data (optional, uses defaults if not provided)

        Returns:
            Sorted ranking table with all companies ranked
        """
        # Add our company to the list
        all_companies = peer_companies.copy()

        our_company = company_data or {
            "name": "Our Company",
            "production_efficiency": 88.5,
            "safety_score": 95.5,
        }
        all_companies.append(our_company)

        # Sort by production efficiency (descending)
        all_companies.sort(
            key=lambda x: x.get("production_efficiency", 0), reverse=True
        )

        # Add ranking
        for i, company in enumerate(all_companies, 1):
            company["rank"] = i

        return all_companies

    def create_radar_chart(self, benchmark_data: Dict) -> Any:
        """
        Create competitive benchmark radar chart.

        Args:
            benchmark_data: Benchmark data with company_metrics and industry_benchmarks

        Returns:
            Plotly figure or None if Plotly unavailable
        """
        return create_benchmark_radar_chart(benchmark_data)

    def calculate_benchmark_gaps(self, company_metrics: Dict) -> Dict:
        """
        Calculate gaps between company metrics and industry benchmarks.

        Args:
            company_metrics: Dictionary of company metric values

        Returns:
            Dictionary of gap analysis results
        """
        gaps = {}

        for metric, company_value in company_metrics.items():
            if metric in self.industry_benchmarks:
                benchmark = self.industry_benchmarks[metric]
                gap = company_value - benchmark

                gaps[metric] = {
                    "company_value": company_value,
                    "benchmark": benchmark,
                    "gap": gap,
                    "gap_percentage": (
                        round((gap / benchmark) * 100, 2) if benchmark else 0
                    ),
                    "status": "above" if gap > 0 else "below" if gap < 0 else "at",
                }

        return gaps

    def identify_improvement_opportunities(self, gaps: Dict) -> List[Dict]:
        """
        Identify improvement opportunities from gap analysis.

        Args:
            gaps: Gap analysis results from calculate_benchmark_gaps

        Returns:
            List of improvement opportunities sorted by potential impact
        """
        opportunities = []

        for metric, gap_data in gaps.items():
            if gap_data["status"] == "below":
                opportunities.append(
                    {
                        "metric": metric,
                        "current": gap_data["company_value"],
                        "target": gap_data["benchmark"],
                        "gap": abs(gap_data["gap"]),
                        "gap_percentage": abs(gap_data["gap_percentage"]),
                        "priority": self._calculate_priority(
                            metric, gap_data["gap_percentage"]
                        ),
                    }
                )

        # Sort by priority (high to low)
        priority_order = {"high": 0, "medium": 1, "low": 2}
        opportunities.sort(key=lambda x: priority_order.get(x["priority"], 3))

        return opportunities

    def _calculate_priority(self, metric: str, gap_percentage: float) -> str:
        """
        Calculate improvement priority based on metric and gap.

        Args:
            metric: Metric name
            gap_percentage: Gap percentage (negative for below benchmark)

        Returns:
            Priority level (high/medium/low)
        """
        # Critical metrics always get high priority if below benchmark
        critical_metrics = ["safety_trir", "uptime", "efficiency"]

        abs_gap = abs(gap_percentage)

        if metric in critical_metrics or abs_gap > 20:
            return "high"
        elif abs_gap > 10:
            return "medium"
        else:
            return "low"

    def generate_competitive_summary(self, benchmark_data: Dict) -> Dict:
        """
        Generate a competitive summary report.

        Args:
            benchmark_data: Full benchmark data

        Returns:
            Summary report dictionary
        """
        positioning = self.analyze_competitive_position(benchmark_data)
        company_metrics = benchmark_data.get("company_metrics", {})
        gaps = self.calculate_benchmark_gaps(company_metrics)
        opportunities = self.identify_improvement_opportunities(gaps)

        # Calculate overall competitive score
        rankings = positioning.get("percentile_rankings", {})
        if rankings:
            avg_percentile = sum(rankings.values()) / len(rankings)
        else:
            avg_percentile = 50

        return {
            "competitive_score": round(avg_percentile, 1),
            "ranking_label": self._get_ranking_label(avg_percentile),
            "total_metrics_analyzed": len(rankings),
            "strengths_count": len(positioning.get("strengths", [])),
            "improvement_areas_count": len(positioning.get("improvement_areas", [])),
            "top_strengths": positioning.get("strengths", [])[:3],
            "top_improvement_areas": [opp["metric"] for opp in opportunities[:3]],
            "peer_comparison_count": len(positioning.get("peer_comparison", {})),
            "positioning": positioning,
            "gaps": gaps,
            "opportunities": opportunities,
        }

    def _get_ranking_label(self, percentile: float) -> str:
        """
        Get ranking label from percentile.

        Args:
            percentile: Average percentile ranking

        Returns:
            Ranking label string
        """
        if percentile >= 90:
            return "Industry Leader"
        elif percentile >= 75:
            return "Above Average"
        elif percentile >= 50:
            return "Average"
        elif percentile >= 25:
            return "Below Average"
        else:
            return "Needs Improvement"
