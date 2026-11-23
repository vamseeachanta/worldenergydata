"""
Base types, enums, and configuration for interactive dashboard components.

This module provides shared types and configuration used across all component modules.
"""

import logging
from dataclasses import dataclass
from enum import Enum

# Optional imports with fallback
try:
    import plotly.graph_objs as go
    from plotly.subplots import make_subplots

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    go = None
    make_subplots = None

try:
    import dash  # noqa: F401
    import dash_bootstrap_components as dbc
    from dash import Input, Output, State, callback_context, dcc, html

    DASH_AVAILABLE = True
except ImportError:
    DASH_AVAILABLE = False
    dcc = html = Input = Output = State = callback_context = dbc = None

logger = logging.getLogger(__name__)


class QualityLevel(Enum):
    """Quality level enumeration."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    FAILED = "failed"


class FreshnessStatus(Enum):
    """Data freshness status."""

    FRESH = "fresh"
    RECENT = "recent"
    STALE = "stale"
    OUTDATED = "outdated"


@dataclass
class FilterConfig:
    """Configuration for filters."""

    quality_threshold: int = 70
    freshness_days: int = 7
    anomaly_threshold: float = 3.0
    date_format: str = "YYYY-MM-DD"


# Export main components
__all__ = [
    "QualityLevel",
    "FreshnessStatus",
    "FilterConfig",
    "PLOTLY_AVAILABLE",
    "DASH_AVAILABLE",
    "go",
    "make_subplots",
    "dcc",
    "html",
    "dbc",
    "Input",
    "Output",
    "State",
    "callback_context",
    "logger",
]
