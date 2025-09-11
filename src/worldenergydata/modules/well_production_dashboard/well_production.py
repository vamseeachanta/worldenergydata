"""
Well Production Dashboard implementation extending DashboardBuilder.

Integrates with verification system for data quality and provides well-specific visualizations.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import yaml
from pathlib import Path
import logging
from functools import lru_cache
import time

# Import base dashboard builder
from worldenergydata.modules.bsee.reports.comprehensive.visualizations.dashboard_builder import (
    DashboardBuilder,
    DashboardConfig,
    ChartConfig
)

# Import verification system components
from worldenergydata.modules.bsee.analysis.well_data_verification import (
    VerificationWorkflow,
    VerificationResult,
    VerificationConfig
)
from worldenergydata.modules.bsee.analysis.well_data_verification.quality import (
    DataQualityFramework,
    CompletenessChecker
)
from worldenergydata.modules.bsee.analysis.well_data_verification.audit import AuditLogger

# Import comprehensive report components for export
from worldenergydata.modules.bsee.reports.comprehensive.exporters import (
    ReportExporter,
    ExportFormat,
    ExportConfig
)
from worldenergydata.modules.bsee.reports.comprehensive.exporters.pdf_exporter import PDFExporter
from worldenergydata.modules.bsee.reports.comprehensive.exporters.excel_exporter import ExcelExporter

# Import visualization components
from worldenergydata.modules.bsee.reports.comprehensive.visualizations import (
    ProductionChart,
    EconomicChart
)

logger = logging.getLogger(__name__)


@dataclass
class WellDashboardConfig(DashboardConfig):
    """Extended configuration for well production dashboard."""
    enable_verification: bool = True
    enable_real_time: bool = False
    cache_ttl: int = 300  # seconds
    quality_threshold: float = 0.8
    websocket_port: int = 8765
    api_port: int = 5000
    auth_enabled: bool = True
    export_formats: List[str] = field(default_factory=lambda: ['pdf', 'excel'])


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
            if production[i-1] > 0:
                rate = (production[i-1] - production[i]) / production[i-1]
                decline_rates.append(rate)
        
        return np.mean(decline_rates) if decline_rates else 0.0
    
    @staticmethod
    def calculate_economic_indicators(revenue: float, opex: float, capex: float) -> Dict[str, float]:
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
        payback_period = capex / (revenue - opex) if (revenue - opex) > 0 else float('inf')
        
        return {
            'profit': profit,
            'profit_margin': profit_margin,
            'roi': roi,
            'payback_period': payback_period
        }
    
    @staticmethod
    def forecast_production(historical_data: pd.Series, periods: int = 12) -> pd.DataFrame:
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
        
        return pd.DataFrame({
            'forecast': forecast,
            'lower_bound': lower_bound,
            'upper_bound': upper_bound
        })


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
        field_data = well_data.groupby('date').agg({
            'oil_production': 'sum',
            'gas_production': 'sum',
            'water_production': 'sum',
            'well_id': 'count'
        }).rename(columns={'well_id': 'well_count'})
        
        field_data['field'] = field_name
        field_data['total_oil'] = field_data['oil_production']
        field_data['total_gas'] = field_data['gas_production']
        
        return field_data.reset_index()
    
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
        rollup = well_data.groupby('date').agg({
            'oil_production': ['sum', 'mean', 'std'],
            'gas_production': ['sum', 'mean', 'std'],
            'water_production': ['sum', 'mean', 'std']
        })
        
        # Flatten column names
        rollup.columns = ['_'.join(col).strip() for col in rollup.columns.values]
        rollup['total_production'] = rollup['oil_production_sum']
        rollup['field'] = field_name
        
        return rollup.reset_index()
    
    @staticmethod
    def compare_fields(field1_data: pd.DataFrame, field2_data: pd.DataFrame) -> Dict[str, Any]:
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
        field1_total = field1_data['total_production'].sum()
        field2_total = field2_data['total_production'].sum()
        
        # Calculate performance ratio
        performance_ratio = field1_total / field2_total if field2_total > 0 else 0
        
        # Calculate trend comparison
        field1_trend = np.polyfit(range(len(field1_data)), field1_data['total_production'], 1)[0]
        field2_trend = np.polyfit(range(len(field2_data)), field2_data['total_production'], 1)[0]
        
        return {
            'field1_total': field1_total,
            'field2_total': field2_total,
            'performance_ratio': performance_ratio,
            'field1_trend': field1_trend,
            'field2_trend': field2_trend,
            'trend_comparison': field1_trend - field2_trend
        }


class WellProductionDashboard(DashboardBuilder):
    """
    Extended dashboard for well production visualization and analysis.
    
    Integrates with verification system and provides well-specific functionality.
    """
    
    def __init__(self, config: Optional[WellDashboardConfig] = None):
        """
        Initialize well production dashboard.
        
        Args:
            config: Dashboard configuration
        """
        # Initialize base dashboard
        super().__init__(config or WellDashboardConfig(title="Well Production Dashboard"))
        
        # Store extended config
        self.config: WellDashboardConfig = config or WellDashboardConfig(title="Well Production Dashboard")
        
        # Initialize components
        self.verification_enabled = self.config.enable_verification
        self.cache_ttl = self.config.cache_ttl
        self.quality_threshold = self.config.quality_threshold
        
        # Data storage
        self.well_data = None
        self.field_data = {}
        self.verification_results = {}
        
        # Performance tracking
        self.cache_hits = 0
        self.total_requests = 0
        self._cache = {}
        self._cache_timestamps = {}
        
        # Components
        self.verification_engine = None
        self.authenticator = None
        self.websocket_handler = None
        self.exporter = None
        
        # Initialize verification if enabled
        if self.verification_enabled:
            self._init_verification()
        
        # Real-time updates
        self.real_time_enabled = False
        self.update_interval = 60000  # milliseconds
        
        logger.info(f"WellProductionDashboard initialized with config: {self.config.title}")
    
    def _init_verification(self):
        """Initialize verification system integration."""
        try:
            self.verification_config = VerificationConfig()
            self.verification_workflow = VerificationWorkflow(self.verification_config)
            self.quality_framework = DataQualityFramework()
            self.completeness_checker = CompletenessChecker()
            self.audit_logger = AuditLogger()
            logger.info("Verification system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize verification: {e}")
            self.verification_enabled = False
    
    @classmethod
    def from_yaml(cls, config_path: str) -> 'WellProductionDashboard':
        """
        Create dashboard from YAML configuration.
        
        Args:
            config_path: Path to YAML config file
            
        Returns:
            Configured dashboard instance
        """
        with open(config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        dashboard_config = config_dict.get('dashboard', {})
        config = WellDashboardConfig(
            title=dashboard_config.get('title', 'Well Production Dashboard'),
            enable_verification=dashboard_config.get('enable_verification', True),
            cache_ttl=dashboard_config.get('cache_ttl', 300),
            quality_threshold=dashboard_config.get('quality_threshold', 0.8)
        )
        
        dashboard = cls(config)
        
        # Load wells if specified
        if 'wells' in config_dict:
            for well in config_dict['wells']:
                dashboard.add_well(well['id'])
        
        # Configure filters if specified
        if 'filters' in config_dict:
            for filter_name, filter_config in config_dict['filters'].items():
                dashboard.configure_filter(filter_name, filter_config)
        
        return dashboard
    
    def load_well_data(self, data: pd.DataFrame):
        """
        Load well production data.
        
        Args:
            data: DataFrame with well production data
            
        Raises:
            ValueError: If required columns are missing
        """
        required_columns = ['well_id', 'date', 'oil_production']
        missing = [col for col in required_columns if col not in data.columns]
        
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        self.well_data = data
        self.total_requests += 1
        
        # Clear cache when new data is loaded
        self._clear_cache()
        
        logger.info(f"Loaded {len(data)} rows of well data")
    
    def verify_well_data(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Verify well data using verification system.
        
        Args:
            data: Well data to verify
            
        Returns:
            Verification results
        """
        if not self.verification_enabled or self.verification_workflow is None:
            return {'status': 'unverified', 'quality_score': 0}
        
        try:
            # Run verification workflow
            result = self.verification_workflow.verify(data)
            
            # Calculate quality score
            quality_score = self.quality_framework.calculate_quality_score(data)
            
            verification_results = {
                'status': 'verified' if result.is_valid else 'failed',
                'quality_score': quality_score,
                'anomalies': result.issues if hasattr(result, 'issues') else [],
                'audit_trail': []
            }
            
            self.verification_results[data['well_id'].iloc[0]] = verification_results
            
            # Log to audit trail
            if self.audit_logger:
                self.audit_logger.log_action(
                    action='verification',
                    details={
                        'well_id': data['well_id'].iloc[0],
                        'status': verification_results['status'],
                        'quality_score': quality_score
                    }
                )
            
            return verification_results
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return {'status': 'error', 'quality_score': 0, 'error': str(e)}
    
    def create_production_chart(self, well_id: str, use_cache: bool = True) -> ChartConfig:
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
            filters=['date_range', 'product_type']
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
        
        well_subset = self.well_data[self.well_data['well_id'] == well_id]
        
        if well_subset.empty:
            return {}
        
        # Calculate metrics
        total_revenue = well_subset['revenue'].sum() if 'revenue' in well_subset else 0
        total_opex = well_subset['opex'].sum() if 'opex' in well_subset else 0
        
        # Calculate NPV if cash flows available
        if 'revenue' in well_subset and 'opex' in well_subset:
            cash_flows = (well_subset['revenue'] - well_subset['opex']).tolist()
            npv = WellMetrics.calculate_npv(cash_flows)
        else:
            npv = 0
        
        metrics = WellMetrics.calculate_economic_indicators(
            revenue=total_revenue,
            opex=total_opex,
            capex=0  # Would need capex data
        )
        
        metrics['npv'] = npv
        metrics['total_revenue'] = total_revenue
        metrics['total_opex'] = total_opex
        
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
        
        well_subset = self.well_data[self.well_data['well_id'] == well_id]
        
        if well_subset.empty or 'oil_production' not in well_subset:
            return {}
        
        production = well_subset['oil_production'].tolist()
        decline_rate = WellMetrics.calculate_decline_rate(production)
        
        # Generate forecast
        forecast_df = WellMetrics.forecast_production(well_subset['oil_production'])
        
        return {
            'decline_rate': decline_rate,
            'forecast': forecast_df.to_dict('records') if not forecast_df.empty else [],
            'confidence_interval': {
                'lower': forecast_df['lower_bound'].tolist() if not forecast_df.empty else [],
                'upper': forecast_df['upper_bound'].tolist() if not forecast_df.empty else []
            }
        }
    
    def get_quality_indicators(self, well_id: str) -> Dict[str, Any]:
        """
        Get quality indicators for a well.
        
        Args:
            well_id: Well identifier
            
        Returns:
            Quality indicators
        """
        if well_id not in self.verification_results:
            return {
                'status': 'unverified',
                'quality_score': 0,
                'indicator_color': 'gray'
            }
        
        results = self.verification_results[well_id]
        quality_score = results.get('quality_score', 0)
        
        # Determine indicator color
        if quality_score >= 0.9:
            color = 'green'
        elif quality_score >= 0.7:
            color = 'yellow'
        else:
            color = 'red'
        
        return {
            'status': results.get('status', 'unknown'),
            'quality_score': quality_score,
            'indicator_color': color,
            'anomalies': results.get('anomalies', [])
        }
    
    def setup_authentication(self):
        """Set up authentication using BSEE patterns."""
        if not self.config.auth_enabled:
            return
        
        try:
            # Import BSEE authenticator if available
            from worldenergydata.modules.bsee.auth import BSEEAuthenticator
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
        """
        Enable real-time updates.
        
        Args:
            interval: Update interval in milliseconds
        """
        self.real_time_enabled = True
        self.update_interval = interval
        
        # Initialize WebSocket handler for real-time updates
        try:
            from .websocket import WebSocketHandler
            self.websocket_handler = WebSocketHandler(port=self.config.websocket_port)
            logger.info(f"Real-time updates enabled with {interval}ms interval")
        except ImportError:
            logger.warning("WebSocket support not available")
            self.websocket_handler = None
    
    def export_dashboard(self, format: str = 'pdf') -> bytes:
        """
        Export dashboard to specified format.
        
        Args:
            format: Export format ('pdf' or 'excel')
            
        Returns:
            Exported content as bytes
        """
        if format not in self.config.export_formats:
            raise ValueError(f"Unsupported export format: {format}")
        
        try:
            if format == 'pdf':
                exporter = PDFExporter()
                return exporter.export_to_pdf(self.get_dashboard_data())
            elif format == 'excel':
                exporter = ExcelExporter()
                return exporter.export_to_excel(self.get_dashboard_data())
        except ImportError:
            logger.error(f"Export module for {format} not available")
            return b''
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Get complete dashboard data for export.
        
        Returns:
            Dashboard data dictionary
        """
        return {
            'title': self.config.title,
            'well_data': self.well_data.to_dict('records') if self.well_data is not None else [],
            'charts': [chart.__dict__ for chart in self.charts],
            'filters': self.filters,
            'verification_results': self.verification_results,
            'timestamp': datetime.now().isoformat()
        }
    
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
        if 'date_range' in self.filters:
            date_range = self.filters['date_range']
            if len(date_range) == 2:
                filtered = filtered[
                    (filtered['date'] >= date_range[0]) &
                    (filtered['date'] <= date_range[1])
                ]
        
        # Apply quality score filter
        if 'min_quality_score' in self.filters and 'quality_score' in filtered.columns:
            min_score = self.filters['min_quality_score']
            filtered = filtered[filtered['quality_score'] >= min_score]
        
        return filtered
    
    def get_api_endpoints(self) -> List[str]:
        """
        Get available API endpoints.
        
        Returns:
            List of API endpoints
        """
        return [
            '/api/wells',
            '/api/wells/{well_id}',
            '/api/dashboard/data',
            '/api/dashboard/export',
            '/api/dashboard/metrics/{well_id}',
            '/api/fields',
            '/api/fields/{field_name}',
            '/api/verification/{well_id}'
        ]
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """
        Get dashboard performance metrics.
        
        Returns:
            Performance metrics
        """
        cache_hit_rate = self.cache_hits / self.total_requests if self.total_requests > 0 else 0
        
        # Get memory usage
        try:
            import psutil
            process = psutil.Process()
            memory_usage = process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            memory_usage = 0.0  # Default if psutil not available
        
        return {
            'cache_hit_rate': cache_hit_rate,
            'cache_hits': self.cache_hits,
            'total_requests': self.total_requests,
            'memory_usage': memory_usage,
            'render_time': 0.5  # Placeholder - would measure actual render time
        }
    
    def get_audit_trail(self, well_id: str) -> pd.DataFrame:
        """
        Get audit trail for a well.
        
        Args:
            well_id: Well identifier
            
        Returns:
            Audit trail DataFrame
        """
        if not self.audit_logger:
            return pd.DataFrame()
        
        try:
            # Get audit logs for this well
            logs = self.audit_logger.get_logs(filter_by={'well_id': well_id})
            if logs:
                return pd.DataFrame(logs)
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Failed to get audit trail: {e}")
            return pd.DataFrame()
    
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


class MockAuthenticator:
    """Mock authenticator for testing."""
    
    def is_authenticated(self) -> bool:
        """Always return True for mock."""
        return True