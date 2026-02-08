"""
Filter components for interactive dashboard.

This module provides quality filtering, date filtering, and filter chain functionality.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .components_base import (
    DASH_AVAILABLE,
    FilterConfig,
    FreshnessStatus,
    QualityLevel,
    dcc,
)

logger = logging.getLogger(__name__)


class QualityFilter:
    """Quality-aware filter component for dashboard data."""

    def __init__(self, config: Optional[FilterConfig] = None):
        """Initialize quality filter."""
        self.config = config or FilterConfig()
        self.quality_levels = {
            QualityLevel.HIGH: (90, 100),
            QualityLevel.MEDIUM: (70, 89),
            QualityLevel.LOW: (50, 69),
            QualityLevel.FAILED: (0, 49),
        }

    def filter_by_quality(
        self, data: pd.DataFrame, min_score: int = 70
    ) -> pd.DataFrame:
        """Filter data by quality score threshold."""
        if "quality_score" not in data.columns:
            logger.warning("No quality_score column found, returning all data")
            return data

        return data[data["quality_score"] >= min_score].copy()

    def filter_by_status(self, data: pd.DataFrame, statuses: List[str]) -> pd.DataFrame:
        """Filter data by verification status."""
        if "verification_status" not in data.columns:
            logger.warning("No verification_status column found, returning all data")
            return data

        return data[data["verification_status"].isin(statuses)].copy()

    def create_quality_dropdown(self, component_id: str) -> Dict[str, Any]:
        """Create quality filter dropdown component."""
        if not DASH_AVAILABLE:
            return {
                "id": component_id,
                "options": [
                    {"label": "All Data", "value": "all"},
                    {"label": "High Quality (90+)", "value": "high"},
                    {"label": "Medium Quality (70-89)", "value": "medium"},
                    {"label": "Verified Only", "value": "verified"},
                ],
                "value": "all",
            }

        return dcc.Dropdown(
            id=component_id,
            options=[
                {"label": "All Data", "value": "all"},
                {"label": "High Quality (90+)", "value": "high"},
                {"label": "Medium Quality (70-89)", "value": "medium"},
                {"label": "Verified Only", "value": "verified"},
                {"label": "Exclude Failed", "value": "exclude_failed"},
            ],
            value="all",
            placeholder="Select quality filter...",
        )

    def apply_filter_chain(
        self, data: pd.DataFrame, filters: Dict[str, Any]
    ) -> pd.DataFrame:
        """Apply multiple filters in sequence."""
        result = data.copy()

        # Apply quality score filter
        if "quality_score" in filters and filters["quality_score"] is not None:
            result = self.filter_by_quality(result, filters["quality_score"])

        # Apply verification status filter
        if "verification_status" in filters and filters["verification_status"]:
            result = self.filter_by_status(result, filters["verification_status"])

        # Apply custom filters
        for key, value in filters.items():
            if (
                key not in ["quality_score", "verification_status"]
                and value is not None
            ):
                if key in result.columns:
                    if isinstance(value, list):
                        result = result[result[key].isin(value)]
                    else:
                        result = result[result[key] == value]

        return result

    def get_quality_badges(self, data: pd.DataFrame) -> List[Dict[str, str]]:
        """Generate quality badges for data points."""
        badges = []

        if "quality_score" not in data.columns:
            return badges

        for _, row in data.iterrows():
            score = row.get("quality_score", 0)

            if score >= 90:
                color = "success"
                text = "High Quality"
            elif score >= 70:
                color = "warning"
                text = "Medium Quality"
            elif score >= 50:
                color = "info"
                text = "Low Quality"
            else:
                color = "danger"
                text = "Failed"

            badges.append(
                {"color": color, "text": f"{text} ({score:.0f}%)", "score": score}
            )

        return badges


class DateRangeSelector:
    """Date range selector with data freshness indicators."""

    def __init__(self):
        """Initialize date range selector."""
        self.presets = self._create_preset_ranges()

    def create_date_range_picker(self, component_id: str) -> Dict[str, Any]:
        """Create date range picker component."""
        today = datetime.now().date()

        if not DASH_AVAILABLE:
            return {
                "id": component_id,
                "start_date": (today - timedelta(days=30)).isoformat(),
                "end_date": today.isoformat(),
                "display_format": "YYYY-MM-DD",
            }

        return dcc.DatePickerRange(
            id=component_id,
            start_date=today - timedelta(days=30),
            end_date=today,
            display_format="YYYY-MM-DD",
            style={"marginBottom": "10px"},
        )

    def filter_by_date_range(
        self, data: pd.DataFrame, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """Filter data by date range."""
        if "date" not in data.columns:
            logger.warning("No date column found, returning all data")
            return data

        # Ensure date column is datetime
        data["date"] = pd.to_datetime(data["date"])

        mask = (data["date"] >= start_date) & (data["date"] <= end_date)
        return data[mask].copy()

    def calculate_freshness(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate data freshness metrics."""
        if "last_updated" not in data.columns and "date" not in data.columns:
            return {"days_old": -1, "freshness_score": 0, "status": "unknown"}

        # Use last_updated if available, otherwise use date
        date_col = "last_updated" if "last_updated" in data.columns else "date"
        latest_date = pd.to_datetime(data[date_col]).max()

        if pd.isna(latest_date):
            return {"days_old": -1, "freshness_score": 0, "status": "unknown"}

        days_old = (datetime.now() - latest_date).days

        # Calculate freshness score (100 = today, 0 = 30+ days old)
        freshness_score = max(0, min(100, 100 - (days_old * 3.33)))

        # Determine status
        if days_old <= 1:
            status = FreshnessStatus.FRESH.value
        elif days_old <= 7:
            status = FreshnessStatus.RECENT.value
        elif days_old <= 30:
            status = FreshnessStatus.STALE.value
        else:
            status = FreshnessStatus.OUTDATED.value

        return {
            "days_old": days_old,
            "freshness_score": freshness_score,
            "status": status,
            "latest_date": latest_date.isoformat(),
        }

    def create_freshness_indicator(self, data: pd.DataFrame) -> Dict[str, str]:
        """Create freshness indicator component."""
        freshness = self.calculate_freshness(data)

        color_map = {
            FreshnessStatus.FRESH.value: "success",
            FreshnessStatus.RECENT.value: "info",
            FreshnessStatus.STALE.value: "warning",
            FreshnessStatus.OUTDATED.value: "danger",
        }

        icon_map = {
            FreshnessStatus.FRESH.value: "✓",
            FreshnessStatus.RECENT.value: "⚡",
            FreshnessStatus.STALE.value: "⚠",
            FreshnessStatus.OUTDATED.value: "✗",
        }

        return {
            "color": color_map.get(freshness["status"], "secondary"),
            "text": f"Data freshness: {freshness['days_old']} days old",
            "icon": icon_map.get(freshness["status"], "?"),
            "score": freshness["freshness_score"],
        }

    def get_preset_ranges(self) -> Dict[str, Tuple[datetime, datetime]]:
        """Get preset date range options."""
        return self.presets

    def _create_preset_ranges(self) -> Dict[str, Tuple[datetime, datetime]]:
        """Create preset date ranges."""
        today = datetime.now().date()

        return {
            "Last 7 Days": (today - timedelta(days=7), today),
            "Last 30 Days": (today - timedelta(days=30), today),
            "Last 90 Days": (today - timedelta(days=90), today),
            "Year to Date": (datetime(today.year, 1, 1).date(), today),
            "Last Year": (
                datetime(today.year - 1, 1, 1).date(),
                datetime(today.year - 1, 12, 31).date(),
            ),
            "All Time": (datetime(2000, 1, 1).date(), today),
        }


