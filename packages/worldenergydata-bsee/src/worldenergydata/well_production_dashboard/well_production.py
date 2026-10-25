"""
Well Production Dashboard implementation extending DashboardBuilder.

Integrates with verification system for data quality and provides well-specific visualizations.
"""

import time
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import yaml

from worldenergydata.bsee.reports.comprehensive.visualizations.dashboard_builder import (
    ChartConfig,
    DashboardBuilder,
    DashboardConfig,
)
from worldenergydata.common import get_logger
from worldenergydata.well_production_dashboard.cache_config import (
    DashboardCacheManager,
)
from worldenergydata.well_production_dashboard.export_manager import (
    ExportConfiguration,
    ExportResult,
    VerificationMetadata,
    WellDashboardExportManager,
)
from worldenergydata.well_production_dashboard.query_optimizer import (
    QueryOptimizer,
)
from worldenergydata.well_production_dashboard.verification_adapter import (
    DashboardVerification,
    valid_score,
)

logger = get_logger(__name__)

# Import verification system components

# Import comprehensive report components for export

# Import base dashboard builder

# Import cache configuration

# Import export manager for dashboard exports

# Import query optimizer for BSEE data loader integration

# Import visualization components
# Note: logger is already defined at line 18 using get_logger


@dataclass
class WellDashboardConfig(DashboardConfig):
    """Extended configuration for well production dashboard."""

    enable_verification: bool = True
    audit_db_path: Optional[str] = None
    enable_real_time: bool = False
    cache_ttl: int = 300  # seconds
    quality_threshold: float = 0.8
    websocket_port: int = 8765
    api_port: int = 5000
    auth_enabled: bool = True
    export_formats: List[str] = field(default_factory=lambda: ["pdf", "excel"])


class WellMetrics:
    """Calculator for well-specific metrics and KPIs."""

    @staticmethod
    def calculate_npv(cash_flows: List[float], discount_rate: float = 0.1) -> float:
        """
        Calculate Net Present Value.

        Args:
            cash_flows: List of cash flows by period
            discount_rate: Discount rate (default 10%)

        Returns:
            NPV value
        """
        npv = 0
        for i, cf in enumerate(cash_flows):
            npv += cf / ((1 + discount_rate) ** i)
        return npv

    @staticmethod
    def calculate_decline_rate(production: List[float]) -> float:
        """
        Calculate production decline rate.

        Args:
            production: List of production values over time

        Returns:
            Decline rate as a fraction
        """
        if len(production) < 2:
            return 0.0

        # Calculate average decline rate
        decline_rates = []
        for i in range(1, len(production)):
            if production[i - 1] > 0:
                rate = (production[i - 1] - production[i]) / production[i - 1]
                decline_rates.append(rate)

        return np.mean(decline_rates) if decline_rates else 0.0

    @staticmethod
    def calculate_economic_indicators(
        revenue: float, opex: float, capex: float
    ) -> Dict[str, float]:
        """
        Calculate economic indicators.

        Args:
            revenue: Total revenue
            opex: Operating expenses
            capex: Capital expenses

        Returns:
            Dictionary of economic indicators
        """
        profit = revenue - opex - capex
        profit_margin = profit / revenue if revenue > 0 else 0
        roi = profit / capex if capex > 0 else 0
        payback_period = (
            capex / (revenue - opex) if (revenue - opex) > 0 else float("inf")
        )

        return {
            "profit": profit,
            "profit_margin": profit_margin,
            "roi": roi,
            "payback_period": payback_period,
        }

    @staticmethod
    def forecast_production(
        historical_data: pd.Series, periods: int = 12
    ) -> pd.DataFrame:
        """
        Forecast future production based on historical data.

        Args:
            historical_data: Historical production data
            periods: Number of periods to forecast

        Returns:
            DataFrame with forecast and confidence intervals
        """
        # Simple exponential decline model
        if len(historical_data) < 3:
            return pd.DataFrame()

        # Fit exponential decline
        x = np.arange(len(historical_data))
        y = historical_data.values

        # Log transform for linear regression
        log_y = np.log(y + 1)  # Add 1 to avoid log(0)
        coeffs = np.polyfit(x, log_y, 1)

        # Generate forecast
        future_x = np.arange(len(historical_data), len(historical_data) + periods)
        forecast = np.exp(coeffs[0] * future_x + coeffs[1]) - 1

        # Simple confidence intervals (±20%)
        lower_bound = forecast * 0.8
        upper_bound = forecast * 1.2

        return pd.DataFrame(
            {
                "forecast": forecast,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
            }
        )


