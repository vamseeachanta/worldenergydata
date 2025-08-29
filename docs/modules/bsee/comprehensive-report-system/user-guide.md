# BSEE Comprehensive Report System - User Guide

## Table of Contents
1. [Overview](#overview)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [CLI Usage](#cli-usage)
5. [Report Types](#report-types)
6. [Configuration](#configuration)
7. [Examples](#examples)
8. [Output Formats](#output-formats)

## Overview

The BSEE Comprehensive Report System generates standardized reports for well and production data across three organizational levels:
- **Blocks** - Highest level aggregation
- **Fields** - Mid-level aggregation
- **Leases** - Detailed well-level data

### Key Features
- Multi-level hierarchical reporting
- Template-based report generation
- Multiple export formats (Excel, PDF, HTML, JSON)
- Interactive visualizations
- Performance-optimized for large datasets

## Installation

### Prerequisites
- Python 3.8 or higher
- Required packages: Install via pip or uv

```bash
# Using uv (recommended)
uv pip install openpyxl weasyprint plotly jinja2 click pyyaml pandas numpy

# Or using pip
pip install openpyxl weasyprint plotly jinja2 click pyyaml pandas numpy
```

### Module Installation
The module is part of the worldenergydata package:
```bash
cd /path/to/worldenergydata
python -m worldenergydata.modules.bsee.reports.comprehensive --help
```

## Quick Start

### Generate a Basic Report
```bash
# Generate a block-level report for Atwater Valley
python -m worldenergydata.modules.bsee.reports.comprehensive generate \
    --level block \
    --unit "Atwater Valley" \
    --format excel \
    --output reports/
```

### Generate Multiple Reports
```bash
# Generate reports for multiple fields
python -m worldenergydata.modules.bsee.reports.comprehensive generate \
    --level field \
    --units "Jack,Julia,St Malo,Stones" \
    --format pdf \
    --output reports/
```

## CLI Usage

### Main Command Structure
```
python -m worldenergydata.modules.bsee.reports.comprehensive [COMMAND] [OPTIONS]
```

### Available Commands

#### `generate` - Generate Reports
Generate reports for specified organizational units.

**Options:**
- `--level` - Organization level: block, field, or lease (required)
- `--unit` - Single unit name (e.g., "Jack")
- `--units` - Multiple units, comma-separated (e.g., "Jack,Julia,Stones")
- `--template` - Template type: compliance, economic, operational, executive (default: economic)
- `--format` - Output format: excel, pdf, html, json (default: excel)
- `--output` - Output directory path (default: current directory)
- `--start-date` - Report start date (YYYY-MM-DD)
- `--end-date` - Report end date (YYYY-MM-DD)
- `--config` - Path to YAML configuration file

**Examples:**
```bash
# Single field report
python -m worldenergydata.modules.bsee.reports.comprehensive generate \
    --level field \
    --unit "Jack" \
    --template economic \
    --format excel

# Multiple lease reports with date range
python -m worldenergydata.modules.bsee.reports.comprehensive generate \
    --level lease \
    --units "WC544-001,WC544-002" \
    --start-date 2023-01-01 \
    --end-date 2023-12-31 \
    --format pdf
```

#### `export` - Export Existing Reports
Export previously generated reports to different formats.

**Options:**
- `--input` - Input report file path
- `--format` - Target format: excel, pdf, html, json
- `--output` - Output file path

**Example:**
```bash
python -m worldenergydata.modules.bsee.reports.comprehensive export \
    --input reports/jack_field_report.json \
    --format pdf \
    --output reports/jack_field_report.pdf
```

#### `analyze` - Analyze Data
Perform quick analysis without full report generation.

**Options:**
- `--level` - Organization level
- `--unit` - Unit name
- `--metric` - Metric to analyze: production, revenue, costs, efficiency
- `--period` - Time period: monthly, quarterly, yearly

**Example:**
```bash
python -m worldenergydata.modules.bsee.reports.comprehensive analyze \
    --level field \
    --unit "Jack" \
    --metric production \
    --period monthly
```

#### `configure` - Manage Configuration
Create or modify configuration files.

**Options:**
- `--create` - Create new configuration
- `--template` - Base template for configuration
- `--output` - Configuration file path

**Example:**
```bash
python -m worldenergydata.modules.bsee.reports.comprehensive configure \
    --create \
    --template economic \
    --output config/economic_reports.yaml
```

## Report Types

### 1. Compliance Report
Focuses on regulatory compliance and environmental metrics.

**Sections:**
- Production quota compliance
- Environmental metrics and thresholds
- Safety incident tracking
- Regulatory citations and references

**Best for:** Regulatory submissions, audit preparation

### 2. Economic Report
Comprehensive financial analysis and economics.

**Sections:**
- Revenue and cost breakdown
- NPV and IRR calculations
- Individual well economics
- Sensitivity analysis
- Economic forecasting

**Best for:** Financial planning, investment decisions

### 3. Operational Report
Detailed operational performance metrics.

**Sections:**
- Well status and availability
- Production efficiency metrics
- Equipment reliability (MTBF, MTTR)
- Maintenance schedules
- Failure analysis

**Best for:** Operations management, maintenance planning

### 4. Executive Report
High-level dashboard with KPIs and strategic metrics.

**Sections:**
- Key performance indicators
- Traffic light status indicators
- Year-over-year comparisons
- Competitive benchmarking
- Strategic recommendations

**Best for:** Executive briefings, board presentations

## Configuration

### Using Configuration Files
Create a YAML configuration file for complex report setups:

```yaml
# config/report_config.yaml
report:
  level: field
  units:
    - Jack
    - Julia
    - St Malo
  template: economic
  date_range:
    start: 2023-01-01
    end: 2023-12-31
  
output:
  formats:
    - excel
    - pdf
  directory: reports/2023/
  
options:
  include_visualizations: true
  include_summaries: true
  parallel_processing: true
  cache_enabled: true
```

Run with configuration:
```bash
python -m worldenergydata.modules.bsee.reports.comprehensive generate \
    --config config/report_config.yaml
```

### Environment Variables
Set defaults via environment variables:
```bash
export BSEE_REPORT_OUTPUT_DIR=/path/to/reports
export BSEE_REPORT_DEFAULT_FORMAT=excel
export BSEE_REPORT_CACHE_ENABLED=true
```

## Examples

### Example 1: Monthly Production Report
Generate monthly production reports for all fields in Walker Ridge:

```bash
python -m worldenergydata.modules.bsee.reports.comprehensive generate \
    --level block \
    --unit "Walker Ridge" \
    --template operational \
    --format excel \
    --start-date 2023-01-01 \
    --end-date 2023-12-31 \
    --output reports/walker_ridge/
```

### Example 2: Compliance Audit Package
Create compliance reports for regulatory audit:

```bash
python -m worldenergydata.modules.bsee.reports.comprehensive generate \
    --level field \
    --units "Jack,Julia,St Malo,Stones" \
    --template compliance \
    --format pdf \
    --output audit_2023/
```

### Example 3: Executive Dashboard
Generate executive dashboard for all blocks:

```bash
python -m worldenergydata.modules.bsee.reports.comprehensive generate \
    --level block \
    --units "ALL" \
    --template executive \
    --format html \
    --output dashboards/
```

### Example 4: Batch Processing
Process multiple reports using a configuration file:

```yaml
# batch_reports.yaml
reports:
  - level: block
    unit: Walker Ridge
    template: economic
    format: excel
  
  - level: field
    units: [Jack, Julia]
    template: operational
    format: pdf
  
  - level: lease
    units: [WC544-001, WC544-002]
    template: compliance
    format: excel

output:
  directory: batch_reports/
  timestamp: true
```

```bash
python -m worldenergydata.modules.bsee.reports.comprehensive generate \
    --config batch_reports.yaml
```

## Output Formats

### Excel Format
- Multiple worksheets for different sections
- Professional formatting with headers and footers
- Embedded charts and graphs
- Formulas for dynamic calculations
- Color-coded cells for status indicators

### PDF Format
- Professional document layout
- Table of contents with bookmarks
- High-quality charts and visualizations
- Page numbers and headers
- Print-ready formatting

### HTML Format
- Interactive web-based reports
- Responsive design for mobile viewing
- Interactive Plotly charts
- Drill-down capabilities
- Export individual sections

### JSON Format
- Machine-readable data structure
- Complete data preservation
- Easy integration with other systems
- Suitable for APIs and automation
- Compact file size

## Performance Tips

### For Large Datasets
1. **Enable caching** to reuse aggregated data:
   ```bash
   --cache-enabled true
   ```

2. **Use parallel processing** for multiple units:
   ```bash
   --parallel true --workers 4
   ```

3. **Limit date ranges** when possible:
   ```bash
   --start-date 2023-01-01 --end-date 2023-12-31
   ```

### Memory Management
- Process blocks separately for very large datasets
- Use streaming mode for datasets over 1GB
- Enable garbage collection between reports

### Optimization Settings
```yaml
# performance.yaml
performance:
  cache:
    enabled: true
    ttl: 3600  # seconds
  
  parallel:
    enabled: true
    workers: 4
  
  memory:
    max_usage: 2048  # MB
    streaming_threshold: 1024  # MB
  
  batch:
    size: 10
    delay: 1  # seconds between batches
```

## Troubleshooting

### Common Issues

**Issue:** Report generation takes too long
- **Solution:** Enable caching and parallel processing
- **Solution:** Reduce date range or process in batches

**Issue:** Out of memory error
- **Solution:** Enable streaming mode for large datasets
- **Solution:** Process organizational units separately

**Issue:** Missing data in reports
- **Solution:** Verify data source connectivity
- **Solution:** Check date range includes data
- **Solution:** Review log files for data loading errors

**Issue:** Export format not working
- **Solution:** Ensure required libraries installed (weasyprint for PDF)
- **Solution:** Check output directory permissions
- **Solution:** Verify format is supported for template type

### Getting Help
- Check log files in `logs/` directory
- Run with `--verbose` flag for detailed output
- Use `--dry-run` to test without generating reports
- Contact support with error messages and log files

## Best Practices

1. **Regular Updates**: Generate reports on a consistent schedule
2. **Template Selection**: Choose appropriate template for audience
3. **Data Validation**: Review reports for accuracy before distribution
4. **Performance**: Use caching for frequently generated reports
5. **Automation**: Use configuration files for repeatable processes
6. **Archival**: Keep historical reports for trend analysis
7. **Security**: Protect sensitive financial and operational data

## Command Reference

### Global Options
- `--verbose` - Enable detailed logging
- `--quiet` - Suppress non-error output
- `--dry-run` - Preview without execution
- `--help` - Show help message
- `--version` - Show version information

### Exit Codes
- `0` - Success
- `1` - General error
- `2` - Invalid arguments
- `3` - Data not found
- `4` - Permission denied
- `5` - Output error

---

For more information, see the [API Documentation](api-documentation.md) or [Developer Guide](developer-guide.md).