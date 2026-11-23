"""
Executive Template Data Models.

This module contains data classes and enumerations used by the executive
reporting template for KPIs, metrics, and dashboard components.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class KPIStatus(Enum):
    """KPI status indicators."""

    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    GRAY = "gray"  # No data


class TrendDirection(Enum):
    """Trend direction indicators."""

    UP = "up"
    DOWN = "down"
    STABLE = "stable"


@dataclass
class ExecutiveKPI:
    """Executive Key Performance Indicator."""

    name: str
    value: Union[float, int, Decimal]
    unit: str
    target: Optional[Union[float, int, Decimal]] = None
    trend: Optional[str] = None
    status: str = "gray"
    category: str = "General"
    description: Optional[str] = None
    period: Optional[str] = None

    def get_performance_percentage(self) -> float:
        """Calculate performance as percentage of target."""
        if self.target and self.target != 0:
            return round((float(self.value) / float(self.target)) * 100, 2)
        return 0.0

    def is_meeting_target(self) -> bool:
        """Check if KPI is meeting target."""
        if self.target:
            return float(self.value) >= float(self.target)
        return False

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "value": (
                float(self.value) if isinstance(self.value, Decimal) else self.value
            ),
            "unit": self.unit,
            "target": (
                float(self.target) if isinstance(self.target, Decimal) else self.target
            ),
            "trend": self.trend,
            "status": self.status,
            "category": self.category,
            "description": self.description,
            "period": self.period,
            "performance": self.get_performance_percentage(),
        }


@dataclass
class StrategicMetric:
    """Strategic business metric with comparisons."""

    name: str
    current_value: Union[float, int, Decimal]
    previous_value: Optional[Union[float, int, Decimal]] = None
    target_value: Optional[Union[float, int, Decimal]] = None
    unit: str = ""
    period: str = ""

    def get_change(self) -> float:
        """Calculate absolute change from previous period."""
        if self.previous_value is not None:
            return float(self.current_value) - float(self.previous_value)
        return 0.0

    def get_change_percentage(self) -> float:
        """Calculate percentage change from previous period."""
        if self.previous_value and self.previous_value != 0:
            change = self.get_change()
            return round((change / float(self.previous_value)) * 100, 2)
        return 0.0

    def is_meeting_target(self) -> bool:
        """Check if metric is meeting target."""
        if self.target_value:
            return float(self.current_value) >= float(self.target_value)
        return False

    def get_target_gap(self) -> float:
        """Calculate gap to target."""
        if self.target_value:
            return float(self.current_value) - float(self.target_value)
        return 0.0


@dataclass
class PerformanceScore:
    """Overall performance score with category breakdowns."""

    overall: float
    category_scores: Dict[str, float]
    period: str
    trend: str = "stable"

    def get_rating(self) -> str:
        """Get performance rating."""
        if self.overall >= 90:
            return "Excellent"
        elif self.overall >= 80:
            return "Good"
        elif self.overall >= 70:
            return "Satisfactory"
        elif self.overall >= 60:
            return "Needs Improvement"
        else:
            return "Critical"


@dataclass
class ExecutiveSummary:
    """Executive summary container."""

    key_messages: List[str]
    highlights: List[Dict]
    lowlights: List[Dict]
    recommendations: List[str]
    outlook: str


@dataclass
class BusinessHighlight:
    """Business highlight or achievement."""

    title: str
    description: str
    impact: str
    metric: Optional[str] = None
    value: Optional[Union[float, str]] = None


@dataclass
class RiskIndicator:
    """Risk indicator for executive attention."""

    category: str
    risk_level: str  # low, medium, high, critical
    description: str
    mitigation: str
    timeline: Optional[str] = None


@dataclass
class StrategicInitiative:
    """Strategic initiative tracking."""

    name: str
    status: str  # planned, in-progress, completed, delayed
    progress: float  # 0-100
    target_date: datetime
    owner: str
    impact: str


@dataclass
class TrafficLightIndicator:
    """Traffic light status indicator."""

    metric_name: str
    value: Union[float, int]
    status: str  # green, yellow, red
    threshold_green: float
    threshold_yellow: float

    def get_color_code(self) -> str:
        """Get HTML color code for status."""
        colors = {
            "green": "#28a745",
            "yellow": "#ffc107",
            "red": "#dc3545",
            "gray": "#6c757d",
        }
        return colors.get(self.status, "#6c757d")


@dataclass
class ExecutiveDashboard:
    """Executive dashboard container."""

    layout: Dict
    charts: List[Any]
    components: Dict[str, Any]
    export_config: Dict


@dataclass
class ExecutiveChart:
    """Executive chart configuration."""

    type: str
    data: Dict
    layout: Dict
    config: Dict
