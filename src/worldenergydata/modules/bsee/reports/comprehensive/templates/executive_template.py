"""
Executive Template for Comprehensive Report System.

This module provides executive-level reporting with KPIs, strategic metrics,
traffic light indicators, and competitive benchmarking.
"""
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
import json
import numpy as np
import pandas as pd
from enum import Enum

# Import Plotly for visualizations
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

from .base import BaseReportTemplate


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
            'name': self.name,
            'value': float(self.value) if isinstance(self.value, Decimal) else self.value,
            'unit': self.unit,
            'target': float(self.target) if isinstance(self.target, Decimal) else self.target,
            'trend': self.trend,
            'status': self.status,
            'category': self.category,
            'description': self.description,
            'period': self.period,
            'performance': self.get_performance_percentage()
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
            "gray": "#6c757d"
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


class ExecutiveTemplate(BaseReportTemplate):
    """
    Executive template for high-level reporting.
    
    Provides KPIs, strategic metrics, traffic light indicators,
    and competitive benchmarking for executive decision-making.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize executive template."""
        super().__init__(
            template_name="executive",
            template_type="executive",
            version="1.0.0"
        )
        self.config = config or {}
        self.kpi_thresholds = self._load_kpi_thresholds()
        self.benchmarks = self._load_industry_benchmarks()
    
    def _load_kpi_thresholds(self) -> Dict:
        """Load KPI threshold configurations."""
        return self.config.get('kpi_thresholds', {
            'uptime': {'green': 95, 'yellow': 90},
            'efficiency': {'green': 85, 'yellow': 80},
            'safety_trir': {'green': 0.5, 'yellow': 1.0},
            'emissions_intensity': {'green': 15, 'yellow': 20},
            'roi': {'green': 20, 'yellow': 15},
            'npv': {'green': 0, 'yellow': -1000000}
        })
    
    def _load_industry_benchmarks(self) -> Dict:
        """Load industry benchmark data."""
        return self.config.get('benchmarks', {
            'uptime': 92.0,
            'efficiency': 85.0,
            'safety_trir': 0.75,
            'emissions_intensity': 18.0,
            'operating_cost_per_boe': 28.0,
            'finding_cost_per_boe': 15.0
        })
    
    def generate_executive_kpis(self, data: Dict) -> List[ExecutiveKPI]:
        """
        Generate executive KPIs from report data.
        
        Args:
            data: Report data dictionary
            
        Returns:
            List of ExecutiveKPI objects
        """
        kpis = []
        
        # Financial KPIs
        if 'financial' in data:
            fin_data = data['financial']
            
            if 'revenue' in fin_data:
                kpis.append(ExecutiveKPI(
                    name="Revenue",
                    value=fin_data['revenue'],
                    unit="$",
                    target=fin_data.get('revenue_target'),
                    trend=self._calculate_trend(fin_data.get('revenue_history', [])),
                    status=self._determine_financial_status(fin_data['revenue'], fin_data.get('revenue_target')),
                    category="Financial",
                    description="Total revenue for the period"
                ))
            
            if 'ebitda' in fin_data:
                kpis.append(ExecutiveKPI(
                    name="EBITDA",
                    value=fin_data['ebitda'],
                    unit="$",
                    target=fin_data.get('ebitda_target'),
                    trend=self._calculate_trend(fin_data.get('ebitda_history', [])),
                    status=self._determine_financial_status(fin_data['ebitda'], fin_data.get('ebitda_target')),
                    category="Financial",
                    description="Earnings before interest, taxes, depreciation and amortization"
                ))
            
            if 'roi' in fin_data:
                kpis.append(ExecutiveKPI(
                    name="ROI",
                    value=fin_data['roi'],
                    unit="%",
                    target=self.kpi_thresholds.get('roi', {}).get('green', 20),
                    trend=self._calculate_trend(fin_data.get('roi_history', [])),
                    status=self.determine_kpi_status(fin_data['roi'], self.kpi_thresholds.get('roi', {}).get('green', 20)),
                    category="Financial",
                    description="Return on investment"
                ))
        
        # Operational KPIs
        if 'operational' in data:
            ops_data = data['operational']
            
            if 'uptime_percentage' in ops_data:
                kpis.append(ExecutiveKPI(
                    name="Uptime",
                    value=ops_data['uptime_percentage'],
                    unit="%",
                    target=self.kpi_thresholds['uptime']['green'],
                    trend=self._calculate_trend(ops_data.get('uptime_history', [])),
                    status=self.determine_kpi_status(
                        ops_data['uptime_percentage'],
                        self.kpi_thresholds['uptime']['green']
                    ),
                    category="Operational",
                    description="Overall system uptime"
                ))
            
            if 'efficiency_rate' in ops_data:
                kpis.append(ExecutiveKPI(
                    name="Efficiency",
                    value=ops_data['efficiency_rate'],
                    unit="%",
                    target=self.kpi_thresholds['efficiency']['green'],
                    trend=self._calculate_trend(ops_data.get('efficiency_history', [])),
                    status=self.determine_kpi_status(
                        ops_data['efficiency_rate'],
                        self.kpi_thresholds['efficiency']['green']
                    ),
                    category="Operational",
                    description="Production efficiency rate"
                ))
        
        # Production KPIs
        if 'production' in data:
            prod_data = data['production']
            
            if 'total_boe' in prod_data:
                kpis.append(ExecutiveKPI(
                    name="Production Volume",
                    value=prod_data['total_boe'],
                    unit="BOE",
                    target=prod_data.get('production_target'),
                    trend=self._calculate_trend(prod_data.get('production_history', [])),
                    status=self._determine_production_status(prod_data['total_boe'], prod_data.get('production_target')),
                    category="Production",
                    description="Total barrel of oil equivalent production"
                ))
        
        # Safety KPIs
        if 'safety' in data:
            safety_data = data['safety']
            
            if 'trir' in safety_data:
                kpis.append(ExecutiveKPI(
                    name="Safety Score",
                    value=100 - (safety_data['trir'] * 20),  # Convert TRIR to score
                    unit="score",
                    target=95,
                    trend=self._calculate_trend(safety_data.get('trir_history', [])),
                    status=self._determine_safety_status(safety_data['trir']),
                    category="Safety",
                    description="Overall safety performance score"
                ))
        
        # Environmental KPIs
        if 'environmental' in data:
            env_data = data['environmental']
            
            if 'emissions_tons_co2' in env_data:
                kpis.append(ExecutiveKPI(
                    name="Emissions",
                    value=env_data['emissions_tons_co2'],
                    unit="tons CO₂",
                    target=env_data.get('emissions_target', self.kpi_thresholds['emissions_intensity']['green'] * 1000),
                    trend=self._calculate_trend(env_data.get('emissions_history', [])),
                    status=self._determine_emissions_status(env_data['emissions_tons_co2']),
                    category="Environmental",
                    description="Total CO₂ emissions"
                ))
        
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
    
    def _determine_financial_status(self, value: Union[float, Decimal], target: Optional[Union[float, Decimal]]) -> str:
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
    
    def _determine_production_status(self, value: float, target: Optional[float]) -> str:
        """Determine production KPI status."""
        if not target:
            return "gray"
        
        if value >= target:
            return "green"
        elif value >= target * 0.95:
            return "yellow"
        else:
            return "red"
    
    def _determine_safety_status(self, trir: float) -> str:
        """Determine safety KPI status based on TRIR."""
        thresholds = self.kpi_thresholds.get('safety_trir', {})
        
        if trir <= thresholds.get('green', 0.5):
            return "green"
        elif trir <= thresholds.get('yellow', 1.0):
            return "yellow"
        else:
            return "red"
    
    def _determine_emissions_status(self, emissions: float) -> str:
        """Determine emissions KPI status."""
        # Assuming thresholds are per 1000 BOE, scale appropriately
        intensity_threshold_green = self.kpi_thresholds['emissions_intensity']['green'] * 1000
        intensity_threshold_yellow = self.kpi_thresholds['emissions_intensity']['yellow'] * 1000
        
        if emissions <= intensity_threshold_green:
            return "green"
        elif emissions <= intensity_threshold_yellow:
            return "yellow"
        else:
            return "red"
    
    def _calculate_trend(self, history: List[float]) -> str:
        """Calculate trend from historical data."""
        if len(history) < 2:
            return "stable"
        
        # Simple linear trend
        recent = history[-3:] if len(history) >= 3 else history
        if len(recent) < 2:
            return "stable"
        
        avg_change = sum(recent[i] - recent[i-1] for i in range(1, len(recent))) / (len(recent) - 1)
        
        if avg_change > 0.01 * recent[0]:  # More than 1% positive change
            return "up"
        elif avg_change < -0.01 * recent[0]:  # More than 1% negative change
            return "down"
        else:
            return "stable"
    
    def analyze_kpi_trend(self, values: List[float]) -> str:
        """
        Analyze KPI trend over time.
        
        Args:
            values: List of historical values
            
        Returns:
            Trend direction (up/down/stable)
        """
        return self._calculate_trend(values)
    
    def calculate_performance_score(self, kpis: List[ExecutiveKPI]) -> PerformanceScore:
        """
        Calculate overall performance score from KPIs.
        
        Args:
            kpis: List of ExecutiveKPI objects
            
        Returns:
            PerformanceScore object
        """
        category_scores = {}
        category_counts = {}
        
        for kpi in kpis:
            if kpi.target:
                score = min(100, kpi.get_performance_percentage())
                
                if kpi.category not in category_scores:
                    category_scores[kpi.category] = 0
                    category_counts[kpi.category] = 0
                
                category_scores[kpi.category] += score
                category_counts[kpi.category] += 1
        
        # Calculate average score per category
        for category in category_scores:
            if category_counts[category] > 0:
                category_scores[category] = round(
                    category_scores[category] / category_counts[category], 1
                )
        
        # Calculate overall score
        if category_scores:
            overall = round(sum(category_scores.values()) / len(category_scores), 1)
        else:
            overall = 0.0
        
        # Determine trend
        trend = "stable"
        if overall >= 85:
            trend = "up"
        elif overall < 70:
            trend = "down"
        
        return PerformanceScore(
            overall=overall,
            category_scores=category_scores,
            period=datetime.now().strftime("%B %Y"),
            trend=trend
        )
    
    def calculate_strategic_metrics(self, data: Dict) -> List[StrategicMetric]:
        """
        Calculate strategic business metrics.
        
        Args:
            data: Strategic data dictionary
            
        Returns:
            List of StrategicMetric objects
        """
        metrics = []
        
        if 'current_period' in data and 'previous_period' in data:
            current = data['current_period']
            previous = data['previous_period']
            targets = data.get('targets', {})
            
            # Revenue metric
            if 'revenue' in current:
                metrics.append(StrategicMetric(
                    name="Revenue",
                    current_value=current['revenue'],
                    previous_value=previous.get('revenue'),
                    target_value=targets.get('revenue'),
                    unit="$",
                    period="Current Quarter"
                ))
            
            # Market share metric
            if 'market_share' in current:
                metrics.append(StrategicMetric(
                    name="Market Share",
                    current_value=current['market_share'],
                    previous_value=previous.get('market_share'),
                    target_value=targets.get('market_share'),
                    unit="%",
                    period="Current Quarter"
                ))
            
            # ROI metric
            if 'roi' in current:
                metrics.append(StrategicMetric(
                    name="Return on Investment",
                    current_value=current['roi'],
                    previous_value=previous.get('roi'),
                    target_value=targets.get('roi'),
                    unit="%",
                    period="Current Quarter"
                ))
            
            # Production growth metric
            if 'production_growth' in current:
                metrics.append(StrategicMetric(
                    name="Production Growth",
                    current_value=current['production_growth'],
                    previous_value=previous.get('production_growth'),
                    target_value=targets.get('production_growth'),
                    unit="%",
                    period="YoY"
                ))
            
            # Cost reduction metric
            if 'cost_reduction' in current:
                metrics.append(StrategicMetric(
                    name="Cost Reduction",
                    current_value=current['cost_reduction'],
                    previous_value=previous.get('cost_reduction'),
                    target_value=targets.get('cost_reduction'),
                    unit="%",
                    period="YoY"
                ))
        
        return metrics
    
    def compare_with_benchmarks(self, data: Dict, benchmarks: Dict) -> Dict:
        """
        Compare KPIs with industry benchmarks.
        
        Args:
            data: Company data
            benchmarks: Industry benchmark data
            
        Returns:
            Comparison results dictionary
        """
        comparisons = {}
        
        for metric, benchmark_value in benchmarks.items():
            if metric in data.get('operational', {}):
                company_value = data['operational'][metric]
                comparisons[metric] = {
                    'company_value': company_value,
                    'benchmark': benchmark_value,
                    'vs_benchmark': company_value - benchmark_value,
                    'performance': 'above' if company_value > benchmark_value else 'below'
                }
        
        return comparisons
    
    def rank_kpis_by_priority(self, kpis: List[ExecutiveKPI]) -> List[ExecutiveKPI]:
        """
        Rank KPIs by priority.
        
        Args:
            kpis: List of ExecutiveKPI objects
            
        Returns:
            Sorted list of KPIs by priority
        """
        # Define priority weights
        priority_weights = {
            'Revenue': 10,
            'Safety Score': 9,
            'Production Volume': 8,
            'EBITDA': 7,
            'Uptime': 6,
            'ROI': 5,
            'Efficiency': 4,
            'Emissions': 3
        }
        
        # Sort by priority weight, then by performance
        def sort_key(kpi):
            weight = priority_weights.get(kpi.name, 1)
            performance = kpi.get_performance_percentage() if kpi.target else 0
            # Higher weight and lower performance = higher priority
            return (-weight, -performance if kpi.status == "red" else performance)
        
        return sorted(kpis, key=sort_key)
    
    def analyze_year_over_year(self, data: Dict) -> Dict:
        """
        Analyze year-over-year metrics.
        
        Args:
            data: Multi-year data dictionary
            
        Returns:
            YoY analysis results
        """
        years = sorted(data.keys())
        
        if len(years) < 2:
            return {'error': 'Insufficient data for YoY analysis'}
        
        latest_year = years[-1]
        previous_year = years[-2]
        
        # Calculate CAGR if more than 2 years
        cagr = None
        if len(years) > 2 and 'revenue' in data[years[0]] and 'revenue' in data[latest_year]:
            start_value = float(data[years[0]]['revenue'])
            end_value = float(data[latest_year]['revenue'])
            num_years = len(years) - 1
            
            if start_value > 0:
                cagr = ((end_value / start_value) ** (1 / num_years) - 1) * 100
        
        # Determine trend direction
        revenue_trend = []
        for year in years:
            if 'revenue' in data[year]:
                revenue_trend.append(float(data[year]['revenue']))
        
        trend_direction = "stable"
        if len(revenue_trend) >= 2:
            if revenue_trend[-1] > revenue_trend[-2]:
                trend_direction = "growth"
            elif revenue_trend[-1] < revenue_trend[-2]:
                trend_direction = "decline"
        
        # Calculate volatility
        volatility = 0
        if len(revenue_trend) > 1:
            changes = [abs(revenue_trend[i] - revenue_trend[i-1]) / revenue_trend[i-1] 
                      for i in range(1, len(revenue_trend))]
            volatility = sum(changes) / len(changes) * 100
        
        return {
            'cagr': cagr,
            'trend_direction': trend_direction,
            'volatility': volatility,
            'latest_year': latest_year,
            'comparison_year': previous_year
        }
    
    def generate_strategic_forecast(self, historical_data: pd.DataFrame, periods: int = 3) -> Dict:
        """
        Generate strategic forecast.
        
        Args:
            historical_data: Historical data DataFrame
            periods: Number of periods to forecast
            
        Returns:
            Forecast results dictionary
        """
        forecast = {}
        
        # Simple linear trend forecasting
        if 'revenue' in historical_data.columns:
            revenue_values = historical_data['revenue'].values
            x = np.arange(len(revenue_values))
            
            # Linear regression
            z = np.polyfit(x, revenue_values, 1)
            p = np.poly1d(z)
            
            # Generate forecast
            future_x = np.arange(len(revenue_values), len(revenue_values) + periods)
            revenue_forecast = p(future_x).tolist()
            
            # Calculate confidence interval (simplified)
            std_dev = np.std(revenue_values)
            confidence_interval = [(f - std_dev, f + std_dev) for f in revenue_forecast]
            
            forecast['revenue_forecast'] = revenue_forecast
            forecast['confidence_interval'] = confidence_interval
        
        if 'production' in historical_data.columns:
            production_values = historical_data['production'].values
            x = np.arange(len(production_values))
            
            z = np.polyfit(x, production_values, 1)
            p = np.poly1d(z)
            
            future_x = np.arange(len(production_values), len(production_values) + periods)
            production_forecast = p(future_x).tolist()
            
            forecast['production_forecast'] = production_forecast
        
        return forecast
    
    def track_strategic_goals(self, goals: List[Dict]) -> List[Dict]:
        """
        Track strategic goals progress.
        
        Args:
            goals: List of goal dictionaries
            
        Returns:
            List of tracking results
        """
        tracking_results = []
        
        for goal in goals:
            progress = (goal['current'] / goal['target']) * 100 if goal['target'] else 0
            
            # Calculate days remaining
            deadline = datetime.strptime(goal['deadline'], '%Y-%m-%d')
            days_remaining = (deadline - datetime.now()).days
            
            # Determine if on track
            expected_progress = ((datetime.now() - datetime(2024, 1, 1)).days / 
                               (deadline - datetime(2024, 1, 1)).days * 100)
            on_track = progress >= expected_progress * 0.9  # 90% of expected progress
            
            tracking_results.append({
                'name': goal['name'],
                'progress_percentage': round(progress, 1),
                'on_track': on_track,
                'days_remaining': days_remaining,
                'current': goal['current'],
                'target': goal['target'],
                'deadline': goal['deadline']
            })
        
        return tracking_results
    
    def determine_traffic_light_status(self, value: float, green_threshold: float, 
                                      yellow_threshold: float) -> str:
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
    
    def generate_executive_dashboard(self, data: Dict) -> ExecutiveDashboard:
        """
        Generate executive dashboard.
        
        Args:
            data: Dashboard data
            
        Returns:
            ExecutiveDashboard object
        """
        if not PLOTLY_AVAILABLE:
            return ExecutiveDashboard(
                layout={},
                charts=[],
                components={'error': 'Plotly not available'},
                export_config={}
            )
        
        # Create dashboard components
        components = {
            'kpi_grid': self._create_kpi_grid(data.get('kpis', [])),
            'traffic_lights': self._create_traffic_lights(data.get('kpis', [])),
            'trend_charts': self._create_trend_charts(data.get('trends', {}))
        }
        
        # Create charts
        charts = []
        
        # KPI summary chart
        if 'kpis' in data:
            charts.append(self._create_kpi_summary_chart(data['kpis']))
        
        # Trend charts
        if 'trends' in data:
            for metric, values in data['trends'].items():
                if metric != 'periods':
                    charts.append(self._create_trend_chart(metric, values, data['trends'].get('periods', [])))
        
        # Layout configuration
        layout = self.get_dashboard_layout_config()
        
        # Export configuration
        export_config = self.get_dashboard_export_config()
        
        return ExecutiveDashboard(
            layout=layout,
            charts=charts,
            components=components,
            export_config=export_config
        )
    
    def _create_kpi_grid(self, kpis: List[Dict]) -> Dict:
        """Create KPI grid component."""
        return {
            'type': 'grid',
            'kpis': kpis,
            'layout': {
                'rows': 2,
                'cols': 3,
                'spacing': 10
            }
        }
    
    def _create_traffic_lights(self, kpis: List[Dict]) -> List[Dict]:
        """Create traffic light indicators."""
        traffic_lights = []
        
        for kpi in kpis:
            if 'status' in kpi:
                traffic_lights.append({
                    'name': kpi['name'],
                    'status': kpi['status'],
                    'value': kpi.get('value'),
                    'color': self._get_status_color(kpi['status'])
                })
        
        return traffic_lights
    
    def _get_status_color(self, status: str) -> str:
        """Get color for status."""
        colors = {
            'green': '#28a745',
            'yellow': '#ffc107',
            'red': '#dc3545',
            'gray': '#6c757d'
        }
        return colors.get(status, '#6c757d')
    
    def _create_trend_charts(self, trends: Dict) -> List[Dict]:
        """Create trend chart configurations."""
        charts = []
        
        for metric, values in trends.items():
            if metric != 'periods' and isinstance(values, list):
                charts.append({
                    'metric': metric,
                    'values': values,
                    'periods': trends.get('periods', [])
                })
        
        return charts
    
    def _create_kpi_summary_chart(self, kpis: List[Dict]) -> Any:
        """Create KPI summary chart."""
        if not PLOTLY_AVAILABLE:
            return None
        
        categories = []
        values = []
        colors = []
        
        for kpi in kpis[:6]:  # Top 6 KPIs
            categories.append(kpi['name'])
            values.append(kpi.get('value', 0))
            colors.append(self._get_status_color(kpi.get('status', 'gray')))
        
        fig = go.Figure(data=[
            go.Bar(
                x=categories,
                y=values,
                marker_color=colors,
                text=values,
                textposition='outside'
            )
        ])
        
        fig.update_layout(
            title="Key Performance Indicators",
            xaxis_title="KPI",
            yaxis_title="Value",
            height=400,
            showlegend=False
        )
        
        return fig
    
    def _create_trend_chart(self, metric: str, values: List, periods: List) -> Any:
        """Create trend chart for a metric."""
        if not PLOTLY_AVAILABLE:
            return None
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=periods if periods else list(range(len(values))),
            y=values,
            mode='lines+markers',
            name=metric,
            line=dict(width=2),
            marker=dict(size=8)
        ))
        
        fig.update_layout(
            title=f"{metric} Trend",
            xaxis_title="Period",
            yaxis_title="Value",
            height=300,
            showlegend=False
        )
        
        return fig
    
    def create_kpi_gauge_chart(self, kpi_data: Dict) -> Any:
        """
        Create KPI gauge chart.
        
        Args:
            kpi_data: KPI data dictionary
            
        Returns:
            Plotly figure
        """
        if not PLOTLY_AVAILABLE:
            return None
        
        fig = go.Figure(data=[
            go.Indicator(
                mode="gauge+number+delta",
                value=kpi_data['value'],
                title={'text': kpi_data['name']},
                delta={'reference': kpi_data.get('target', 0)},
                gauge={
                    'axis': {'range': [kpi_data.get('min', 0), kpi_data.get('max', 100)]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [kpi_data.get('min', 0), kpi_data.get('target', 50) * 0.9], 'color': "lightgray"},
                        {'range': [kpi_data.get('target', 50) * 0.9, kpi_data.get('target', 50)], 'color': "yellow"},
                        {'range': [kpi_data.get('target', 50), kpi_data.get('max', 100)], 'color': "green"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': kpi_data.get('target', 50)
                    }
                }
            )
        ])
        
        fig.update_layout(height=300)
        
        return fig
    
    def create_trend_sparkline(self, trend_data: Dict) -> Any:
        """
        Create trend sparkline.
        
        Args:
            trend_data: Trend data dictionary
            
        Returns:
            Plotly figure
        """
        if not PLOTLY_AVAILABLE:
            return None
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=trend_data.get('periods', list(range(len(trend_data['values'])))),
            y=trend_data['values'],
            mode='lines',
            line=dict(width=2, color='blue'),
            fill='tozeroy',
            fillcolor='rgba(0, 100, 200, 0.2)'
        ))
        
        fig.update_layout(
            height=100,
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(showgrid=False, zeroline=False, visible=False),
            yaxis=dict(showgrid=False, zeroline=False, visible=False),
            showlegend=False
        )
        
        return fig
    
    def create_executive_summary_chart(self, summary_data: Dict) -> Any:
        """
        Create executive summary chart.
        
        Args:
            summary_data: Summary data dictionary
            
        Returns:
            Plotly figure
        """
        if not PLOTLY_AVAILABLE:
            return None
        
        fig = go.Figure()
        
        # Actual vs Target bars
        fig.add_trace(go.Bar(
            name='Actual',
            x=summary_data['categories'],
            y=summary_data['scores'],
            marker_color='lightblue'
        ))
        
        fig.add_trace(go.Bar(
            name='Target',
            x=summary_data['categories'],
            y=summary_data['targets'],
            marker_color='gray',
            opacity=0.5
        ))
        
        fig.update_layout(
            title="Performance vs Target",
            xaxis_title="Category",
            yaxis_title="Score",
            barmode='group',
            height=400
        )
        
        return fig
    
    def create_traffic_light_grid(self, metrics: List[Dict]) -> Any:
        """
        Create traffic light grid visualization.
        
        Args:
            metrics: List of metric dictionaries with status
            
        Returns:
            Plotly figure
        """
        if not PLOTLY_AVAILABLE:
            return None
        
        # Create grid layout
        rows = (len(metrics) - 1) // 3 + 1
        cols = min(3, len(metrics))
        
        fig = make_subplots(
            rows=rows, cols=cols,
            subplot_titles=[m['name'] for m in metrics],
            specs=[[{'type': 'scatter'}] * cols for _ in range(rows)]
        )
        
        for i, metric in enumerate(metrics):
            row = i // 3 + 1
            col = i % 3 + 1
            
            color = self._get_status_color(metric['status'])
            
            fig.add_trace(
                go.Scatter(
                    x=[0.5],
                    y=[0.5],
                    mode='markers',
                    marker=dict(size=50, color=color),
                    showlegend=False,
                    hoverinfo='skip'
                ),
                row=row, col=col
            )
        
        fig.update_xaxes(visible=False, range=[0, 1])
        fig.update_yaxes(visible=False, range=[0, 1])
        
        fig.update_layout(
            height=100 * rows,
            title="Status Indicators",
            showlegend=False
        )
        
        return fig
    
    def get_dashboard_layout_config(self) -> Dict:
        """
        Get dashboard layout configuration.
        
        Returns:
            Layout configuration dictionary
        """
        return {
            'grid_rows': 3,
            'grid_cols': 4,
            'component_positions': {
                'kpi_summary': {'row': 1, 'col': 1, 'colspan': 4},
                'traffic_lights': {'row': 2, 'col': 1, 'colspan': 2},
                'trend_chart': {'row': 2, 'col': 3, 'colspan': 2},
                'details': {'row': 3, 'col': 1, 'colspan': 4}
            },
            'spacing': {
                'horizontal': 0.05,
                'vertical': 0.1
            }
        }
    
    def create_multi_panel_dashboard(self, panels: List[Dict], data: Dict) -> Any:
        """
        Create multi-panel executive dashboard.
        
        Args:
            panels: Panel configuration list
            data: Dashboard data
            
        Returns:
            Plotly figure
        """
        if not PLOTLY_AVAILABLE:
            return None
        
        # Determine grid dimensions
        max_row = max(p['position'][0] for p in panels)
        max_col = max(p['position'][1] for p in panels)
        
        # Create subplots
        fig = make_subplots(
            rows=max_row,
            cols=max_col,
            subplot_titles=[p.get('title', '') for p in panels],
            specs=[[{'type': p.get('type', 'scatter')}] * max_col for _ in range(max_row)]
        )
        
        # Add panels
        for panel in panels:
            row, col = panel['position']
            panel_type = panel['type']
            
            if panel_type == 'kpi_grid' and 'kpis' in data:
                # Add KPI bars
                kpis = data['kpis'][:6]
                fig.add_trace(
                    go.Bar(
                        x=[k['name'] for k in kpis],
                        y=[k.get('value', 0) for k in kpis],
                        marker_color=[self._get_status_color(k.get('status', 'gray')) for k in kpis]
                    ),
                    row=row, col=col
                )
            
            elif panel_type == 'trend_chart' and 'trends' in data:
                # Add trend line
                if 'revenue' in data['trends']:
                    fig.add_trace(
                        go.Scatter(
                            x=data['trends'].get('periods', list(range(len(data['trends']['revenue'])))),
                            y=data['trends']['revenue'],
                            mode='lines+markers'
                        ),
                        row=row, col=col
                    )
            
            elif panel_type == 'traffic_lights' and 'kpis' in data:
                # Add traffic light indicators
                for i, kpi in enumerate(data['kpis'][:3]):
                    fig.add_trace(
                        go.Scatter(
                            x=[i],
                            y=[1],
                            mode='markers',
                            marker=dict(
                                size=30,
                                color=self._get_status_color(kpi.get('status', 'gray'))
                            ),
                            text=kpi['name'],
                            showlegend=False
                        ),
                        row=row, col=col
                    )
        
        fig.update_layout(height=600, title="Executive Dashboard")
        
        return fig
    
    def get_dashboard_export_config(self) -> Dict:
        """
        Get dashboard export configuration.
        
        Returns:
            Export configuration dictionary
        """
        return {
            'width': 1920,
            'height': 1080,
            'scale': 2,
            'format': 'png',
            'formats_available': ['png', 'pdf', 'svg'],
            'quality': 'high'
        }
    
    def analyze_competitive_position(self, benchmark_data: Dict) -> Dict:
        """
        Analyze competitive positioning.
        
        Args:
            benchmark_data: Benchmark data dictionary
            
        Returns:
            Competitive analysis results
        """
        positioning = {
            'percentile_rankings': {},
            'peer_comparison': {},
            'strengths': [],
            'improvement_areas': []
        }
        
        company_metrics = benchmark_data.get('company_metrics', {})
        industry_benchmarks = benchmark_data.get('industry_benchmarks', {})
        
        # Calculate percentile rankings
        for metric, value in company_metrics.items():
            if metric in industry_benchmarks:
                benchmark = industry_benchmarks[metric]
                
                # Determine percentile
                if value <= benchmark.get('p25', value):
                    percentile = 25
                elif value <= benchmark.get('p50', value):
                    percentile = 50
                elif value <= benchmark.get('p75', value):
                    percentile = 75
                elif value <= benchmark.get('p90', value):
                    percentile = 90
                else:
                    percentile = 95
                
                positioning['percentile_rankings'][metric] = percentile
                
                # Identify strengths and weaknesses
                if percentile >= 75:
                    positioning['strengths'].append(metric)
                elif percentile <= 25:
                    positioning['improvement_areas'].append(metric)
        
        # Peer comparison
        peer_companies = benchmark_data.get('peer_companies', [])
        for peer in peer_companies:
            peer_name = peer['name']
            positioning['peer_comparison'][peer_name] = {}
            
            for metric in ['production_efficiency', 'safety_score']:
                if metric in peer and metric in company_metrics:
                    positioning['peer_comparison'][peer_name][metric] = {
                        'peer_value': peer[metric],
                        'company_value': company_metrics[metric],
                        'difference': company_metrics[metric] - peer[metric]
                    }
        
        return positioning
    
    def create_benchmark_radar_chart(self, benchmark_data: Dict) -> Any:
        """
        Create competitive benchmark radar chart.
        
        Args:
            benchmark_data: Benchmark data
            
        Returns:
            Plotly figure
        """
        if not PLOTLY_AVAILABLE:
            return None
        
        company_metrics = benchmark_data.get('company_metrics', {})
        industry_benchmarks = benchmark_data.get('industry_benchmarks', {})
        
        categories = list(company_metrics.keys())
        company_values = list(company_metrics.values())
        
        # Get median benchmarks
        benchmark_values = []
        for cat in categories:
            if cat in industry_benchmarks:
                benchmark_values.append(industry_benchmarks[cat].get('p50', 0))
            else:
                benchmark_values.append(0)
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=company_values,
            theta=categories,
            fill='toself',
            name='Company'
        ))
        
        fig.add_trace(go.Scatterpolar(
            r=benchmark_values,
            theta=categories,
            fill='toself',
            name='Industry Median',
            opacity=0.5
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, max(company_values + benchmark_values) * 1.1]
                )
            ),
            showlegend=True,
            title="Competitive Benchmark Analysis"
        )
        
        return fig
    
    def generate_peer_ranking_table(self, peer_companies: List[Dict]) -> List[Dict]:
        """
        Generate peer ranking table.
        
        Args:
            peer_companies: List of peer company data
            
        Returns:
            Sorted ranking table
        """
        # Add our company to the list
        all_companies = peer_companies.copy()
        all_companies.append({
            'name': 'Our Company',
            'production_efficiency': 88.5,  # Example value
            'safety_score': 95.5  # Example value
        })
        
        # Sort by production efficiency (descending)
        all_companies.sort(key=lambda x: x.get('production_efficiency', 0), reverse=True)
        
        # Add ranking
        for i, company in enumerate(all_companies, 1):
            company['rank'] = i
        
        return all_companies
    
    def render(self, context: Dict) -> str:
        """
        Render the executive template.
        
        Args:
            context: Report context data
            
        Returns:
            Rendered report content
        """
        # Generate executive components
        context['executive_kpis'] = self.generate_executive_kpis(context)
        context['performance_score'] = self.calculate_performance_score(context['executive_kpis'])
        
        # Generate strategic metrics if data available
        if 'strategic_data' in context:
            context['strategic_metrics'] = self.calculate_strategic_metrics(context['strategic_data'])
        
        # Generate dashboard if requested
        if context.get('include_dashboard', True):
            dashboard_data = {
                'kpis': [kpi.to_dict() for kpi in context['executive_kpis']],
                'trends': context.get('trends', {})
            }
            context['dashboard'] = self.generate_executive_dashboard(dashboard_data)
        
        # Render using base template
        return super().render(context)