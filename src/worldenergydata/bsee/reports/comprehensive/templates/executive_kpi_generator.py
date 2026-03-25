"""
Executive KPI Generator.

This module provides KPI generation and status determination
for executive reporting across financial, operational, production,
safety, and environmental categories.
"""

from decimal import Decimal
from typing import Dict, List, Optional, Union

from .executive_models import ExecutiveKPI


class KPIGenerator:
    """
    Generator for executive KPIs.

    Provides methods for generating KPIs from various data sources
    and determining their status based on configurable thresholds.
    """

    def __init__(self, kpi_thresholds: Optional[Dict] = None):
        """
        Initialize KPI generator with thresholds.

        Args:
            kpi_thresholds: KPI threshold configurations
        """
        self.kpi_thresholds = kpi_thresholds or self._default_kpi_thresholds()

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

    def generate_executive_kpis(
        self, data: Dict, trend_calculator: callable = None
    ) -> List[ExecutiveKPI]:
        """
        Generate executive KPIs from report data.

        Args:
            data: Report data dictionary
            trend_calculator: Optional function to calculate trends

        Returns:
            List of ExecutiveKPI objects
        """
        kpis = []

        # Use no-op trend calculator if not provided
        def no_trend(history):
            return "stable"

        calc_trend = trend_calculator or no_trend

        # Financial KPIs
        if "financial" in data:
            kpis.extend(self._generate_financial_kpis(data["financial"], calc_trend))

        # Operational KPIs
        if "operational" in data:
            kpis.extend(
                self._generate_operational_kpis(data["operational"], calc_trend)
            )

        # Production KPIs
        if "production" in data:
            kpis.extend(self._generate_production_kpis(data["production"], calc_trend))

        # Safety KPIs
        if "safety" in data:
            kpis.extend(self._generate_safety_kpis(data["safety"], calc_trend))

        # Environmental KPIs
        if "environmental" in data:
            kpis.extend(
                self._generate_environmental_kpis(data["environmental"], calc_trend)
            )

        return kpis

    def _generate_financial_kpis(
        self, fin_data: Dict, calc_trend: callable
    ) -> List[ExecutiveKPI]:
        """Generate financial KPIs."""
        kpis = []

        if "revenue" in fin_data:
            kpis.append(
                ExecutiveKPI(
                    name="Revenue",
                    value=fin_data["revenue"],
                    unit="$",
                    target=fin_data.get("revenue_target"),
                    trend=calc_trend(fin_data.get("revenue_history", [])),
                    status=self.determine_financial_status(
                        fin_data["revenue"], fin_data.get("revenue_target")
                    ),
                    category="Financial",
                    description="Total revenue for the period",
                )
            )

        if "ebitda" in fin_data:
            kpis.append(
                ExecutiveKPI(
                    name="EBITDA",
                    value=fin_data["ebitda"],
                    unit="$",
                    target=fin_data.get("ebitda_target"),
                    trend=calc_trend(fin_data.get("ebitda_history", [])),
                    status=self.determine_financial_status(
                        fin_data["ebitda"], fin_data.get("ebitda_target")
                    ),
                    category="Financial",
                    description="Earnings before interest, taxes, depreciation and amortization",
                )
            )

        if "roi" in fin_data:
            kpis.append(
                ExecutiveKPI(
                    name="ROI",
                    value=fin_data["roi"],
                    unit="%",
                    target=self.kpi_thresholds.get("roi", {}).get("green", 20),
                    trend=calc_trend(fin_data.get("roi_history", [])),
                    status=self.determine_kpi_status(
                        fin_data["roi"],
                        self.kpi_thresholds.get("roi", {}).get("green", 20),
                    ),
                    category="Financial",
                    description="Return on investment",
                )
            )

        return kpis

    def _generate_operational_kpis(
        self, ops_data: Dict, calc_trend: callable
    ) -> List[ExecutiveKPI]:
        """Generate operational KPIs."""
        kpis = []

        if "uptime_percentage" in ops_data:
            kpis.append(
                ExecutiveKPI(
                    name="Uptime",
                    value=ops_data["uptime_percentage"],
                    unit="%",
                    target=self.kpi_thresholds["uptime"]["green"],
                    trend=calc_trend(ops_data.get("uptime_history", [])),
                    status=self.determine_kpi_status(
                        ops_data["uptime_percentage"],
                        self.kpi_thresholds["uptime"]["green"],
                    ),
                    category="Operational",
                    description="Overall system uptime",
                )
            )

        if "efficiency_rate" in ops_data:
            kpis.append(
                ExecutiveKPI(
                    name="Efficiency",
                    value=ops_data["efficiency_rate"],
                    unit="%",
                    target=self.kpi_thresholds["efficiency"]["green"],
                    trend=calc_trend(ops_data.get("efficiency_history", [])),
                    status=self.determine_kpi_status(
                        ops_data["efficiency_rate"],
                        self.kpi_thresholds["efficiency"]["green"],
                    ),
                    category="Operational",
                    description="Production efficiency rate",
                )
            )

        return kpis

    def _generate_production_kpis(
        self, prod_data: Dict, calc_trend: callable
    ) -> List[ExecutiveKPI]:
        """Generate production KPIs."""
        kpis = []

        if "total_boe" in prod_data:
            kpis.append(
                ExecutiveKPI(
                    name="Production Volume",
                    value=prod_data["total_boe"],
                    unit="BOE",
                    target=prod_data.get("production_target"),
                    trend=calc_trend(prod_data.get("production_history", [])),
                    status=self.determine_production_status(
                        prod_data["total_boe"], prod_data.get("production_target")
                    ),
                    category="Production",
                    description="Total barrel of oil equivalent production",
                )
            )

        return kpis

    def _generate_safety_kpis(
        self, safety_data: Dict, calc_trend: callable
    ) -> List[ExecutiveKPI]:
        """Generate safety KPIs."""
        kpis = []

        if "trir" in safety_data:
            kpis.append(
                ExecutiveKPI(
                    name="Safety Score",
                    value=100 - (safety_data["trir"] * 20),  # Convert TRIR to score
                    unit="score",
                    target=95,
                    trend=calc_trend(safety_data.get("trir_history", [])),
                    status=self.determine_safety_status(safety_data["trir"]),
                    category="Safety",
                    description="Overall safety performance score",
                )
            )

        return kpis

    def _generate_environmental_kpis(
        self, env_data: Dict, calc_trend: callable
    ) -> List[ExecutiveKPI]:
        """Generate environmental KPIs."""
        kpis = []

        if "emissions_tons_co2" in env_data:
            target = env_data.get(
                "emissions_target",
                self.kpi_thresholds["emissions_intensity"]["green"] * 1000,
            )
            kpis.append(
                ExecutiveKPI(
                    name="Emissions",
                    value=env_data["emissions_tons_co2"],
                    unit="tons CO2",
                    target=target,
                    trend=calc_trend(env_data.get("emissions_history", [])),
                    status=self.determine_emissions_status(
                        env_data["emissions_tons_co2"]
                    ),
                    category="Environmental",
                    description="Total CO2 emissions",
                )
            )

        return kpis

    def determine_kpi_status(self, value: float, target: float) -> str:
        """
        Determine KPI status (green/yellow/red).

        Args:
            value: Current value
            target: Target value

        Returns:
            Status string
        """
        if value >= target:
            return "green"
        elif value >= target * 0.95:  # Within 5% of target
            return "yellow"
        else:
            return "red"

    def determine_financial_status(
        self, value: Union[float, Decimal], target: Optional[Union[float, Decimal]]
    ) -> str:
        """Determine financial KPI status."""
        if not target:
            return "gray"

        value_float = float(value)
        target_float = float(target)

        if value_float >= target_float:
            return "green"
        elif value_float >= target_float * 0.9:
            return "yellow"
        else:
            return "red"

    def determine_production_status(self, value: float, target: Optional[float]) -> str:
        """Determine production KPI status."""
        if not target:
            return "gray"

        if value >= target:
            return "green"
        elif value >= target * 0.95:
            return "yellow"
        else:
            return "red"

    def determine_safety_status(self, trir: float) -> str:
        """Determine safety KPI status based on TRIR."""
        thresholds = self.kpi_thresholds.get("safety_trir", {})

        if trir <= thresholds.get("green", 0.5):
            return "green"
        elif trir <= thresholds.get("yellow", 1.0):
            return "yellow"
        else:
            return "red"

    def determine_emissions_status(self, emissions: float) -> str:
        """Determine emissions KPI status."""
        intensity_threshold_green = (
            self.kpi_thresholds["emissions_intensity"]["green"] * 1000
        )
        intensity_threshold_yellow = (
            self.kpi_thresholds["emissions_intensity"]["yellow"] * 1000
        )

        if emissions <= intensity_threshold_green:
            return "green"
        elif emissions <= intensity_threshold_yellow:
            return "yellow"
        else:
            return "red"

    def determine_traffic_light_status(
        self, value: float, green_threshold: float, yellow_threshold: float
    ) -> str:
        """
        Determine traffic light status.

        Args:
            value: Current value
            green_threshold: Threshold for green status
            yellow_threshold: Threshold for yellow status

        Returns:
            Status string (green/yellow/red)
        """
        if value >= green_threshold:
            return "green"
        elif value >= yellow_threshold:
            return "yellow"
        else:
            return "red"