class DataFreshnessIndicator:
    """Data freshness indicator component."""

    def __init__(self):
        """Initialize freshness indicator."""
        self.freshness_thresholds = {
            "fresh": 1,  # 1 day
            "recent": 7,  # 7 days
            "stale": 30,  # 30 days
        }

    def calculate_age(self, last_update: datetime) -> Dict[str, Any]:
        """Calculate data age from last update."""
        if not isinstance(last_update, datetime):
            last_update = pd.to_datetime(last_update)

        age = datetime.now() - last_update
        days = age.days
        hours = age.seconds // 3600

        if days <= self.freshness_thresholds["fresh"]:
            status = "fresh"
        elif days <= self.freshness_thresholds["recent"]:
            status = "recent"
        elif days <= self.freshness_thresholds["stale"]:
            status = "stale"
        else:
            status = "outdated"

        return {
            "days": days,
            "hours": hours,
            "status": status,
            "last_update": last_update.isoformat(),
        }

    def get_freshness_color(self, days_old: int) -> str:
        """Get color code based on data age."""
        if days_old <= self.freshness_thresholds["fresh"]:
            return "success"
        elif days_old <= self.freshness_thresholds["recent"]:
            return "warning"
        else:
            return "danger"

    def create_freshness_badge(self, last_update: datetime) -> Dict[str, str]:
        """Create freshness badge component."""
        age_info = self.calculate_age(last_update)

        if age_info["days"] == 0:
            text = f"Updated {age_info['hours']} hours ago"
        else:
            text = f"Updated {age_info['days']} days ago"

        return {
            "color": self.get_freshness_color(age_info["days"]),
            "text": text,
            "status": age_info["status"],
        }


class FilterChain:
    """Chain multiple filters together."""

    def __init__(self):
        """Initialize filter chain."""
        self.filters = {}

    def add_filter(self, name: str, filter_func: callable):
        """Add filter to chain."""
        self.filters[name] = filter_func

    def remove_filter(self, name: str):
        """Remove filter from chain."""
        if name in self.filters:
            del self.filters[name]

    def apply(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply all filters in chain."""
        result = data

        for name, filter_func in self.filters.items():
            try:
                result = filter_func(result)
                logger.debug(f"Applied filter '{name}', rows: {len(result)}")
            except Exception as e:
                logger.error(f"Error applying filter '{name}': {e}")

        return result

    def clear(self):
        """Clear all filters."""
        self.filters = {}


# Export main components
__all__ = [
    "QualityFilter",
    "DateRangeSelector",
    "DataFreshnessIndicator",
    "FilterChain",
]
