# Well Data Verification - CLI Reference

## Table of Contents
1. [Installation](#installation)
2. [Basic Usage](#basic-usage)
3. [Commands](#commands)
4. [Options and Flags](#options-and-flags)
5. [Configuration Files](#configuration-files)
6. [Examples](#examples)
7. [Exit Codes](#exit-codes)

## Installation

The CLI is included with the WorldEnergyData package. Access it via Python module execution:

```bash
# Run the CLI
python -m worldenergydata.modules.analysis.verification.cli [command] [options]

# Or create an alias for convenience
alias wdv="python -m worldenergydata.modules.analysis.verification.cli"
```

## Basic Usage

```bash
# General syntax
python -m worldenergydata.modules.analysis.verification.cli [command] [options]

# Get help
python -m worldenergydata.modules.analysis.verification.cli --help

# Get help for a specific command
python -m worldenergydata.modules.analysis.verification.cli verify --help
```

## Commands

### `verify`

Run a complete verification workflow on production data.

```bash
python -m worldenergydata.modules.analysis.verification.cli verify \
    --data-file <path> \
    --config <config_file> \
    --output-dir <directory>
```

**Arguments:**
- `--data-file, -d`: Path to the data file (CSV or Excel)
- `--config, -c`: Path to configuration YAML file
- `--output-dir, -o`: Directory for output files (default: ./output)

**Options:**
- `--format`: Output format (pdf, excel, both) [default: both]
- `--verbose, -v`: Enable verbose output
- `--parallel`: Number of parallel workers [default: 4]
- `--checkpoint`: Enable checkpoint saving
- `--resume`: Resume from checkpoint file

**Example:**
```bash
python -m worldenergydata.modules.analysis.verification.cli verify \
    --data-file production_2024.csv \
    --config verification_config.yaml \
    --output-dir ./results \
    --format both \
    --verbose
```

### `quality-check`

Run data quality checks without full verification.

```bash
python -m worldenergydata.modules.analysis.verification.cli quality-check \
    --data-file <path> \
    [options]
```

**Arguments:**
- `--data-file, -d`: Path to the data file

**Options:**
- `--completeness`: Check data completeness
- `--outliers`: Detect outliers
- `--ranges`: Validate value ranges
- `--all`: Run all quality checks [default]
- `--threshold`: Quality score threshold [default: 0.95]
- `--export`: Export results to file

**Example:**
```bash
python -m worldenergydata.modules.analysis.verification.cli quality-check \
    --data-file monthly_production.csv \
    --all \
    --threshold 0.90 \
    --export quality_report.json
```

### `cross-reference`

Compare production data with Excel benchmarks.

```bash
python -m worldenergydata.modules.analysis.verification.cli cross-reference \
    --data-file <path> \
    --benchmark <excel_file> \
    [options]
```

**Arguments:**
- `--data-file, -d`: Path to production data
- `--benchmark, -b`: Path to benchmark Excel file

**Options:**
- `--sheet`: Excel sheet name [default: first sheet]
- `--mapping`: Field mapping configuration file
- `--tolerance`: Numeric tolerance percentage [default: 5]
- `--export-discrepancies`: Export discrepancy report

**Example:**
```bash
python -m worldenergydata.modules.analysis.verification.cli cross-reference \
    --data-file actual_production.csv \
    --benchmark expected_values.xlsx \
    --sheet "Q1_2024" \
    --tolerance 10 \
    --export-discrepancies discrepancies.xlsx
```

### `validate-rules`

Validate data against custom rules.

```bash
python -m worldenergydata.modules.analysis.verification.cli validate-rules \
    --data-file <path> \
    --rules <rules_file> \
    [options]
```

**Arguments:**
- `--data-file, -d`: Path to data file
- `--rules, -r`: Path to validation rules YAML file

**Options:**
- `--stop-on-error`: Stop validation on first error
- `--export-violations`: Export rule violations
- `--summary`: Show summary only

**Example:**
```bash
python -m worldenergydata.modules.analysis.verification.cli validate-rules \
    --data-file production.csv \
    --rules custom_rules.yaml \
    --export-violations violations.csv
```

### `audit-log`

Query and export audit logs.

```bash
python -m worldenergydata.modules.analysis.verification.cli audit-log \
    [options]
```

**Options:**
- `--start-date`: Start date (YYYY-MM-DD)
- `--end-date`: End date (YYYY-MM-DD)
- `--user`: Filter by user
- `--activity`: Filter by activity type
- `--export`: Export format (json, csv, excel)
- `--limit`: Maximum number of records

**Example:**
```bash
python -m worldenergydata.modules.analysis.verification.cli audit-log \
    --start-date 2024-01-01 \
    --end-date 2024-01-31 \
    --user john.doe \
    --export audit_january.csv
```

### `generate-report`

Generate verification reports from existing results.

```bash
python -m worldenergydata.modules.analysis.verification.cli generate-report \
    --results <results_file> \
    [options]
```

**Arguments:**
- `--results, -r`: Path to verification results file

**Options:**
- `--template`: Report template name
- `--format`: Output format (pdf, excel, html)
- `--include-charts`: Include visualizations
- `--include-audit`: Include audit trail
- `--output`: Output file path

**Example:**
```bash
python -m worldenergydata.modules.analysis.verification.cli generate-report \
    --results verification_results.json \
    --template comprehensive \
    --format pdf \
    --include-charts \
    --output final_report.pdf
```

### `workflow`

Manage verification workflows.

```bash
python -m worldenergydata.modules.analysis.verification.cli workflow \
    <subcommand> \
    [options]
```

**Subcommands:**
- `list`: List available workflows
- `run`: Run a specific workflow
- `status`: Check workflow status
- `resume`: Resume paused workflow
- `cancel`: Cancel running workflow

**Example:**
```bash
# List available workflows
python -m worldenergydata.modules.analysis.verification.cli workflow list

# Run a workflow
python -m worldenergydata.modules.analysis.verification.cli workflow run \
    --name monthly_verification \
    --config workflow_config.yaml

# Check status
python -m worldenergydata.modules.analysis.verification.cli workflow status \
    --session-id abc123

# Resume workflow
python -m worldenergydata.modules.analysis.verification.cli workflow resume \
    --checkpoint checkpoint_abc123.json
```

### `config`

Manage configuration files.

```bash
python -m worldenergydata.modules.analysis.verification.cli config \
    <subcommand> \
    [options]
```

**Subcommands:**
- `generate`: Generate template configuration
- `validate`: Validate configuration file
- `merge`: Merge multiple configurations

**Example:**
```bash
# Generate template
python -m worldenergydata.modules.analysis.verification.cli config generate \
    --type verification \
    --output my_config.yaml

# Validate configuration
python -m worldenergydata.modules.analysis.verification.cli config validate \
    --file my_config.yaml

# Merge configurations
python -m worldenergydata.modules.analysis.verification.cli config merge \
    --base base_config.yaml \
    --override custom_config.yaml \
    --output merged_config.yaml
```

## Options and Flags

### Global Options

These options are available for all commands:

- `--help, -h`: Show help message
- `--version`: Show version information
- `--verbose, -v`: Enable verbose output
- `--quiet, -q`: Suppress non-error output
- `--log-file`: Path to log file
- `--log-level`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `--no-color`: Disable colored output
- `--config-dir`: Configuration directory [default: ~/.wdv]

### Performance Options

- `--parallel, -p`: Number of parallel workers
- `--batch-size`: Batch size for processing
- `--memory-limit`: Maximum memory usage (MB)
- `--timeout`: Operation timeout (seconds)
- `--cache`: Enable caching
- `--cache-dir`: Cache directory

### Output Options

- `--output-dir, -o`: Output directory
- `--format, -f`: Output format
- `--compress`: Compress output files
- `--timestamp`: Add timestamp to output files
- `--overwrite`: Overwrite existing files

## Configuration Files

### Verification Configuration

```yaml
# verification_config.yaml
verification:
  # Data source configuration
  data_source:
    type: "csv"  # or "excel", "database"
    file: "path/to/data.csv"
    encoding: "utf-8"
    date_columns: ["production_date"]
    
  # Validation rules
  validation_rules:
    oil_production:
      type: "range"
      min: 0
      max: 100000
      unit: "BBL/day"
      
    gas_production:
      type: "range"
      min: 0
      max: 500000
      unit: "MCF/day"
      
    well_name:
      type: "pattern"
      pattern: "^[A-Z]{2}-\\d{4}$"
      
  # Quality checks
  quality_checks:
    completeness:
      threshold: 0.95
      required_fields: ["well_name", "production_date", "oil_production"]
      
    outliers:
      method: "iqr"  # or "z_score", "isolation_forest"
      threshold: 1.5
      
    consistency:
      cross_field_rules:
        - "oil_production + gas_production > 0"
        - "water_cut between 0 and 1"
        
  # Reporting
  reporting:
    format: ["pdf", "excel"]
    template: "standard"
    include_charts: true
    include_audit_trail: true
    
  # Performance
  performance:
    parallel_workers: 4
    batch_size: 1000
    cache_enabled: true
```

### Workflow Configuration

```yaml
# workflow_config.yaml
workflow:
  name: "Monthly Production Verification"
  description: "Complete verification of monthly production data"
  
  # Workflow steps
  steps:
    - id: "load_data"
      name: "Load Production Data"
      type: "data_loader"
      config:
        source: "production_data.csv"
        
    - id: "validate"
      name: "Validate Data"
      type: "validator"
      depends_on: ["load_data"]
      config:
        rules_file: "validation_rules.yaml"
        
    - id: "quality_check"
      name: "Check Data Quality"
      type: "quality_checker"
      depends_on: ["validate"]
      config:
        checks: ["completeness", "outliers", "consistency"]
        
    - id: "cross_reference"
      name: "Cross-Reference Benchmarks"
      type: "cross_reference"
      depends_on: ["quality_check"]
      config:
        benchmark_file: "benchmarks.xlsx"
        
    - id: "report"
      name: "Generate Report"
      type: "report_generator"
      depends_on: ["cross_reference"]
      config:
        format: "pdf"
        template: "monthly_report"
        
  # Checkpoint configuration
  checkpoints:
    enabled: true
    interval: 100  # Records
    directory: "./checkpoints"
    
  # Error handling
  error_handling:
    on_error: "pause"  # or "continue", "abort"
    max_retries: 3
    retry_delay: 60  # Seconds
```

### Rules Configuration

```yaml
# validation_rules.yaml
rules:
  # Range rules
  production_ranges:
    oil_production:
      min: 0
      max: 100000
      severity: "error"
      message: "Oil production {value} outside valid range [{min}, {max}]"
      
    gas_production:
      min: 0
      max: 500000
      severity: "warning"
      
  # Pattern rules
  format_rules:
    well_name:
      pattern: "^[A-Z]{2}-\\d{4}$"
      severity: "error"
      message: "Well name '{value}' doesn't match pattern"
      
    api_number:
      pattern: "^\\d{14}$"
      severity: "warning"
      
  # Custom rules
  custom_rules:
    - name: "production_sum_check"
      expression: "oil_production + gas_production + water_production > 0"
      severity: "error"
      message: "Total production cannot be zero"
      
    - name: "water_cut_range"
      expression: "water_cut >= 0 and water_cut <= 1"
      severity: "error"
      message: "Water cut must be between 0 and 1"
      
  # Conditional rules
  conditional_rules:
    - name: "gas_well_check"
      condition: "well_type == 'GAS'"
      rule: "gas_production > oil_production"
      severity: "warning"
      message: "Gas well should have higher gas than oil production"
```

## Examples

### Example 1: Basic Verification

```bash
# Simple verification with default settings
python -m worldenergydata.modules.analysis.verification.cli verify \
    --data-file production_jan_2024.csv \
    --output-dir ./results
```

### Example 2: Advanced Verification with Configuration

```bash
# Full verification with custom configuration
python -m worldenergydata.modules.analysis.verification.cli verify \
    --data-file production_q1_2024.csv \
    --config advanced_verification.yaml \
    --output-dir ./q1_results \
    --format both \
    --parallel 8 \
    --checkpoint \
    --verbose
```

### Example 3: Quality Check Pipeline

```bash
# Run quality checks and export results
python -m worldenergydata.modules.analysis.verification.cli quality-check \
    --data-file raw_production.csv \
    --completeness \
    --outliers \
    --ranges \
    --threshold 0.90 \
    --export quality_results.json \
    | python -m worldenergydata.modules.analysis.verification.cli generate-report \
    --results - \
    --format pdf \
    --output quality_report.pdf
```

### Example 4: Batch Processing

```bash
#!/bin/bash
# Process multiple files

for file in data/*.csv; do
    echo "Processing $file..."
    python -m worldenergydata.modules.analysis.verification.cli verify \
        --data-file "$file" \
        --config standard_config.yaml \
        --output-dir "./results/$(basename $file .csv)" \
        --quiet
done
```

### Example 5: Cross-Reference with Reporting

```bash
# Compare with benchmarks and generate discrepancy report
python -m worldenergydata.modules.analysis.verification.cli cross-reference \
    --data-file actual_production.csv \
    --benchmark expected_production.xlsx \
    --sheet "January" \
    --tolerance 5 \
    --export-discrepancies discrepancies.xlsx \
    && python -m worldenergydata.modules.analysis.verification.cli generate-report \
    --results discrepancies.xlsx \
    --template discrepancy_report \
    --format pdf \
    --include-charts \
    --output discrepancy_analysis.pdf
```

### Example 6: Workflow Management

```bash
# Start a workflow
SESSION_ID=$(python -m worldenergydata.modules.analysis.verification.cli workflow run \
    --name monthly_verification \
    --config workflow_config.yaml \
    --output-json | jq -r '.session_id')

# Check status
python -m worldenergydata.modules.analysis.verification.cli workflow status \
    --session-id $SESSION_ID

# If paused, resume
python -m worldenergydata.modules.analysis.verification.cli workflow resume \
    --session-id $SESSION_ID
```

### Example 7: Audit Trail Query

```bash
# Query audit logs for specific user and export
python -m worldenergydata.modules.analysis.verification.cli audit-log \
    --start-date 2024-01-01 \
    --end-date 2024-01-31 \
    --user john.doe@company.com \
    --activity data_validation \
    --export audit_trail.csv \
    --limit 1000
```

## Exit Codes

The CLI uses standard exit codes:

- `0`: Success
- `1`: General error
- `2`: Misuse of shell command (invalid arguments)
- `3`: Configuration error
- `4`: Data validation error
- `5`: File not found
- `6`: Permission denied
- `7`: Network error
- `8`: Timeout
- `9`: User cancelled
- `10`: Checkpoint error
- `11`: Memory limit exceeded
- `12`: Invalid data format

## Environment Variables

The CLI respects the following environment variables:

- `WDV_CONFIG_DIR`: Configuration directory (default: ~/.wdv)
- `WDV_LOG_LEVEL`: Default log level
- `WDV_PARALLEL_WORKERS`: Default number of parallel workers
- `WDV_CACHE_DIR`: Cache directory
- `WDV_OUTPUT_DIR`: Default output directory
- `WDV_NO_COLOR`: Disable colored output (set to 1)
- `WDV_TIMEOUT`: Default timeout in seconds

Example:
```bash
export WDV_CONFIG_DIR=/opt/wdv/config
export WDV_LOG_LEVEL=DEBUG
export WDV_PARALLEL_WORKERS=8

python -m worldenergydata.modules.analysis.verification.cli verify \
    --data-file production.csv
```

## Troubleshooting

### Common Issues

1. **Import Error**: Ensure WorldEnergyData is installed:
   ```bash
   pip install -e .
   ```

2. **Configuration Not Found**: Check file path and permissions:
   ```bash
   ls -la verification_config.yaml
   ```

3. **Memory Error**: Reduce batch size or increase memory limit:
   ```bash
   --batch-size 500 --memory-limit 4096
   ```

4. **Timeout Error**: Increase timeout or use checkpoints:
   ```bash
   --timeout 3600 --checkpoint
   ```

For more help, see the [Troubleshooting Guide](troubleshooting.md).