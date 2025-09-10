# Well Data Verification System - User Guide

## Table of Contents
1. [System Overview](#system-overview)
2. [Key Concepts](#key-concepts)
3. [Getting Started](#getting-started)
4. [Core Features](#core-features)
5. [Verification Workflows](#verification-workflows)
6. [Data Quality Checks](#data-quality-checks)
7. [Audit and Compliance](#audit-and-compliance)
8. [Report Generation](#report-generation)
9. [Best Practices](#best-practices)

## System Overview

The Well Data Verification System is a comprehensive data quality assurance tool designed specifically for validating oil and gas well production data from BSEE (Bureau of Safety and Environmental Enforcement) sources. It provides systematic workflows for ensuring data accuracy, identifying anomalies, and maintaining compliance with regulatory requirements.

### Purpose

The system addresses critical challenges in well data management:
- **Data Accuracy**: Validates production volumes against expected ranges
- **Completeness**: Identifies missing data points and gaps in time series
- **Consistency**: Cross-references data with Excel benchmarks
- **Compliance**: Maintains complete audit trails for regulatory requirements
- **Quality Assurance**: Detects outliers and anomalies before analysis

### Architecture

The system is built on a modular architecture that extends WorldEnergyData's existing validation framework:

```
Well Data Verification System
├── Workflow Engine        (Guided validation processes)
├── Data Quality Framework (Validation rules and checks)
├── Cross-Reference Module (Excel benchmark comparison)
├── Audit System          (Compliance and tracking)
└── Report Generator      (PDF and Excel outputs)
```

## Key Concepts

### Verification Workflow
A structured, step-by-step process that guides users through data validation tasks. Each workflow consists of:
- **Steps**: Individual validation tasks (e.g., "Check production volumes")
- **Checkpoints**: Save points where progress is preserved
- **Sessions**: User sessions that can be paused and resumed
- **Results**: Validation outcomes with detailed findings

### Validation Rules
Configurable business rules that define acceptable data criteria:
- **Range Rules**: Numeric values must fall within specified bounds
- **Pattern Rules**: String values must match specific patterns
- **Completeness Rules**: Required fields must be present
- **Consistency Rules**: Related fields must be logically consistent

### Quality Scores
Quantitative metrics that measure data quality:
- **Completeness Score**: Percentage of non-missing values
- **Validity Score**: Percentage of values passing validation rules
- **Consistency Score**: Percentage of cross-referenced matches
- **Overall Score**: Weighted average of all quality metrics

### Audit Trail
Complete record of all verification activities:
- **User Actions**: Who performed what action and when
- **Data Changes**: Before/after values for corrections
- **Validation Results**: Outcomes of each check
- **Compliance Status**: Alignment with regulatory standards

## Getting Started

### Installation

The verification system is part of the WorldEnergyData package. Ensure you have the required dependencies:

```bash
# Using uv (recommended)
uv pip install jsonschema openpyxl reportlab

# Or using pip
pip install jsonschema openpyxl reportlab
```

### Basic Usage

The simplest way to start is using the command-line interface:

```bash
# Run a basic verification workflow
python -m worldenergydata.modules.analysis.verification.cli verify \
    --data-file production_data.csv \
    --output-dir ./verification_results

# Check data quality
python -m worldenergydata.modules.analysis.verification.cli quality-check \
    --data-file production_data.csv \
    --config quality_config.yaml
```

### Python API

For programmatic access:

```python
from worldenergydata.modules.analysis.verification import VerificationEngine
from worldenergydata.modules.analysis.verification.config import VerificationConfig

# Load configuration
config = VerificationConfig.from_yaml("verification_config.yaml")

# Create verification engine
engine = VerificationEngine(config)

# Run verification workflow
results = engine.verify_data("production_data.csv")

# Generate report
report = engine.generate_report(results, format="pdf")
```

## Core Features

### 1. Data Loading and Preprocessing

The system supports multiple data sources:
- **CSV Files**: Standard comma-separated values
- **Excel Files**: Multi-sheet workbooks with complex layouts
- **BSEE Data**: Direct integration with BSEE data processors

Example data loading:

```python
from worldenergydata.modules.analysis.verification.processors import BSEEDataAdapter

# Load BSEE production data
adapter = BSEEDataAdapter()
data = adapter.load_production_data("bsee_production_2024.csv")

# Apply preprocessing
data = adapter.normalize_lease_numbers(data)
data = adapter.convert_date_columns(data)
```

### 2. Validation Rules Engine

Define and apply custom validation rules:

```python
from worldenergydata.modules.analysis.verification.quality import ValidationRuleBuilder

# Create validation rules
builder = ValidationRuleBuilder()

# Add range rule for oil production
oil_rule = builder.add_range_rule(
    field="oil_production",
    min_value=0,
    max_value=100000,
    message="Oil production outside expected range"
).build()

# Add pattern rule for well names
well_rule = builder.add_pattern_rule(
    field="well_name",
    pattern=r"^[A-Z]{2}-\d{4}$",
    message="Invalid well name format"
).build()

# Apply rules to data
results = validator.validate(data, rules=[oil_rule, well_rule])
```

### 3. Outlier Detection

Identify statistical anomalies in production data:

```python
from worldenergydata.modules.analysis.verification.quality import OutlierDetector

detector = OutlierDetector(method="z_score", threshold=3.0)
outliers = detector.detect(data["oil_production"])

# Get detailed outlier information
for idx, value in outliers:
    print(f"Outlier at index {idx}: {value}")
```

### 4. Cross-Reference with Excel Benchmarks

Compare data against Excel reference files:

```python
from worldenergydata.modules.analysis.verification.cross_reference import CrossReferenceModule

# Initialize cross-reference module
cross_ref = CrossReferenceModule()

# Load Excel benchmark
cross_ref.load_benchmark("benchmark_data.xlsx", sheet="Production")

# Map fields between database and Excel
cross_ref.add_mapping("oil_prod", "Oil Production (BBL)")
cross_ref.add_mapping("gas_prod", "Gas Production (MCF)")

# Compare and get discrepancies
discrepancies = cross_ref.compare(data)
```

## Verification Workflows

### Standard Verification Workflow

The standard workflow covers all essential validation steps:

1. **Data Loading**: Import production data from source files
2. **Completeness Check**: Identify missing values and gaps
3. **Range Validation**: Verify values fall within expected bounds
4. **Outlier Detection**: Identify statistical anomalies
5. **Cross-Reference**: Compare with Excel benchmarks
6. **Report Generation**: Create verification reports

### Custom Workflows

Create custom workflows for specific needs:

```yaml
# custom_workflow.yaml
workflow:
  name: "Monthly Production Verification"
  description: "Verify monthly production data for Jack Field"
  
  steps:
    - id: "load_data"
      type: "data_loader"
      config:
        source: "bsee_monthly_production.csv"
        
    - id: "validate_volumes"
      type: "validator"
      config:
        rules:
          - field: "oil_production"
            min: 0
            max: 50000
          - field: "gas_production"
            min: 0
            max: 100000
            
    - id: "check_completeness"
      type: "completeness_checker"
      config:
        required_fields: ["well_name", "production_date", "oil_production"]
        
    - id: "generate_report"
      type: "report_generator"
      config:
        format: "pdf"
        template: "monthly_verification"
```

### Resumable Sessions

Workflows support pause and resume functionality:

```python
from worldenergydata.modules.analysis.verification.engine import WorkflowEngine

# Start workflow
engine = WorkflowEngine()
session = engine.start_workflow("verification_workflow.yaml")

# Process some steps
for i in range(3):
    engine.execute_step(session)
    
# Save checkpoint
checkpoint = engine.create_checkpoint(session)
checkpoint.save("session_checkpoint.json")

# Later, resume from checkpoint
resumed_session = engine.load_checkpoint("session_checkpoint.json")
engine.continue_workflow(resumed_session)
```

## Data Quality Checks

### Completeness Validation

Check for missing data and gaps:

```python
from worldenergydata.modules.analysis.verification.quality import CompletenessChecker

checker = CompletenessChecker()
results = checker.check(data)

print(f"Completeness Score: {results.completeness_score:.2%}")
print(f"Missing Values: {results.missing_count}")
print(f"Missing Months: {results.missing_months}")
```

### Production Volume Validation

Validate oil and gas production values:

```python
from worldenergydata.modules.analysis.verification.quality import ProductionVolumeValidator

validator = ProductionVolumeValidator(
    oil_min=0, oil_max=100000,
    gas_min=0, gas_max=500000
)

results = validator.validate(data)
for issue in results.issues:
    print(f"{issue.severity}: {issue.message}")
```

### Statistical Analysis

Perform statistical quality checks:

```python
from worldenergydata.modules.analysis.verification.quality import DataQualityFramework

framework = DataQualityFramework()
quality_report = framework.analyze(data)

# Get quality metrics
print(f"Mean: {quality_report.statistics['mean']}")
print(f"Std Dev: {quality_report.statistics['std_dev']}")
print(f"Outliers: {quality_report.outlier_count}")
```

## Audit and Compliance

### Activity Logging

All verification activities are automatically logged:

```python
from worldenergydata.modules.analysis.verification.audit import AuditSystem

# Initialize audit system
audit = AuditSystem(user="john.doe@company.com")

# Activities are automatically logged
with audit.track_session("verification_session"):
    # Perform verification tasks
    results = engine.verify_data(data)
    
# Query audit logs
logs = audit.query_logs(
    start_date="2024-01-01",
    activity_type="data_validation"
)
```

### Compliance Reporting

Generate compliance reports for regulatory requirements:

```python
from worldenergydata.modules.analysis.verification.audit import ComplianceManager

compliance = ComplianceManager()

# Check SOX compliance
sox_status = compliance.check_compliance("SOX", audit_logs)

# Generate compliance report
report = compliance.generate_compliance_report(
    standard="SOX",
    period="2024-Q1"
)
```

### Role-Based Access Control

Control access to verification functions:

```python
from worldenergydata.modules.analysis.verification.audit import SecurityController

security = SecurityController()

# Check user permissions
if security.has_permission(user, "approve_verification"):
    # Allow approval action
    results.approve(user)
else:
    raise PermissionError("User lacks approval permission")
```

## Report Generation

### Verification Reports

Generate comprehensive verification reports:

```python
from worldenergydata.modules.analysis.verification.reports import VerificationReportGenerator

generator = VerificationReportGenerator()

# Create verification report
report = generator.create_report(
    verification_results=results,
    include_sections=[
        "summary",
        "data_quality",
        "validation_results",
        "discrepancies",
        "audit_trail"
    ]
)

# Export to PDF
generator.export_pdf(report, "verification_report.pdf")

# Export to Excel
generator.export_excel(report, "verification_report.xlsx")
```

### Custom Report Templates

Create custom report templates:

```python
from worldenergydata.modules.analysis.verification.reports import ReportTemplate

# Define custom template
template = ReportTemplate(
    name="Monthly Verification Report",
    sections=[
        {"id": "header", "type": "title", "content": "Monthly Production Verification"},
        {"id": "summary", "type": "summary", "fields": ["total_wells", "verification_date"]},
        {"id": "quality", "type": "data_quality", "include_charts": True},
        {"id": "issues", "type": "issues_list", "severity": ["error", "warning"]}
    ]
)

# Generate report with custom template
report = generator.create_report(results, template=template)
```

### Batch Report Generation

Generate multiple reports efficiently:

```python
# Generate reports for multiple fields
fields = ["Jack Field", "Mary Field", "John Field"]

for field in fields:
    field_data = data[data["field_name"] == field]
    results = engine.verify_data(field_data)
    
    report_name = f"{field}_verification_report.pdf"
    generator.export_pdf(
        generator.create_report(results),
        report_name
    )
```

## Best Practices

### 1. Configuration Management

Store configuration in YAML files for version control:

```yaml
# verification_config.yaml
verification:
  workflow:
    type: "standard"
    checkpoint_interval: 100
    
  validation:
    oil_production:
      min: 0
      max: 100000
    gas_production:
      min: 0
      max: 500000
      
  quality:
    completeness_threshold: 0.95
    outlier_method: "iqr"
    outlier_threshold: 1.5
    
  reporting:
    format: "pdf"
    include_charts: true
    include_audit_trail: true
```

### 2. Error Handling

Implement robust error handling:

```python
from worldenergydata.modules.analysis.verification.base import VerificationError

try:
    results = engine.verify_data(data)
except VerificationError as e:
    logger.error(f"Verification failed: {e}")
    # Handle specific error types
    if e.error_type == "data_quality":
        # Attempt data cleaning
        cleaned_data = clean_data(data)
        results = engine.verify_data(cleaned_data)
```

### 3. Performance Optimization

For large datasets, use batch processing:

```python
# Process data in chunks
chunk_size = 1000
for i in range(0, len(data), chunk_size):
    chunk = data[i:i+chunk_size]
    results = engine.verify_data(chunk)
    # Process results incrementally
```

### 4. Regular Validation

Schedule regular verification runs:

```python
import schedule
import time

def run_daily_verification():
    """Run daily verification workflow"""
    data = load_latest_production_data()
    results = engine.verify_data(data)
    
    if results.has_critical_issues():
        send_alert_email(results)
    
    generator.export_pdf(
        generator.create_report(results),
        f"daily_verification_{datetime.now().date()}.pdf"
    )

# Schedule daily at 6 AM
schedule.every().day.at("06:00").do(run_daily_verification)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### 5. Documentation

Document validation rules and decisions:

```python
# Add documentation to validation rules
rule = ValidationRuleBuilder() \
    .add_range_rule(
        field="oil_production",
        min_value=0,
        max_value=100000,
        message="Oil production outside expected range",
        documentation="""
        Range based on historical production data from 2020-2024.
        Maximum observed production was 95,000 BBL/day.
        Added 5% buffer for exceptional cases.
        """
    ).build()
```

## Next Steps

After familiarizing yourself with this guide:

1. Review the [Workflow Tutorial](workflow_tutorial.md) for step-by-step instructions
2. Check the [CLI Reference](cli_reference.md) for command-line options
3. See the [API Documentation](api_reference.md) for programmatic usage
4. Read the [Configuration Guide](configuration_guide.md) for customization
5. Consult the [Troubleshooting Guide](troubleshooting.md) for common issues

For questions or support, please refer to the WorldEnergyData documentation or contact the development team.