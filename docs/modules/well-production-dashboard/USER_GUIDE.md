# Well Production Dashboard - User Guide

## Table of Contents
1. [Overview](#overview)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Features](#features)
5. [CLI Commands](#cli-commands)
6. [API Reference](#api-reference)
7. [Configuration](#configuration)
8. [Performance Optimization](#performance-optimization)
9. [Troubleshooting](#troubleshooting)

## Overview

The Well Production Dashboard is a comprehensive web-based visualization and analysis platform for oil & gas well production data. It provides real-time monitoring, data verification, field aggregation, and export capabilities with integrated quality assurance.

### Key Capabilities
- **Real-time Visualization**: Interactive charts for production trends, decline curves, and economic metrics
- **Data Verification**: Integrated quality scoring and anomaly detection
- **Field Aggregation**: Multi-well analysis and comparison at field level
- **Export Options**: PDF, Excel, and JSON exports with verification metadata
- **Performance Optimization**: Lazy loading and caching for large datasets
- **Audit Trail**: Complete monitoring and logging of all actions

## Installation

### Prerequisites
- Python 3.8 or higher
- Virtual environment (recommended)
- Redis (optional, for caching)

### Install from Repository
```bash
# Clone the repository
git clone https://github.com/yourusername/worldenergydata.git
cd worldenergydata

# Create virtual environment
python -m venv .venv
source .venv/Scripts/activate  # On Windows
# or
source .venv/bin/activate  # On Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

### Required Dependencies
```bash
# Core dependencies
pandas>=1.3.0
numpy>=1.21.0
plotly>=5.0.0
dash>=2.0.0
flask>=2.0.0
redis>=4.0.0  # Optional
psutil>=5.8.0  # Optional
```

## Quick Start

### 1. Command Line Interface
```bash
# View available commands
python -m worldenergydata.well_production_dashboard.cli --help

# Start the dashboard server
python -m worldenergydata.well_production_dashboard.cli serve

# Generate a report for specific wells
python -m worldenergydata.well_production_dashboard.cli report --wells W001,W002 --format pdf

# Verify data quality
python -m worldenergydata.well_production_dashboard.cli verify --field "Test Field"
```

### 2. Python API
```python
from worldenergydata.well_production_dashboard import WellProductionDashboard

# Initialize dashboard
dashboard = WellProductionDashboard(config_path="config/dashboard_config.yml")

# Load well data
well_data = dashboard.get_well_data("W001", start_date="2023-01-01")

# Generate field summary
field_summary = dashboard.get_field_summary("Test Field")

# Export to Excel
dashboard.export_to_excel(
    wells=["W001", "W002"],
    output_path="reports/production_report.xlsx",
    include_verification=True
)
```

### 3. Web Interface
```bash
# Start the web server
python -m worldenergydata.well_production_dashboard.cli serve --port 8050

# Open browser to http://localhost:8050
```

## Features

### Data Visualization

#### Production Charts
- Time series plots with multiple production streams (oil, gas, water)
- Decline curve analysis with exponential and hyperbolic fitting
- Stacked area charts for composition analysis
- Interactive tooltips and zoom capabilities

#### Economic Metrics
- Net Present Value (NPV) calculations
- Internal Rate of Return (IRR)
- Payback period analysis
- Waterfall charts for cash flow visualization

#### Field Aggregation
- Multi-well comparison charts
- Field-level production rollups
- Efficiency rankings and benchmarking
- Lease hierarchy visualization

### Data Quality & Verification

#### Quality Scoring
- Automatic data quality assessment (0-100 score)
- Completeness checks
- Anomaly detection
- Trend analysis

#### Verification Status
- Visual badges indicating data quality
- Color-coded indicators (Green: >80%, Yellow: 60-80%, Red: <60%)
- Drill-down to detailed verification reports
- Audit trail links for transparency

### Interactive Components

#### Filters
- Quality score filters (minimum threshold)
- Date range selectors with data freshness indicators
- Well/Field multi-select dropdowns
- Production type toggles

#### Chart Interactions
- Click to drill down
- Hover for details
- Pan and zoom
- Export chart as image
- Reset view button

### Export Capabilities

#### Supported Formats
- **PDF**: Professional reports with charts and tables
- **Excel**: Multi-sheet workbooks with formatting
- **JSON**: Machine-readable data with metadata
- **CSV**: Simple tabular exports

#### Export Options
```python
# Example export configuration
export_config = {
    'include_charts': True,
    'include_verification': True,
    'include_raw_data': False,
    'quality_threshold': 0.7,
    'date_range': ('2023-01-01', '2023-12-31')
}

dashboard.export_batch(
    wells=['W001', 'W002'],
    formats=['pdf', 'excel'],
    config=export_config
)
```

## CLI Commands

### Main Commands

#### `serve` - Start Dashboard Server
```bash
python -m worldenergydata.well_production_dashboard.cli serve \
    --host 0.0.0.0 \
    --port 8050 \
    --debug
```

#### `report` - Generate Reports
```bash
# Generate PDF report for specific wells
python -m worldenergydata.well_production_dashboard.cli report \
    --wells W001,W002,W003 \
    --format pdf \
    --output reports/production_report.pdf \
    --include-verification

# Generate Excel report for a field
python -m worldenergydata.well_production_dashboard.cli report \
    --field "Test Field" \
    --format excel \
    --output reports/field_report.xlsx
```

#### `verify` - Run Data Verification
```bash
# Verify specific wells
python -m worldenergydata.well_production_dashboard.cli verify \
    --wells W001,W002 \
    --output verification_report.json

# Verify entire field
python -m worldenergydata.well_production_dashboard.cli verify \
    --field "Test Field" \
    --quality-threshold 0.8
```

#### `export` - Batch Export Data
```bash
# Export multiple formats
python -m worldenergydata.well_production_dashboard.cli export \
    --wells W001,W002 \
    --formats pdf,excel,json \
    --output-dir exports/
```

#### `cache` - Manage Cache
```bash
# Clear cache
python -m worldenergydata.well_production_dashboard.cli cache --clear

# View cache statistics
python -m worldenergydata.well_production_dashboard.cli cache --stats
```

#### `monitor` - View Monitoring Data
```bash
# View performance metrics
python -m worldenergydata.well_production_dashboard.cli monitor --metrics

# View audit trail
python -m worldenergydata.well_production_dashboard.cli monitor --audit \
    --user admin \
    --last-hours 24
```

## API Reference

### Core Classes

#### WellProductionDashboard
Main dashboard class that orchestrates all functionality.

```python
from worldenergydata.well_production_dashboard import WellProductionDashboard

dashboard = WellProductionDashboard(
    config_path="config/dashboard_config.yml",
    enable_cache=True,
    enable_monitoring=True
)
```

**Key Methods:**
- `get_well_data(well_id, start_date, end_date)` - Retrieve well production data
- `get_field_summary(field_name)` - Get field-level aggregated data
- `verify_data_quality(wells)` - Run verification on well data
- `export_to_pdf(wells, output_path)` - Export to PDF report
- `export_to_excel(wells, output_path)` - Export to Excel workbook
- `get_metrics_summary()` - Get performance metrics

#### QueryOptimizer
Handles query optimization and lazy loading for large datasets.

```python
from worldenergydata.well_production_dashboard.query_optimizer import QueryOptimizer

optimizer = QueryOptimizer()
optimizer.optimize_for_dashboard(enable_lazy=True, prefetch=2)

# Lazy load data in pages
page_data = optimizer.get_data_lazy(page=0, filters={'field': 'Test'})

# Process large dataset in chunks
for chunk in optimizer.get_data_chunked(filters={'status': 'active'}):
    process_chunk(chunk)
```

#### DashboardMonitor
Provides monitoring and audit logging capabilities.

```python
from worldenergydata.well_production_dashboard.monitoring import DashboardMonitor

monitor = DashboardMonitor(config={'audit_file': 'logs/audit.jsonl'})

# Track performance
with monitor.track_performance("data_export"):
    export_data()

# Log audit entry
monitor.audit_action(
    action="data_export",
    resource="well_W001",
    user="admin",
    details={"format": "pdf"}
)

# Get metrics
metrics = monitor.get_metrics_summary()
```

## Configuration

### Dashboard Configuration (YAML)
```yaml
# config/dashboard_config.yml
dashboard:
  title: "Well Production Dashboard"
  theme: "light"
  refresh_interval: 60  # seconds

data:
  source: "bsee"
  cache_enabled: true
  cache_ttl: 300  # seconds
  lazy_loading:
    enabled: true
    page_size: 100
    prefetch_pages: 2

verification:
  enabled: true
  quality_threshold: 0.7
  anomaly_detection: true

export:
  formats: ["pdf", "excel", "json"]
  include_verification: true
  include_charts: true

monitoring:
  enabled: true
  audit_file: "logs/dashboard_audit.jsonl"
  alert_thresholds:
    response_time_ms: 5000
    error_rate: 0.05
    memory_mb: 1000
```

### Environment Variables
```bash
# .env file
DASHBOARD_PORT=8050
DASHBOARD_HOST=0.0.0.0
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql://user:pass@localhost/db
LOG_LEVEL=INFO
ENABLE_DEBUG=false
```

## Performance Optimization

### Lazy Loading
Enable lazy loading for large datasets to improve performance:

```python
# Configure lazy loading
dashboard.query_optimizer.optimize_for_dashboard(
    enable_lazy=True,
    prefetch=3,  # Prefetch 3 pages
    cache_ttl=600  # Cache for 10 minutes
)

# Process data in chunks
def process_large_dataset(well_ids):
    results = dashboard.query_optimizer.process_large_dataset(
        well_ids=well_ids,
        batch_processor=analyze_batch,
        progress_callback=update_progress
    )
    return results
```

### Caching Strategies
```python
# Configure Redis caching
from worldenergydata.well_production_dashboard.cache_config import CacheConfig

cache_config = CacheConfig(
    backend="redis",
    redis_url="redis://localhost:6379",
    ttl=300,
    max_entries=10000
)

dashboard.set_cache_config(cache_config)
```

### Memory Management
```python
# Monitor memory usage
memory_stats = dashboard.query_optimizer.get_memory_usage()
print(f"Cache size: {memory_stats['cache_mb']} MB")
print(f"Index size: {memory_stats['index_mb']} MB")

# Clear cache when needed
if memory_stats['total_mb'] > 500:
    dashboard.query_optimizer.clear_cache()
```

## Troubleshooting

### Common Issues

#### 1. Dashboard Won't Start
**Error**: `ModuleNotFoundError: No module named 'dash'`
**Solution**: Install required dependencies
```bash
pip install dash plotly flask
```

#### 2. Slow Performance
**Issue**: Dashboard loads slowly with large datasets
**Solution**: Enable lazy loading and caching
```python
dashboard.query_optimizer.optimize_for_dashboard(enable_lazy=True)
```

#### 3. Export Fails
**Error**: `PermissionError: [Errno 13] Permission denied`
**Solution**: Ensure write permissions for output directory
```bash
chmod 755 reports/
```

#### 4. Data Verification Issues
**Issue**: Low quality scores for all wells
**Solution**: Check data completeness and format
```python
# Debug verification
result = dashboard.verify_data_quality(wells=['W001'], debug=True)
print(result.details)
```

### Debug Mode
Enable debug mode for detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

dashboard = WellProductionDashboard(debug=True)
```

### Support
For additional help:
- Check the [API documentation](api-reference.md)
- Review [example notebooks](examples/)
- Submit issues on [GitHub](https://github.com/yourusername/worldenergydata/issues)

## Examples

### Complete Workflow Example
```python
from worldenergydata.well_production_dashboard import WellProductionDashboard
from datetime import datetime, timedelta

# Initialize dashboard
dashboard = WellProductionDashboard(config_path="config/dashboard.yml")

# Set date range
end_date = datetime.now()
start_date = end_date - timedelta(days=365)

# Get well data with verification
wells = ["W001", "W002", "W003"]
for well_id in wells:
    # Load data
    data = dashboard.get_well_data(well_id, start_date, end_date)
    
    # Verify quality
    quality = dashboard.verify_data_quality([well_id])
    
    # Generate visualizations if quality is good
    if quality.quality_score > 0.7:
        dashboard.create_production_chart(well_id)
        dashboard.create_decline_curve(well_id)
    else:
        print(f"Warning: Low quality score for {well_id}: {quality.quality_score}")

# Generate field summary
field_summary = dashboard.get_field_summary("Test Field")

# Export comprehensive report
dashboard.export_batch(
    wells=wells,
    formats=["pdf", "excel"],
    output_dir="reports/",
    config={
        'include_verification': True,
        'include_charts': True,
        'quality_threshold': 0.7
    }
)

# View performance metrics
metrics = dashboard.get_metrics_summary()
print(f"Processed {metrics['data_points_processed']} data points")
print(f"Average response time: {metrics['avg_response_time_ms']}ms")
print(f"Cache hit rate: {metrics['cache_hit_rate']*100:.1f}%")
```

---

*Last Updated: 2025-09-12*
*Version: 1.0.0*