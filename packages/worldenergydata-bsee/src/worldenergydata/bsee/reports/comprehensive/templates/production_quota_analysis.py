"""
Production quota analysis module for compliance reporting
Implements quota vs actual production analysis with variance calculations
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import numpy as np

from ..models import ProductionMetrics
from .compliance_template import ProductionQuota


@dataclass
class QuotaVarianceAnalysis:
    """Analysis of production quota variances"""

    entity_id: str
    period_start: date
    period_end: date
    oil_quota_bbls: float
    oil_actual_bbls: float
    gas_quota_mcf: float
    gas_actual_mcf: float

    def __post_init__(self):
        """Calculate derived metrics after initialization"""
        self.oil_variance_bbls = self.oil_actual_bbls - self.oil_quota_bbls
        self.gas_variance_mcf = self.gas_actual_mcf - self.gas_quota_mcf

        # Calculate percentage variances
        self.oil_variance_pct = (
            (self.oil_variance_bbls / self.oil_quota_bbls * 100)
            if self.oil_quota_bbls > 0
            else 0
        )
        self.gas_variance_pct = (
            (self.gas_variance_mcf / self.gas_quota_mcf * 100)
            if self.gas_quota_mcf > 0
            else 0
        )

        # Calculate compliance ratios
        self.oil_compliance_ratio = (
            self.oil_actual_bbls / self.oil_quota_bbls if self.oil_quota_bbls > 0 else 0
        )
        self.gas_compliance_ratio = (
            self.gas_actual_mcf / self.gas_quota_mcf if self.gas_quota_mcf > 0 else 0
        )

    def is_oil_over_quota(self) -> bool:
        """Check if oil production exceeds quota"""
        return self.oil_actual_bbls > self.oil_quota_bbls

    def is_gas_over_quota(self) -> bool:
        """Check if gas production exceeds quota"""
        return self.gas_actual_mcf > self.gas_quota_mcf

    def is_any_quota_exceeded(self) -> bool:
        """Check if any quota is exceeded"""
        return self.is_oil_over_quota() or self.is_gas_over_quota()

    def get_variance_status(self) -> Dict[str, str]:
        """Get variance status for oil and gas"""
        oil_status = (
            "Over"
            if self.is_oil_over_quota()
            else "Under" if self.oil_variance_bbls < 0 else "On Target"
        )
        gas_status = (
            "Over"
            if self.is_gas_over_quota()
            else "Under" if self.gas_variance_mcf < 0 else "On Target"
        )

        return {
            "oil_status": oil_status,
            "gas_status": gas_status,
            "overall_status": (
                "Over Quota" if self.is_any_quota_exceeded() else "Within Limits"
            ),
        }

    def calculate_penalty_exposure(
        self, oil_penalty_rate: float = 25.0, gas_penalty_rate: float = 5.0
    ) -> Dict[str, float]:
        """Calculate potential penalty exposure for over-production"""
        oil_penalty = (
            max(0, self.oil_variance_bbls) * oil_penalty_rate
            if self.is_oil_over_quota()
            else 0
        )
        gas_penalty = (
            max(0, self.gas_variance_mcf) * gas_penalty_rate
            if self.is_gas_over_quota()
            else 0
        )

        return {
            "oil_penalty_usd": oil_penalty,
            "gas_penalty_usd": gas_penalty,
            "total_penalty_usd": oil_penalty + gas_penalty,
        }

    def calculate_opportunity_cost(
        self, oil_price_usd: float = 75.0, gas_price_usd: float = 4.0
    ) -> Dict[str, float]:
        """Calculate opportunity cost of under-production"""
        oil_opportunity = (
            abs(min(0, self.oil_variance_bbls)) * oil_price_usd
            if self.oil_variance_bbls < 0
            else 0
        )
        gas_opportunity = (
            abs(min(0, self.gas_variance_mcf)) * gas_price_usd
            if self.gas_variance_mcf < 0
            else 0
        )

        return {
            "oil_opportunity_cost_usd": oil_opportunity,
            "gas_opportunity_cost_usd": gas_opportunity,
            "total_opportunity_cost_usd": oil_opportunity + gas_opportunity,
        }

    def get_summary_metrics(self) -> Dict[str, Any]:
        """Get summary metrics for reporting"""
        variance_status = self.get_variance_status()

        return {
            "oil_compliance_pct": self.oil_compliance_ratio * 100,
            "gas_compliance_pct": self.gas_compliance_ratio * 100,
            "oil_variance_pct": self.oil_variance_pct,
            "gas_variance_pct": self.gas_variance_pct,
            "oil_variance_bbls": self.oil_variance_bbls,
            "gas_variance_mcf": self.gas_variance_mcf,
            "variance_status": variance_status,
            "days_in_period": (self.period_end - self.period_start).days + 1,
        }


class ProductionQuotaAnalyzer:
    """Production quota analysis and reporting engine"""

    def __init__(self):
        """Initialize analyzer"""
        self.quota_analyses = []
        self.historical_data = []
        self.compliance_thresholds = {
            "excellent": 0.95,  # 95-105% compliance
            "good": 0.90,  # 90-110% compliance
            "fair": 0.85,  # 85-115% compliance
            "poor": 0.0,  # Below 85% or above 115%
        }

    def analyze_quota_compliance(
        self, production: ProductionMetrics, quota: ProductionQuota
    ) -> QuotaVarianceAnalysis:
        """Analyze quota compliance for a production period"""
        analysis = QuotaVarianceAnalysis(
            entity_id=production.entity_id or quota.entity_id,
            period_start=quota.period_start or production.period_start,
            period_end=quota.period_end or production.period_end,
            oil_quota_bbls=quota.oil_quota_bbls,
            oil_actual_bbls=production.oil_production_bbls,
            gas_quota_mcf=quota.gas_quota_mcf,
            gas_actual_mcf=production.gas_production_mcf,
        )

        self.quota_analyses.append(analysis)
        return analysis

    def analyze_multiple_periods(
        self,
        production_list: List[ProductionMetrics],
        quota_list: List[ProductionQuota],
    ) -> List[QuotaVarianceAnalysis]:
        """Analyze quota compliance for multiple periods"""
        analyses = []

        # Match production to quotas by entity and period
        for production in production_list:
            matching_quota = self._find_matching_quota(production, quota_list)
            if matching_quota:
                analysis = self.analyze_quota_compliance(production, matching_quota)
                analyses.append(analysis)

        return analyses

    def _find_matching_quota(
        self, production: ProductionMetrics, quota_list: List[ProductionQuota]
    ) -> Optional[ProductionQuota]:
        """Find matching quota for production data"""
        for quota in quota_list:
            if quota.entity_id == production.entity_id and self._periods_overlap(
                production, quota
            ):
                return quota
        return None

    def _periods_overlap(
        self, production: ProductionMetrics, quota: ProductionQuota
    ) -> bool:
        """Check if production and quota periods overlap"""
        if not all(
            [
                production.period_start,
                production.period_end,
                quota.period_start,
                quota.period_end,
            ]
        ):
            return False

        return (
            production.period_start <= quota.period_end
            and production.period_end >= quota.period_start
        )

    def calculate_compliance_trend(
        self, analyses: List[QuotaVarianceAnalysis]
    ) -> Dict[str, Any]:
        """Calculate compliance trends over multiple periods"""
        if not analyses:
            return {"trend": "No Data", "average_compliance": 0}

        # Sort by period start date
        sorted_analyses = sorted(analyses, key=lambda x: x.period_start)

        oil_compliances = [a.oil_compliance_ratio for a in sorted_analyses]
        gas_compliances = [a.gas_compliance_ratio for a in sorted_analyses]

        # Calculate trends using simple linear regression
        periods = list(range(len(sorted_analyses)))

        oil_trend = self._calculate_trend(periods, oil_compliances)
        gas_trend = self._calculate_trend(periods, gas_compliances)

        avg_oil_compliance = np.mean(oil_compliances) if oil_compliances else 0
        avg_gas_compliance = np.mean(gas_compliances) if gas_compliances else 0

        return {
            "oil_trend": oil_trend,
            "gas_trend": gas_trend,
            "average_oil_compliance": avg_oil_compliance * 100,
            "average_gas_compliance": avg_gas_compliance * 100,
            "overall_trend": (
                "Improving"
                if (oil_trend + gas_trend) > 0.01
                else "Declining" if (oil_trend + gas_trend) < -0.01 else "Stable"
            ),
            "periods_analyzed": len(sorted_analyses),
        }

    def _calculate_trend(self, x_values: List[int], y_values: List[float]) -> float:
        """Calculate linear trend slope"""
        if len(x_values) < 2 or len(y_values) < 2:
            return 0.0

        x_array = np.array(x_values)
        y_array = np.array(y_values)

        # Calculate slope using least squares
        n = len(x_array)
        slope = (n * np.sum(x_array * y_array) - np.sum(x_array) * np.sum(y_array)) / (
            n * np.sum(x_array**2) - np.sum(x_array) ** 2
        )

        return slope

    def generate_compliance_rating(
        self, analysis: QuotaVarianceAnalysis
    ) -> Dict[str, str]:
        """Generate compliance rating based on performance"""
        oil_ratio = analysis.oil_compliance_ratio
        gas_ratio = analysis.gas_compliance_ratio

        # Rate oil compliance
        oil_rating = self._rate_compliance_ratio(oil_ratio)
        gas_rating = self._rate_compliance_ratio(gas_ratio)

        # Overall rating is the worst of the two
        ratings_order = ["Excellent", "Good", "Fair", "Poor"]
        oil_index = ratings_order.index(oil_rating)
        gas_index = ratings_order.index(gas_rating)
        overall_rating = ratings_order[max(oil_index, gas_index)]

        return {
            "oil_rating": oil_rating,
            "gas_rating": gas_rating,
            "overall_rating": overall_rating,
        }

    def _rate_compliance_ratio(self, ratio: float) -> str:
        """Rate individual compliance ratio"""
        if 0.95 <= ratio <= 1.05:
            return "Excellent"
        elif 0.90 <= ratio <= 1.10:
            return "Good"
        elif 0.85 <= ratio <= 1.15:
            return "Fair"
        else:
            return "Poor"

    def create_quota_dashboard_data(
        self, analyses: List[QuotaVarianceAnalysis]
    ) -> Dict[str, Any]:
        """Create dashboard data for quota analysis visualization"""
        if not analyses:
            return {"error": "No analysis data available"}

        # Latest analysis
        latest = max(analyses, key=lambda x: x.period_start)

        # Compliance trends
        trend_data = self.calculate_compliance_trend(analyses)

        # Summary statistics
        oil_compliances = [a.oil_compliance_ratio * 100 for a in analyses]
        gas_compliances = [a.gas_compliance_ratio * 100 for a in analyses]

        dashboard_data = {
            "current_period": {
                "period": f"{latest.period_start} to {latest.period_end}",
                "oil_compliance": latest.oil_compliance_ratio * 100,
                "gas_compliance": latest.gas_compliance_ratio * 100,
                "oil_variance": latest.oil_variance_bbls,
                "gas_variance": latest.gas_variance_mcf,
                "status": latest.get_variance_status(),
            },
            "trends": trend_data,
            "historical_performance": {
                "periods_count": len(analyses),
                "oil_compliance_avg": (
                    np.mean(oil_compliances) if oil_compliances else 0
                ),
                "oil_compliance_min": min(oil_compliances) if oil_compliances else 0,
                "oil_compliance_max": max(oil_compliances) if oil_compliances else 0,
                "gas_compliance_avg": (
                    np.mean(gas_compliances) if gas_compliances else 0
                ),
                "gas_compliance_min": min(gas_compliances) if gas_compliances else 0,
                "gas_compliance_max": max(gas_compliances) if gas_compliances else 0,
            },
            "risk_metrics": {
                "periods_over_quota": len(
                    [a for a in analyses if a.is_any_quota_exceeded()]
                ),
                "max_oil_overage": max(
                    [a.oil_variance_bbls for a in analyses if a.oil_variance_bbls > 0],
                    default=0,
                ),
                "max_gas_overage": max(
                    [a.gas_variance_mcf for a in analyses if a.gas_variance_mcf > 0],
                    default=0,
                ),
            },
        }

        return dashboard_data

    def export_quota_analysis_report(
        self, analyses: List[QuotaVarianceAnalysis], format: str = "dict"
    ) -> Dict[str, Any]:
        """Export comprehensive quota analysis report"""
        if not analyses:
            return {"error": "No analysis data to export"}

        report_data = {
            "report_metadata": {
                "generation_date": datetime.now().isoformat(),
                "periods_analyzed": len(analyses),
                "entities": list(set([a.entity_id for a in analyses])),
                "date_range": {
                    "start": min([a.period_start for a in analyses]).isoformat(),
                    "end": max([a.period_end for a in analyses]).isoformat(),
                },
            },
            "executive_summary": self._create_executive_summary(analyses),
            "detailed_analysis": [],
        }

        # Add detailed analysis for each period
        for analysis in sorted(analyses, key=lambda x: x.period_start):
            detail = {
                "period": f"{analysis.period_start} to {analysis.period_end}",
                "entity_id": analysis.entity_id,
                "quotas": {
                    "oil_bbls": analysis.oil_quota_bbls,
                    "gas_mcf": analysis.gas_quota_mcf,
                },
                "actual_production": {
                    "oil_bbls": analysis.oil_actual_bbls,
                    "gas_mcf": analysis.gas_actual_mcf,
                },
                "variance_analysis": analysis.get_summary_metrics(),
                "compliance_rating": self.generate_compliance_rating(analysis),
                "financial_impact": {
                    **analysis.calculate_penalty_exposure(),
                    **analysis.calculate_opportunity_cost(),
                },
            }
            report_data["detailed_analysis"].append(detail)

        return report_data

    def _create_executive_summary(
        self, analyses: List[QuotaVarianceAnalysis]
    ) -> Dict[str, Any]:
        """Create executive summary of quota analysis"""
        total_periods = len(analyses)
        compliant_periods = len([a for a in analyses if not a.is_any_quota_exceeded()])

        # Calculate average compliance
        oil_avg = np.mean([a.oil_compliance_ratio * 100 for a in analyses])
        gas_avg = np.mean([a.gas_compliance_ratio * 100 for a in analyses])

        # Calculate total variances
        total_oil_overage = sum([max(0, a.oil_variance_bbls) for a in analyses])
        total_gas_overage = sum([max(0, a.gas_variance_mcf) for a in analyses])

        summary = {
            "overall_compliance_rate": (
                (compliant_periods / total_periods * 100) if total_periods > 0 else 0
            ),
            "average_oil_compliance": oil_avg,
            "average_gas_compliance": gas_avg,
            "total_oil_overage_bbls": total_oil_overage,
            "total_gas_overage_mcf": total_gas_overage,
            "periods_analyzed": total_periods,
            "compliant_periods": compliant_periods,
            "non_compliant_periods": total_periods - compliant_periods,
            "recommendation": self._generate_compliance_recommendation(
                oil_avg, gas_avg, compliant_periods, total_periods
            ),
        }

        return summary

    def _generate_compliance_recommendation(
        self, oil_avg: float, gas_avg: float, compliant_periods: int, total_periods: int
    ) -> str:
        """Generate compliance recommendation"""
        compliance_rate = (
            (compliant_periods / total_periods) if total_periods > 0 else 0
        )

        if compliance_rate >= 0.95 and oil_avg >= 95 and gas_avg >= 95:
            return "Excellent quota compliance. Continue current practices."
        elif compliance_rate >= 0.80:
            return "Good quota compliance with room for improvement in production planning."
        elif compliance_rate >= 0.60:
            return "Fair quota compliance. Review production forecasting and quota management processes."  # noqa: E501
        else:
            return "Poor quota compliance. Immediate action required to improve production planning and regulatory compliance."  # noqa: E501