class FieldAggregator:
    """Aggregates well data to field level."""

    @staticmethod
    def aggregate_field_data(well_data: pd.DataFrame, field_name: str) -> pd.DataFrame:
        """
        Aggregate well data to field level.

        Args:
            well_data: DataFrame with well production data
            field_name: Name of the field

        Returns:
            Aggregated field data
        """
        if well_data.empty:
            return pd.DataFrame()

        # Group by date and aggregate
        field_data = (
            well_data.groupby("date")
            .agg(
                {
                    "oil_production": "sum",
                    "gas_production": "sum",
                    "water_production": "sum",
                    "well_id": "count",
                }
            )
            .rename(columns={"well_id": "well_count"})
        )

        field_data["field"] = field_name
        field_data["total_oil"] = field_data["oil_production"]
        field_data["total_gas"] = field_data["gas_production"]

        return field_data.reset_index()

    def aggregate_field_production(self, field_name: str) -> pd.DataFrame:
        """Backward-compatible field production aggregation helper."""
        field_payload = (
            self.get_field_data(field_name) if hasattr(self, "get_field_data") else None
        )
        if isinstance(field_payload, dict):
            field_entry = field_payload.get(field_name, field_payload)
            if isinstance(field_entry, dict):
                production_data = field_entry.get("production")
            else:
                production_data = field_entry
        else:
            production_data = field_payload

        if production_data is None:
            return pd.DataFrame()
        if not isinstance(production_data, pd.DataFrame):
            production_data = pd.DataFrame(production_data)
        return self.aggregate_field_data(production_data, field_name)

    @staticmethod
    def rollup_field_data(well_data: pd.DataFrame, field_name: str) -> pd.DataFrame:
        """
        Rollup well data with additional statistics.

        Args:
            well_data: DataFrame with well production data
            field_name: Name of the field

        Returns:
            Rolled up field data
        """
        if well_data.empty:
            return pd.DataFrame()

        # Group by date
        rollup = well_data.groupby("date").agg(
            {
                "oil_production": ["sum", "mean", "std"],
                "gas_production": ["sum", "mean", "std"],
                "water_production": ["sum", "mean", "std"],
            }
        )

        # Flatten column names
        rollup.columns = ["_".join(col).strip() for col in rollup.columns.values]
        rollup["total_production"] = rollup["oil_production_sum"]
        rollup["field"] = field_name

        return rollup.reset_index()

    @staticmethod
    def compare_fields(
        field1_data: pd.DataFrame, field2_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Compare performance between two fields.

        Args:
            field1_data: First field data
            field2_data: Second field data

        Returns:
            Comparison metrics
        """
        if field1_data.empty or field2_data.empty:
            return {}

        # Calculate total production for each field
        field1_total = field1_data["total_production"].sum()
        field2_total = field2_data["total_production"].sum()

        # Calculate performance ratio
        performance_ratio = field1_total / field2_total if field2_total > 0 else 0

        # Calculate trend comparison
        field1_trend = np.polyfit(
            range(len(field1_data)), field1_data["total_production"], 1
        )[0]
        field2_trend = np.polyfit(
            range(len(field2_data)), field2_data["total_production"], 1
        )[0]

        return {
            "field1_total": field1_total,
            "field2_total": field2_total,
            "performance_ratio": performance_ratio,
            "field1_trend": field1_trend,
            "field2_trend": field2_trend,
            "trend_comparison": field1_trend - field2_trend,
        }


class WellProductionDashboard(DashboardBuilder):
    """
    Extended dashboard for well production visualization and analysis.

    Integrates with verification system and provides well-specific functionality.
    """

    def __init__(
        self,
        config: Optional[WellDashboardConfig] = None,
        config_path: Optional[str] = None,
    ):
        """
        Initialize well production dashboard.

        Args:
            config: Dashboard configuration
            config_path: Optional YAML configuration path. Preserved for
                backward-compatible callers that construct the dashboard
                directly instead of using ``from_yaml``.
        """
        if config is None and config_path:
            config = self._load_dashboard_config(config_path)

        # Initialize base dashboard
        super().__init__(
            config or WellDashboardConfig(title="Well Production Dashboard")
        )

        # Store extended config
        self.config: WellDashboardConfig = config or WellDashboardConfig(
            title="Well Production Dashboard"
        )

        # Initialize components
        self.verification_enabled = self.config.enable_verification
        self.cache_ttl = self.config.cache_ttl
        self.quality_threshold = self.config.quality_threshold

        # Data storage
        self.well_data = None
        self.field_data = {}
        self.verification_results = {}
        self._verification_records = {}
        self._loaded_well_ids = ()
        self._verification_lock = RLock()
        self.verification_workflow = None
        self.quality_framework = None
        self.audit_logger = None
        self._verification = None
        self.verification_reason = "Verification is disabled"

        # Performance tracking
        self.cache_hits = 0
        self.total_requests = 0
        self._cache = {}
        self._cache_timestamps = {}

        # Components
        self.verification_engine = None
        self.query_optimizer = (
            QueryOptimizer()
        )  # Initialize query optimizer for BSEE data
        self.cache_manager = DashboardCacheManager()  # Initialize cache manager
        self.authenticator = None
        self.websocket_handler = None
        self.exporter = None

        # Initialize verification if enabled
        if self.verification_enabled:
            self._init_verification()

        # Real-time updates
        self.real_time_enabled = False
        self.update_interval = 60000  # milliseconds

        logger.info(
            f"WellProductionDashboard initialized with config: {self.config.title}"
        )

    def _init_verification(self):
        """Require explicit audit persistence and the actual validation APIs."""
        if not self.config.audit_db_path:
            self.verification_enabled = False
            self.verification_reason = "An explicit audit database path is required"
            return
        try:
            self._verification = DashboardVerification(
                self.config.audit_db_path, self.quality_threshold
            )
            self._verification_lock = self._verification.lock
            self.verification_workflow = self._verification.workflow
            self.quality_framework = self._verification.quality
            self.audit_logger = self._verification.audit
        except Exception as error:
            self.verification_enabled = False
            self.verification_reason = (
                f"Audit verification initialization failed ({type(error).__name__})"
            )
            logger.error(self.verification_reason)

    @staticmethod
    def _load_dashboard_config(config_path: str) -> WellDashboardConfig:
        """Load dashboard configuration from a YAML file."""
        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f) or {}

        dashboard_config = config_dict.get("dashboard", {}) or {}
        verification_config = config_dict.get("verification", {}) or {}
        audit_path = verification_config.get("audit", {}).get(
            "database", dashboard_config.get("audit_db_path")
        )
        if audit_path and not Path(audit_path).is_absolute():
            audit_path = (Path(config_path).parent / audit_path).as_posix()

        return WellDashboardConfig(
            title=dashboard_config.get("title", "Well Production Dashboard"),
            audit_db_path=audit_path,
            enable_verification=verification_config.get(
                "enabled", dashboard_config.get("enable_verification", True)
            ),
            cache_ttl=dashboard_config.get("cache_ttl", 300),
            quality_threshold=verification_config.get(
                "quality_threshold", dashboard_config.get("quality_threshold", 0.8)
            ),
        )

    @classmethod
    def from_yaml(cls, config_path: str) -> "WellProductionDashboard":
        """
        Create dashboard from YAML configuration.

        Args:
            config_path: Path to YAML config file

        Returns:
            Configured dashboard instance
        """
        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)

        config = cls._load_dashboard_config(config_path)

        dashboard = cls(config)

        # Load wells if specified
        if "wells" in config_dict:
            for well in config_dict["wells"]:
                dashboard.add_well(well["id"])

        # Configure filters if specified
        if "filters" in config_dict:
            for filter_name, filter_config in config_dict["filters"].items():
                dashboard.configure_filter(filter_name, filter_config)

        return dashboard

    @staticmethod
    def _copy_observations(data):
        snapshot = data.copy(deep=True)
        for column in data.select_dtypes(include=["object"]).columns:
            snapshot[column] = data[column].map(deepcopy).astype(data[column].dtype)
        return snapshot

    @staticmethod
    def _requested_ids(well_ids):
        if (
            not isinstance(well_ids, (list, tuple))
            or not well_ids
            or any(
                not isinstance(value, str)
                or not value.strip()
                or value != value.strip()
                for value in well_ids
            )
        ):
            raise ValueError("Requested well identifiers must be nonblank strings")
        return tuple(dict.fromkeys(well_ids))

    @staticmethod
    def _well_identifiers(data):
        if not isinstance(data, pd.DataFrame) or data.empty:
            raise ValueError("Nonempty well observations are required")
        if not data.columns.is_unique or "well_id" not in data:
            raise ValueError("A unique well identifier column is required")
        if (
            not data["well_id"]
            .map(
                lambda value: isinstance(value, str)
                and bool(value.strip())
                and value == value.strip()
            )
            .all()
        ):
            raise ValueError("Nonblank string well identifiers are required")
        return tuple(data["well_id"].unique())

    def load_well_data(
        self,
        data: pd.DataFrame = None,
        well_ids: List[str] = None,
        start_date: datetime = None,
        end_date: datetime = None,
    ):
        """Install complete requested observations and invalidate prior verification."""
        requested = self._requested_ids(well_ids) if well_ids is not None else None
        cache_write = False
        if requested:
            cache_params = {"start_date": str(start_date), "end_date": str(end_date)}
            cache_key = f"wells:{','.join(requested)}"
            data = self.cache_manager.get_well_data(cache_key, cache_params)
            if data is None:
                response = self.query_optimizer.get_dashboard_data_optimized(
                    well_ids=list(requested), start_date=start_date, end_date=end_date
                )
                wells = response.get("wells") if isinstance(response, dict) else None
                if not isinstance(wells, dict) or not wells:
                    raise ValueError("Requested well observations are incomplete")
                if any(not isinstance(frame, pd.DataFrame) for frame in wells.values()):
                    raise ValueError("Requested well observations must be tables")
                data = pd.concat(list(wells.values()), ignore_index=True)
                cache_write = True
            else:
                self.cache_hits += 1
        if not isinstance(data, pd.DataFrame):
            raise ValueError("No well observations were supplied or loaded")
        data = self._copy_observations(data)
        required = ["well_id", "date", "oil_production"]
        missing = [column for column in required if column not in data.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        identifiers = self._well_identifiers(data)
        if requested and set(identifiers) != set(requested):
            raise ValueError("Requested well observations are incomplete")
        if cache_write:
            self.cache_manager.cache_well_data(cache_key, data, cache_params)
        with self._verification_lock:
            self.well_data = data
            self._loaded_well_ids = requested or identifiers
            self.verification_results.clear()
            self._verification_records.clear()
            self.total_requests += 1
            self._clear_cache()
        logger.info(f"Loaded {len(data)} rows of well data")

    def get_well_data(self, well_id: str) -> pd.DataFrame:
        """Return cached production data for a well, if available."""
        if self.well_data is None:
            return pd.DataFrame()
        if "well_id" not in self.well_data.columns:
            return self.well_data.copy()
        return self.well_data[self.well_data["well_id"] == well_id].copy()

    def verify_data_quality(
        self, well_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Every requested well must satisfy the configured quality criterion."""
        with self._verification_lock:
            if not valid_score(self.quality_threshold):
                return {
                    "status": "unverified",
                    "quality_score": None,
                    "results": {},
                    "reason": "A finite quality threshold from zero to one is required",
                }
            if self.well_data is None or self.well_data.empty:
                return {
                    "status": "no_data",
                    "quality_score": None,
                    "results": {},
                    "reason": "No observations are loaded",
                }
            identifiers = self._well_identifiers(self.well_data)
            targets = (
                self._requested_ids(well_ids)
                if well_ids is not None
                else self._loaded_well_ids or identifiers
            )
            results = {}
            for well_id in targets:
                data = self.get_well_data(well_id)
                if data.empty:
                    self.verification_results.pop(well_id, None)
                    self._verification_records.pop(well_id, None)
                    results[well_id] = {"status": "missing", "quality_score": None}
                else:
                    results[well_id] = self.verify_well_data(data)
            verified = bool(results) and all(
                result["status"] == "verified" and valid_score(result["quality_score"])
                for result in results.values()
            )
            return {
                "status": "verified" if verified else "failed",
                "quality_score": (
                    sum(result["quality_score"] for result in results.values())
                    / len(results)
                    if verified
                    else None
                ),
                "quality_threshold": self.quality_threshold,
                "results": results,
            }

    def verify_well_data(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Keep an authoritative copy of assessed observations and persisted results."""
        with self._verification_lock:
            snapshot = (
                self._copy_observations(data)
                if isinstance(data, pd.DataFrame)
                else data
            )
            try:
                identifiers = self._well_identifiers(snapshot)
            except ValueError:
                self.verification_results.clear()
                self._verification_records.clear()
                return {
                    "status": "error",
                    "quality_score": None,
                    "reason": "Nonempty observations with valid well identifiers are required",
                }
            for identifier in identifiers:
                self.verification_results.pop(identifier, None)
                self._verification_records.pop(identifier, None)
            if not self.verification_enabled or self._verification is None:
                return {
                    "status": "unverified",
                    "quality_score": None,
                    "reason": self.verification_reason,
                }
            try:
                if not valid_score(self.quality_threshold):
                    raise ValueError("A finite quality threshold is required")
                self._verification.threshold = self.quality_threshold
                result = self._verification.assess(snapshot)
            except Exception as error:
                result = {
                    "status": "error",
                    "quality_score": None,
                    "quality_threshold": self.quality_threshold,
                    "reason": f"Verification failed ({type(error).__name__})",
                }
            if len(identifiers) == 1:
                well_id = identifiers[0]
                self._verification_records[well_id] = {
                    "observations": snapshot,
                    "result": deepcopy(result),
                }
                self.verification_results[well_id] = deepcopy(result)
            return deepcopy(result)

    def create_production_chart(
        self, well_id: str, use_cache: bool = True
    ) -> ChartConfig:
        """
        Create production timeline chart for a well.

        Args:
            well_id: Well identifier
            use_cache: Whether to use cached results

        Returns:
            Chart configuration
        """
        cache_key = f"production_chart_{well_id}"

        if use_cache and self._is_cached(cache_key):
            self.cache_hits += 1
            return self._get_cached(cache_key)

        chart = ChartConfig(
            chart_id=f"production_{well_id}",
            chart_type="production_timeline",
            title=f"Production Timeline - {well_id}",
            data_source="well_data",
            filters=["date_range", "product_type"],
        )

        if use_cache:
            self._set_cache(cache_key, chart)

        return chart

    def create_economic_metrics(self, well_id: str) -> Dict[str, float]:
        """
        Create economic metrics for a well.

        Args:
            well_id: Well identifier

        Returns:
            Economic metrics dictionary
        """
        if self.well_data is None:
            return {}

        well_subset = self.well_data[self.well_data["well_id"] == well_id]

        if well_subset.empty:
            return {}

        # Calculate metrics
        total_revenue = well_subset["revenue"].sum() if "revenue" in well_subset else 0
        total_opex = well_subset["opex"].sum() if "opex" in well_subset else 0

        # Calculate NPV if cash flows available
        if "revenue" in well_subset and "opex" in well_subset:
            cash_flows = (well_subset["revenue"] - well_subset["opex"]).tolist()
            npv = WellMetrics.calculate_npv(cash_flows)
        else:
            npv = 0

        metrics = WellMetrics.calculate_economic_indicators(
            revenue=total_revenue, opex=total_opex, capex=0  # Would need capex data
        )

        metrics["npv"] = npv
        metrics["total_revenue"] = total_revenue
        metrics["total_opex"] = total_opex

        return metrics

    def create_decline_curve(self, well_id: str) -> Dict[str, Any]:
        """
        Create decline curve analysis for a well.

        Args:
            well_id: Well identifier

        Returns:
            Decline curve analysis results
        """
        if self.well_data is None:
            return {}

        well_subset = self.well_data[self.well_data["well_id"] == well_id]

        if well_subset.empty or "oil_production" not in well_subset:
            return {}

        production = well_subset["oil_production"].tolist()
        decline_rate = WellMetrics.calculate_decline_rate(production)

        # Generate forecast
        forecast_df = WellMetrics.forecast_production(well_subset["oil_production"])

        return {
            "decline_rate": decline_rate,
            "forecast": forecast_df.to_dict("records") if not forecast_df.empty else [],
            "confidence_interval": {
                "lower": (
                    forecast_df["lower_bound"].tolist() if not forecast_df.empty else []
                ),
                "upper": (
                    forecast_df["upper_bound"].tolist() if not forecast_df.empty else []
                ),
            },
        }

    def get_quality_indicators(self, well_id: str) -> Dict[str, Any]:
        """Display only a current assessment against its stated finite criterion."""
        with self._verification_lock:
            result = self._current_verification_result(well_id)
            if result is None:
                return {
                    "status": "unverified",
                    "quality_score": None,
                    "indicator_color": "gray",
                    "quality_threshold": (
                        self.quality_threshold
                        if valid_score(self.quality_threshold)
                        else None
                    ),
                    "reason": "Current observations and quality criterion require verification",
                }
            score = result.get("quality_score")
            if not valid_score(score):
                score, color = None, "gray"
            elif result.get("status") != "verified" or score < self.quality_threshold:
                color = "red"
            else:
                color = "green" if score >= 0.9 else "yellow"
            return {
                "status": result.get("status", "unverified"),
                "quality_score": score,
                "quality_threshold": self.quality_threshold,
                "indicator_color": color,
                "anomalies": result.get("anomalies", []),
            }

    def _current_verification_result(self, well_id, observations=None):
        record = self._verification_records.get(well_id)
        if record is None or not valid_score(self.quality_threshold):
            return None
        result = record["result"]
        if result.get("quality_threshold") != self.quality_threshold:
            return None
        current = self.get_well_data(well_id) if observations is None else observations
        assessed = record["observations"]
        try:
            matches = assessed.reset_index(drop=True).equals(
                current.reset_index(drop=True)
            )
            matches = matches and assessed.attrs == current.attrs
        except (TypeError, ValueError):
            return None
        return deepcopy(result) if matches else None

    def setup_authentication(self):
        """Set up authentication using BSEE patterns."""
        if not self.config.auth_enabled:
            return

        try:
            # Import BSEE authenticator if available
            from worldenergydata.bsee.auth import BSEEAuthenticator

            self.authenticator = BSEEAuthenticator()
            logger.info("Authentication configured")
        except ImportError:
            logger.warning("BSEEAuthenticator not available, using mock authentication")
            self.authenticator = MockAuthenticator()

    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        if self.authenticator:
            return self.authenticator.is_authenticated()
        return True  # Default to authenticated if no authenticator

    def enable_real_time_updates(self, interval: int = 60000):
        """Activate updates only when the optional WebSocket handler is available."""
        if isinstance(interval, bool) or not isinstance(interval, int) or interval <= 0:
            raise ValueError("Update interval must be a positive integer")
        self.real_time_enabled = False
        self.websocket_handler = None
        try:
            from .websocket import WebSocketHandler
        except ImportError as error:
            raise ImportError("WebSocket support is unavailable") from error
        handler = WebSocketHandler(port=self.config.websocket_port)
        self.websocket_handler = handler
        self.update_interval = interval
        self.real_time_enabled = True

    def apply_filters(self) -> pd.DataFrame:
        """
        Apply configured filters to well data.

        Returns:
            Filtered DataFrame
        """
        if self.well_data is None:
            return pd.DataFrame()

        filtered = self.well_data.copy()

        # Apply date range filter
        if "date_range" in self.filters:
            date_range = self.filters["date_range"]
            if len(date_range) == 2:
                filtered = filtered[
                    (filtered["date"] >= date_range[0])
                    & (filtered["date"] <= date_range[1])
                ]

        # Apply quality score filter
        if "min_quality_score" in self.filters and "quality_score" in filtered.columns:
            min_score = self.filters["min_quality_score"]
            filtered = filtered[filtered["quality_score"] >= min_score]

        return filtered

    def get_api_endpoints(self) -> List[str]:
        """
        Get available API endpoints.

        Returns:
            List of API endpoints
        """
        return [
            "/api/wells",
            "/api/wells/{well_id}",
            "/api/dashboard/data",
            "/api/dashboard/export",
            "/api/dashboard/metrics/{well_id}",
            "/api/fields",
            "/api/fields/{field_name}",
            "/api/verification/{well_id}",
        ]

    def get_performance_metrics(self) -> Dict[str, float]:
        """
        Get dashboard performance metrics.

        Returns:
            Performance metrics
        """
        cache_hit_rate = (
            self.cache_hits / self.total_requests if self.total_requests > 0 else 0
        )

        # Get memory usage
        try:
            import psutil

            process = psutil.Process()
            memory_usage = process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            memory_usage = 0.0  # Default if psutil not available

        return {
            "cache_hit_rate": cache_hit_rate,
            "cache_hits": self.cache_hits,
            "total_requests": self.total_requests,
            "memory_usage": memory_usage,
            "render_time": 0.5,  # Placeholder - would measure actual render time
        }

    def get_audit_trail(self, well_id: str) -> pd.DataFrame:
        """Read persisted records; database errors remain visible to the caller."""
        if self._verification is None:
            raise RuntimeError(self.verification_reason)
        return self._verification.history(well_id)

    def add_well(self, well_id: str):
        """Add a well to the dashboard."""
        # Implementation for adding wells
        pass

    def configure_filter(self, filter_name: str, filter_config: Dict):
        """Configure a filter."""
        self.filters[filter_name] = filter_config

    # Cache management methods
    def _is_cached(self, key: str) -> bool:
        """Check if key is in cache and still valid."""
        if key not in self._cache:
            return False

        # Check if cache has expired
        if key in self._cache_timestamps:
            age = time.time() - self._cache_timestamps[key]
            if age > self.cache_ttl:
                del self._cache[key]
                del self._cache_timestamps[key]
                return False

        return True

    def _get_cached(self, key: str) -> Any:
        """Get cached value."""
        return self._cache.get(key)

    def _set_cache(self, key: str, value: Any):
        """Set cache value."""
        self._cache[key] = value
        self._cache_timestamps[key] = time.time()

    def _clear_cache(self):
        """Clear all cache."""
        self._cache.clear()
        self._cache_timestamps.clear()
        self.cache_hits = 0

    # Export functionality methods
    def export_dashboard(
        self, output_path: str, export_config: Optional[ExportConfiguration] = None
    ) -> List[ExportResult]:
        """Export one observation snapshot with matching persisted verification."""
        if export_config is None:
            export_config = ExportConfiguration(
                formats=self.config.export_formats,
                include_verification=self.config.enable_verification,
                include_charts=True,
                include_raw_data=True,
            )
        with self._verification_lock:
            dashboard_data = self.get_dashboard_data()
            if export_config.include_verification:
                dashboard_data["verification_metadata"] = (
                    self._get_verification_metadata(dashboard_data["well_data"])
                )
        if not hasattr(self, "export_manager"):
            self.export_manager = WellDashboardExportManager()
        results = self.export_manager.export_batch(
            dashboard_data, output_path, export_config
        )
        for result in results:
            if result.success:
                logger.info(f"Successfully exported to {result.format}")
            else:
                logger.error(f"Failed to export to {result.format}")
        return results

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Export loaded observations with authoritative, current assessment records."""
        with self._verification_lock:
            results = {
                well_id: self._current_verification_result(well_id)
                or self.get_quality_indicators(well_id)
                for well_id in self._loaded_well_ids
            }
            return {
                "title": self.config.title,
                "well_data": (
                    self._copy_observations(self.well_data)
                    if self.well_data is not None
                    else pd.DataFrame()
                ),
                "well_ids": list(self._loaded_well_ids),
                "charts": [chart.__dict__.copy() for chart in self.charts],
                "filters": deepcopy(self.filters),
                "verification_results": results,
                "timestamp": datetime.now().isoformat(),
            }

    def _get_verification_metadata(self, observations=None) -> VerificationMetadata:
        """Bind exported status to complete scope and exact assessed observations."""
        if not valid_score(self.quality_threshold):
            raise ValueError("A finite quality threshold is required")
        data = self.well_data if observations is None else observations
        if data is None or data.empty:
            raise ValueError("Loaded and verified observations are required")
        identifiers = self._well_identifiers(data)
        if set(identifiers) != set(self._loaded_well_ids):
            raise ValueError("All requested observations must be present and verified")
        results = [
            self._current_verification_result(well_id, data[data["well_id"] == well_id])
            or {}
            for well_id in identifiers
        ]
        if any(
            result.get("status") != "verified"
            or not valid_score(result.get("quality_score"))
            or result["quality_score"] < self.quality_threshold
            or not result.get("audit_trail_id")
            or not isinstance(result.get("verification_date"), datetime)
            for result in results
        ):
            raise ValueError("All loaded observations must be verified before export")
        return VerificationMetadata(
            quality_score=min(result["quality_score"] for result in results),
            verification_date=max(result["verification_date"] for result in results),
            audit_trail_id=",".join(result["audit_trail_id"] for result in results),
            anomalies_detected=sum(len(result["anomalies"]) for result in results),
            data_completeness=min(result["data_completeness"] for result in results),
            verification_status=(
                f"Verified supplied observation data quality; "
                f"score >= {self.quality_threshold:.3f}"
            ),
            data_sources=list(data.attrs.get("sources", [])),
        )

    def export_to_pdf(self, output_path: str) -> ExportResult:
        """
        Export dashboard to PDF format.

        Args:
            output_path: Output file path

        Returns:
            Export result
        """
        config = ExportConfiguration(formats=["pdf"])
        results = self.export_dashboard(output_path.replace(".pdf", ""), config)
        return results[0] if results else ExportResult(success=False, format="pdf")

    def export_to_excel(self, output_path: str) -> ExportResult:
        """
        Export dashboard to Excel format.

        Args:
            output_path: Output file path

        Returns:
            Export result
        """
        config = ExportConfiguration(formats=["excel"])
        results = self.export_dashboard(output_path.replace(".xlsx", ""), config)
        return results[0] if results else ExportResult(success=False, format="excel")

    def export_with_verification(self, output_path: str) -> List[ExportResult]:
        """
        Export dashboard with full verification report.

        Args:
            output_path: Base output path

        Returns:
            List of export results
        """
        config = ExportConfiguration(
            formats=["pdf", "excel"],
            include_verification=True,
            include_charts=True,
            include_raw_data=True,
            include_field_aggregation=True,
        )

        return self.export_dashboard(output_path, config)


class MockAuthenticator:
    """Mock authenticator for testing."""

    def is_authenticated(self) -> bool:
        """Always return True for mock."""
        return True
