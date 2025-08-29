# API Documentation

## Table of Contents
1. [Overview](#overview)
2. [Core Classes](#core-classes)
3. [Data Models](#data-models)
4. [Aggregation API](#aggregation-api)
5. [Template API](#template-api)
6. [Export API](#export-api)
7. [Visualization API](#visualization-api)
8. [Usage Examples](#usage-examples)
9. [Error Handling](#error-handling)
10. [Performance Considerations](#performance-considerations)

## Overview

The BSEE Comprehensive Report System provides a Python API for programmatic report generation, data aggregation, and visualization. The API is designed for integration with existing systems and automation workflows.

### Installation
```python
from worldenergydata.modules.bsee.reports.comprehensive import (
    ReportController,
    DataAggregator,
    TemplateEngine,
    ExportEngine
)
```

## Core Classes

### ReportController

Main orchestrator for report generation.

```python
class ReportController:
    """
    Controls the entire report generation workflow.
    
    Args:
        config (dict): Configuration dictionary
        cache_enabled (bool): Enable caching for performance
        parallel (bool): Enable parallel processing
    """
    
    def __init__(self, config: dict, cache_enabled: bool = True, parallel: bool = True):
        """Initialize the report controller."""
        
    def generate_report(self, 
                       level: str, 
                       unit: str, 
                       template: str = 'economic',
                       date_range: tuple = None) -> Report:
        """
        Generate a report for specified organizational unit.
        
        Args:
            level: Organization level ('block', 'field', 'lease')
            unit: Unit name (e.g., 'Jack')
            template: Template type ('compliance', 'economic', 'operational', 'executive')
            date_range: Tuple of (start_date, end_date)
            
        Returns:
            Report object with generated content
            
        Raises:
            ValueError: Invalid level or unit
            DataNotFoundError: No data for specified unit
        """
        
    def batch_generate(self, units: list, **kwargs) -> list:
        """Generate reports for multiple units."""
        
    async def generate_report_async(self, **kwargs) -> Report:
        """Async version for concurrent generation."""
```

### Usage Example
```python
# Initialize controller
controller = ReportController(
    config={'output_dir': 'reports/'},
    cache_enabled=True,
    parallel=True
)

# Generate single report
report = controller.generate_report(
    level='field',
    unit='Jack',
    template='economic',
    date_range=('2023-01-01', '2023-12-31')
)

# Batch generation
reports = controller.batch_generate(
    units=['Jack', 'Julia', 'St Malo'],
    level='field',
    template='operational'
)
```

## Data Models

### OrganizationalUnit

Base class for hierarchical organization.

```python
@dataclass
class OrganizationalUnit:
    """Represents an organizational unit in the hierarchy."""
    
    name: str
    level: str  # 'block', 'field', 'lease'
    api_number: Optional[str] = None
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_child(self, child: str) -> None:
        """Add a child unit."""
        
    def get_hierarchy_path(self) -> List[str]:
        """Get full hierarchy path from root."""
```

### WellSummary

Well-level data model.

```python
@dataclass
class WellSummary:
    """Summary data for a single well."""
    
    api_number: str
    well_name: str
    lease: str
    field: str
    block: str
    status: str  # 'ACTIVE', 'SHUT_IN', 'ABANDONED'
    spud_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    water_depth: Optional[float] = None
    total_depth: Optional[float] = None
    
    def is_active(self) -> bool:
        """Check if well is currently active."""
        
    def age_days(self) -> int:
        """Calculate well age in days."""
```

### ProductionMetrics

Production data model.

```python
@dataclass
class ProductionMetrics:
    """Production metrics for a time period."""
    
    start_date: datetime
    end_date: datetime
    oil_bbls: float = 0.0
    gas_mcf: float = 0.0
    water_bbls: float = 0.0
    injection_bbls: float = 0.0
    days_on_production: int = 0
    
    @property
    def boe(self) -> float:
        """Calculate barrel of oil equivalent."""
        return self.oil_bbls + (self.gas_mcf / 6.0)
    
    @property
    def water_cut(self) -> float:
        """Calculate water cut percentage."""
        total_liquid = self.oil_bbls + self.water_bbls
        return self.water_bbls / total_liquid if total_liquid > 0 else 0.0
    
    def daily_average(self, metric: str) -> float:
        """Calculate daily average for a metric."""
```

### EconomicMetrics

Financial data model.

```python
@dataclass
class EconomicMetrics:
    """Economic and financial metrics."""
    
    revenue: float = 0.0
    operating_costs: float = 0.0
    capital_costs: float = 0.0
    netback: float = 0.0
    npv: Optional[float] = None
    irr: Optional[float] = None
    payback_months: Optional[int] = None
    
    @property
    def profit(self) -> float:
        """Calculate profit."""
        return self.revenue - self.operating_costs - self.capital_costs
    
    @property
    def margin(self) -> float:
        """Calculate profit margin."""
        return self.profit / self.revenue if self.revenue > 0 else 0.0
```

## Aggregation API

### DataAggregator

Abstract base class for data aggregation strategies.

```python
class DataAggregator(ABC):
    """Abstract base class for data aggregation."""
    
    @abstractmethod
    def aggregate(self, data: pd.DataFrame, level: str) -> Dict[str, Any]:
        """Aggregate data at specified level."""
        
    def validate_data(self, data: pd.DataFrame) -> bool:
        """Validate input data format."""
        
    def apply_filters(self, data: pd.DataFrame, filters: dict) -> pd.DataFrame:
        """Apply filters to data."""
```

### BlockAggregator

Aggregates data at block level.

```python
class BlockAggregator(DataAggregator):
    """Aggregates data at block level."""
    
    def aggregate(self, data: pd.DataFrame, level: str = 'block') -> Dict[str, Any]:
        """
        Aggregate data for block level reporting.
        
        Returns:
            Dictionary with aggregated metrics:
            - total_wells: Total well count
            - active_wells: Active well count
            - production: ProductionMetrics object
            - economics: EconomicMetrics object
            - fields: List of field summaries
        """
        
    def rollup_fields(self, field_data: List[dict]) -> dict:
        """Roll up field-level data to block level."""
```

### Usage Example
```python
# Initialize aggregator
aggregator = BlockAggregator()

# Load data
data = pd.read_csv('production_data.csv')

# Aggregate
block_metrics = aggregator.aggregate(data, level='block')

# Access aggregated data
print(f"Total Wells: {block_metrics['total_wells']}")
print(f"Total Production (BOE): {block_metrics['production'].boe}")
print(f"Total Revenue: ${block_metrics['economics'].revenue:,.2f}")
```

## Template API

### TemplateEngine

Manages template processing and rendering.

```python
class TemplateEngine:
    """Jinja2-based template engine."""
    
    def __init__(self, template_dir: str = None):
        """Initialize template engine with directory."""
        
    def render(self, template_name: str, context: dict) -> str:
        """
        Render template with context data.
        
        Args:
            template_name: Name of template file
            context: Dictionary of template variables
            
        Returns:
            Rendered HTML/text content
        """
        
    def register_filter(self, name: str, func: callable) -> None:
        """Register custom Jinja2 filter."""
        
    def validate_context(self, template_name: str, context: dict) -> bool:
        """Validate context has required variables."""
```

### Template Types

```python
class EconomicTemplate(BaseReportTemplate):
    """Economic report template."""
    
    def render_sections(self, data: dict) -> dict:
        """
        Render all sections of economic report.
        
        Returns:
            Dictionary with rendered sections:
            - summary: Executive summary
            - production: Production analysis
            - revenue: Revenue breakdown
            - costs: Cost analysis
            - npv_analysis: NPV calculations
            - sensitivity: Sensitivity analysis
        """
        
    def calculate_metrics(self, data: dict) -> EconomicMetrics:
        """Calculate economic metrics from data."""
```

### Usage Example
```python
# Initialize template engine
engine = TemplateEngine(template_dir='templates/')

# Register custom filters
engine.register_filter('currency', lambda x: f'${x:,.2f}')
engine.register_filter('percentage', lambda x: f'{x:.1%}')

# Prepare context
context = {
    'unit_name': 'Jack Field',
    'period': '2023',
    'production': production_metrics,
    'economics': economic_metrics
}

# Render template
html_content = engine.render('economic_report.html', context)
```

## Export API

### ExportEngine

Manages multi-format export functionality.

```python
class ExportEngine:
    """Handles report export to various formats."""
    
    def export(self, report: Report, format: str, output_path: str) -> str:
        """
        Export report to specified format.
        
        Args:
            report: Report object to export
            format: Export format ('excel', 'pdf', 'html', 'json')
            output_path: Output file path
            
        Returns:
            Path to exported file
            
        Raises:
            UnsupportedFormatError: Format not supported
            ExportError: Export failed
        """
        
    def batch_export(self, reports: list, format: str, output_dir: str) -> list:
        """Export multiple reports."""
        
    def register_exporter(self, format: str, exporter: callable) -> None:
        """Register custom exporter."""
```

### ExcelExporter

Excel-specific export functionality.

```python
class ExcelExporter:
    """Export reports to Excel format."""
    
    def export(self, report: Report, output_path: str) -> str:
        """
        Export report to Excel with formatting.
        
        Features:
        - Multiple worksheets for sections
        - Professional formatting
        - Embedded charts
        - Formulas and calculations
        """
        
    def add_worksheet(self, workbook: Workbook, name: str, data: pd.DataFrame) -> None:
        """Add formatted worksheet to workbook."""
        
    def add_chart(self, worksheet: Worksheet, chart_type: str, data_range: str) -> None:
        """Add chart to worksheet."""
```

### Usage Example
```python
# Initialize export engine
exporter = ExportEngine()

# Export to Excel
excel_path = exporter.export(
    report=report,
    format='excel',
    output_path='reports/jack_field_2023.xlsx'
)

# Export to PDF
pdf_path = exporter.export(
    report=report,
    format='pdf',
    output_path='reports/jack_field_2023.pdf'
)

# Batch export
paths = exporter.batch_export(
    reports=reports,
    format='excel',
    output_dir='reports/batch/'
)
```

## Visualization API

### VisualizationBuilder

Creates interactive charts and dashboards.

```python
class VisualizationBuilder:
    """Build visualizations using Plotly."""
    
    def create_chart(self, 
                    chart_type: str,
                    data: pd.DataFrame,
                    **kwargs) -> go.Figure:
        """
        Create chart of specified type.
        
        Args:
            chart_type: Type of chart ('line', 'bar', 'scatter', 'heatmap', etc.)
            data: DataFrame with chart data
            **kwargs: Additional chart configuration
            
        Returns:
            Plotly Figure object
        """
        
    def create_dashboard(self, charts: list, layout: str = 'grid') -> go.Figure:
        """Create dashboard with multiple charts."""
        
    def export_static(self, figure: go.Figure, format: str, path: str) -> None:
        """Export chart to static image format."""
```

### Chart Types

```python
class ProductionChart:
    """Production-specific visualizations."""
    
    def trend_chart(self, data: pd.DataFrame, products: list = None) -> go.Figure:
        """Create production trend chart."""
        
    def forecast_chart(self, historical: pd.DataFrame, forecast: pd.DataFrame) -> go.Figure:
        """Create production forecast chart."""
        
    def decline_curve(self, data: pd.DataFrame, well: str) -> go.Figure:
        """Create decline curve analysis chart."""
```

### Usage Example
```python
# Initialize visualization builder
viz = VisualizationBuilder()

# Create production trend chart
production_chart = viz.create_chart(
    chart_type='line',
    data=production_df,
    title='Production Trends',
    x='date',
    y=['oil_bbls', 'gas_mcf'],
    colors=['brown', 'blue']
)

# Create economic waterfall chart
waterfall_chart = viz.create_chart(
    chart_type='waterfall',
    data=financial_df,
    title='Revenue Breakdown',
    categories=['Gross Revenue', 'Operating Costs', 'Capital Costs', 'Net Revenue']
)

# Create dashboard
dashboard = viz.create_dashboard(
    charts=[production_chart, waterfall_chart],
    layout='grid'
)

# Export to static image
viz.export_static(dashboard, format='png', path='dashboard.png')
```

## Usage Examples

### Complete Workflow Example

```python
from worldenergydata.modules.bsee.reports.comprehensive import (
    ReportController,
    DataLoader,
    ConfigManager
)
from datetime import datetime, timedelta

# 1. Setup configuration
config = ConfigManager.load_config('config/report_config.yaml')

# 2. Initialize components
controller = ReportController(config)
loader = DataLoader(config['data_source'])

# 3. Load data
data = loader.load_production_data(
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2023, 12, 31)
)

# 4. Generate reports for multiple fields
fields = ['Jack', 'Julia', 'St Malo', 'Stones']
reports = []

for field in fields:
    try:
        report = controller.generate_report(
            level='field',
            unit=field,
            template='economic',
            date_range=('2023-01-01', '2023-12-31')
        )
        reports.append(report)
        print(f"Generated report for {field}")
        
    except Exception as e:
        print(f"Error generating report for {field}: {e}")
        continue

# 5. Export reports
exporter = ExportEngine()
for report in reports:
    # Export to Excel
    excel_path = exporter.export(
        report=report,
        format='excel',
        output_path=f'reports/{report.unit_name}_2023.xlsx'
    )
    
    # Export to PDF
    pdf_path = exporter.export(
        report=report,
        format='pdf',
        output_path=f'reports/{report.unit_name}_2023.pdf'
    )
    
    print(f"Exported {report.unit_name}: {excel_path}, {pdf_path}")

# 6. Create summary dashboard
viz = VisualizationBuilder()
summary_chart = viz.create_chart(
    chart_type='bar',
    data=pd.DataFrame([r.summary_metrics() for r in reports]),
    title='Field Comparison',
    x='field',
    y='total_production_boe'
)

# Save dashboard
viz.export_static(summary_chart, 'html', 'reports/field_comparison.html')
```

### Custom Integration Example

```python
# Custom integration with existing system
class CustomReportIntegration:
    """Example integration with existing system."""
    
    def __init__(self, db_connection, report_config):
        self.db = db_connection
        self.controller = ReportController(report_config)
        
    def generate_monthly_reports(self):
        """Generate monthly reports for all active fields."""
        
        # Get active fields from database
        fields = self.db.query("SELECT name FROM fields WHERE status = 'ACTIVE'")
        
        # Generate reports
        for field in fields:
            report = self.controller.generate_report(
                level='field',
                unit=field['name'],
                template='operational'
            )
            
            # Store report metadata in database
            self.db.execute(
                "INSERT INTO reports (field, date, path) VALUES (?, ?, ?)",
                (field['name'], datetime.now(), report.output_path)
            )
            
    def schedule_reports(self, frequency='monthly'):
        """Schedule automatic report generation."""
        
        if frequency == 'monthly':
            # Run on first day of each month
            schedule.every().month.at("00:00").do(self.generate_monthly_reports)
        elif frequency == 'weekly':
            # Run every Monday
            schedule.every().monday.at("00:00").do(self.generate_weekly_reports)
```

## Error Handling

### Exception Classes

```python
class ReportGenerationError(Exception):
    """Base exception for report generation errors."""
    pass

class DataNotFoundError(ReportGenerationError):
    """Raised when required data is not available."""
    pass

class TemplateError(ReportGenerationError):
    """Raised when template processing fails."""
    pass

class ExportError(ReportGenerationError):
    """Raised when export fails."""
    pass

class ValidationError(ReportGenerationError):
    """Raised when data validation fails."""
    pass
```

### Error Handling Example

```python
from worldenergydata.modules.bsee.reports.comprehensive.exceptions import (
    DataNotFoundError,
    TemplateError,
    ExportError
)

def safe_report_generation(unit_name: str) -> Optional[Report]:
    """Generate report with comprehensive error handling."""
    
    try:
        # Attempt report generation
        report = controller.generate_report(
            level='field',
            unit=unit_name,
            template='economic'
        )
        return report
        
    except DataNotFoundError as e:
        logger.error(f"No data found for {unit_name}: {e}")
        # Try alternative data source
        return generate_from_backup_source(unit_name)
        
    except TemplateError as e:
        logger.error(f"Template error for {unit_name}: {e}")
        # Fall back to basic template
        return generate_with_basic_template(unit_name)
        
    except ExportError as e:
        logger.error(f"Export failed for {unit_name}: {e}")
        # Retry with different format
        return retry_with_json_export(unit_name)
        
    except Exception as e:
        logger.critical(f"Unexpected error for {unit_name}: {e}")
        # Send alert and return None
        send_error_alert(unit_name, e)
        return None
```

## Performance Considerations

### Caching Strategy

```python
from functools import lru_cache
from worldenergydata.modules.bsee.reports.comprehensive.cache import CacheManager

class OptimizedReportController(ReportController):
    """Report controller with performance optimizations."""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.cache = CacheManager(ttl=3600)  # 1 hour TTL
        
    @lru_cache(maxsize=128)
    def get_aggregated_data(self, unit: str, level: str) -> dict:
        """Cache aggregated data for reuse."""
        
        # Check cache first
        cache_key = f"{level}:{unit}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
            
        # Aggregate data
        data = self.aggregator.aggregate(unit, level)
        
        # Store in cache
        self.cache.set(cache_key, data)
        return data
```

### Parallel Processing

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio

class ParallelReportGenerator:
    """Generate reports in parallel for better performance."""
    
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
    def generate_batch(self, units: list, **kwargs) -> list:
        """Generate reports for multiple units in parallel."""
        
        futures = []
        for unit in units:
            future = self.executor.submit(
                self._generate_single,
                unit,
                **kwargs
            )
            futures.append((unit, future))
            
        results = []
        for unit, future in futures:
            try:
                report = future.result(timeout=300)  # 5 minute timeout
                results.append(report)
            except Exception as e:
                logger.error(f"Failed to generate report for {unit}: {e}")
                continue
                
        return results
        
    async def generate_batch_async(self, units: list, **kwargs) -> list:
        """Async version for better concurrency."""
        
        tasks = [
            self._generate_single_async(unit, **kwargs)
            for unit in units
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        return [r for r in results if not isinstance(r, Exception)]
```

### Memory Management

```python
class StreamingDataProcessor:
    """Process large datasets with streaming to manage memory."""
    
    def process_large_dataset(self, file_path: str, chunk_size: int = 10000):
        """Process large dataset in chunks."""
        
        for chunk in pd.read_csv(file_path, chunksize=chunk_size):
            # Process chunk
            processed = self.process_chunk(chunk)
            
            # Yield results to avoid memory buildup
            yield processed
            
            # Explicit garbage collection for very large datasets
            if chunk_size > 50000:
                import gc
                gc.collect()
```

## Best Practices

1. **Always use context managers** for resource management
2. **Implement proper error handling** with specific exception types
3. **Use caching** for frequently accessed data
4. **Enable parallel processing** for batch operations
5. **Validate input data** before processing
6. **Log all operations** for debugging and audit
7. **Use type hints** for better code documentation
8. **Write unit tests** for custom integrations
9. **Monitor memory usage** for large datasets
10. **Document custom extensions** thoroughly

---

For more information, see the [Developer Guide](developer-guide.md) or [Template Customization Guide](template-customization-guide.md).