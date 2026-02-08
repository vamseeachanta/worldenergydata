# BSEE Integration Guide

## Table of Contents
1. [Overview](#overview)
2. [BSEE Data Sources](#bsee-data-sources)  
3. [Data Processors](#data-processors)
4. [Financial Validators](#financial-validators)
5. [Comprehensive Reports Integration](#comprehensive-reports-integration)
6. [Common Patterns](#common-patterns)
7. [Field Mappings](#field-mappings)
8. [Examples](#examples)

## Overview

The Well Data Verification System is designed to seamlessly integrate with existing BSEE (Bureau of Safety and Environmental Enforcement) modules in the WorldEnergyData repository. This guide documents how to leverage existing BSEE infrastructure for verification workflows.

### Architecture Integration

```
WorldEnergyData Repository
├── src/worldenergydata/
│   ├── validation/              # Base validation framework
│   │   ├── base.py             # Extended by verification
│   │   └── rules.py            # Reused validation rules
│   │
│   └── modules/
│       ├── bsee/               # BSEE modules
│       │   ├── data/           # Data processors (imported)
│       │   ├── analysis/       
│       │   │   └── financial/  # Financial validators (reused)
│       │   └── reports/
│       │       └── comprehensive/ # Report exporters (leveraged)
│       │
│       └── analysis/
│           └── verification/   # Verification system
│               ├── processors.py # BSEE data adapters
│               └── base.py      # Extends validation framework
```

## BSEE Data Sources

### Available Data Processors

The verification system can directly use BSEE data processors:

```python
from worldenergydata.bsee.data import (
    ProductionDataProcessor,
    LeaseDataProcessor,
    WellDataProcessor,
    FieldDataProcessor
)

# Use BSEE processor in verification
processor = ProductionDataProcessor()
data = processor.load_monthly_production("2024-01")

# Apply BSEE-specific transformations
data = processor.normalize_lease_numbers(data)
data = processor.convert_units(data, target="metric")
```

### BSEEDataAdapter

The verification system provides an adapter for seamless integration:

```python
from worldenergydata.analysis.verification.processors import BSEEDataAdapter

class BSEEDataAdapter:
    """Adapter for BSEE data processors."""
    
    def load_production_data(self, source: str) -> pd.DataFrame:
        """Load production data using BSEE processors."""
        processor = ProductionDataProcessor()
        data = processor.load(source)
        
        # Apply standard transformations
        data = self.normalize_columns(data)
        data = self.validate_structure(data)
        
        return data
    
    def load_well_data(self, source: str) -> pd.DataFrame:
        """Load well master data."""
        processor = WellDataProcessor()
        return processor.load(source)
```

### Data Source Configuration

```yaml
# bsee_data_config.yaml
data_sources:
  production:
    processor: "bsee.ProductionDataProcessor"
    source: "https://www.data.bsee.gov/Production/Files"
    format: "csv"
    
  wells:
    processor: "bsee.WellDataProcessor"
    source: "https://www.data.bsee.gov/Well/Files"
    format: "csv"
    
  leases:
    processor: "bsee.LeaseDataProcessor"
    source: "https://www.data.bsee.gov/Lease/Files"
    format: "csv"
```

## Data Processors

### Production Data Processing

```python
from worldenergydata.bsee.data import ProductionDataProcessor
from worldenergydata.analysis.verification import VerificationEngine

# Load and process BSEE production data
processor = ProductionDataProcessor()

# Load monthly production
monthly_data = processor.load_monthly_production(
    year=2024,
    month=1,
    fields=["Jack", "St. Malo", "Tahiti"]
)

# Apply BSEE-specific transformations
monthly_data = processor.apply_transformations([
    "normalize_lease_numbers",
    "convert_date_formats",
    "calculate_oil_equivalent",
    "add_field_groupings"
])

# Verify processed data
engine = VerificationEngine()
results = engine.verify_data(monthly_data)
```

### Well Data Processing

```python
from worldenergydata.bsee.data import WellDataProcessor

# Process well master data
well_processor = WellDataProcessor()

# Load well information
wells = well_processor.load_well_master()

# Apply well-specific processing
wells = well_processor.process_well_data(wells, {
    "normalize_api": True,
    "validate_coordinates": True,
    "add_field_mapping": True
})

# Cross-reference with production data
verification_engine.cross_reference_wells(
    production_data=monthly_data,
    well_master=wells
)
```

### Lease Data Processing

```python
from worldenergydata.bsee.data import LeaseDataProcessor

# Process lease information
lease_processor = LeaseDataProcessor()

# Load and normalize lease data
leases = lease_processor.load_active_leases()
leases = lease_processor.normalize_lease_numbers(leases)

# Validate lease-production relationships
verification_engine.validate_lease_production(
    production_data=monthly_data,
    lease_data=leases
)
```

## Financial Validators

### Reusing Financial Validation Logic

```python
from worldenergydata.bsee.analysis.financial.validators import (
    validate_oil_prices,
    validate_revenue_calculations,
    validate_royalty_rates
)

# Use BSEE financial validators in verification
class FinancialVerification:
    def verify_financial_data(self, data):
        # Reuse oil price validation
        price_issues = validate_oil_prices(
            data["oil_price"],
            min_price=20,
            max_price=150
        )
        
        # Reuse revenue validation
        revenue_issues = validate_revenue_calculations(
            oil_volume=data["oil_production"],
            oil_price=data["oil_price"],
            calculated_revenue=data["oil_revenue"]
        )
        
        # Reuse royalty validation
        royalty_issues = validate_royalty_rates(
            data["royalty_rate"],
            lease_type=data["lease_type"]
        )
        
        return price_issues + revenue_issues + royalty_issues
```

### Column Validators

```python
from worldenergydata.bsee.analysis.financial.validators import (
    ColumnValidator,
    DateColumnConverter,
    NumericColumnValidator
)

# Use BSEE column validators
validator = ColumnValidator()

# Validate required columns
validator.validate_required_columns(
    data,
    required=["well_name", "production_date", "oil_production"]
)

# Convert date columns
date_converter = DateColumnConverter()
data["production_date"] = date_converter.convert(
    data["production_date"],
    format="%Y-%m-%d"
)

# Validate numeric columns
numeric_validator = NumericColumnValidator()
numeric_issues = numeric_validator.validate(
    data[["oil_production", "gas_production", "water_production"]]
)
```

## Comprehensive Reports Integration

### Leveraging Report Exporters

```python
from worldenergydata.bsee.reports.comprehensive import (
    ReportExporter,
    PDFExporter,
    ExcelExporter
)

class VerificationReportGenerator:
    def __init__(self):
        # Reuse BSEE exporters
        self.pdf_exporter = PDFExporter()
        self.excel_exporter = ExcelExporter()
    
    def generate_verification_report(self, results):
        # Create report data structure
        report_data = self.format_verification_results(results)
        
        # Use BSEE PDF exporter
        self.pdf_exporter.export(
            data=report_data,
            template="verification_template",
            output_path="verification_report.pdf"
        )
        
        # Use BSEE Excel exporter
        self.excel_exporter.export(
            data=report_data,
            sheets={
                "Summary": report_data.summary,
                "Details": report_data.details,
                "Issues": report_data.issues
            },
            output_path="verification_report.xlsx"
        )
```

### Report Controller Patterns

```python
from worldenergydata.bsee.reports.comprehensive import ReportController

class VerificationReportController(ReportController):
    """Extends BSEE report controller for verification."""
    
    def __init__(self):
        super().__init__()
        # Inherit caching, performance optimization, etc.
    
    def generate_verification_report(self, data, config):
        # Use parent class orchestration
        sections = []
        
        # Generate sections using parent methods
        sections.append(self.generate_summary_section(data))
        sections.append(self.generate_detail_section(data))
        
        # Add verification-specific sections
        sections.append(self.generate_quality_section(data))
        sections.append(self.generate_audit_section(data))
        
        # Use parent class report assembly
        return self.assemble_report(sections, config)
```

## Common Patterns

### Pattern 1: Data Loading and Validation

```python
from worldenergydata.bsee.data import ProductionDataProcessor
from worldenergydata.analysis.verification import VerificationEngine

def verify_bsee_production(file_path):
    """Common pattern for BSEE data verification."""
    
    # Step 1: Load using BSEE processor
    processor = ProductionDataProcessor()
    data = processor.load(file_path)
    
    # Step 2: Apply BSEE transformations
    data = processor.normalize_lease_numbers(data)
    data = processor.convert_date_columns(data)
    
    # Step 3: Verify using verification engine
    engine = VerificationEngine()
    results = engine.verify_data(data)
    
    # Step 4: Generate report using BSEE exporters
    report = engine.generate_report(results, format="pdf")
    
    return results, report
```

### Pattern 2: Cross-Module Validation

```python
from worldenergydata.bsee.analysis.financial import FinancialAnalyzer
from worldenergydata.analysis.verification import DataQualityFramework

def cross_validate_financial_data(production_data, price_data):
    """Cross-validate using multiple BSEE modules."""
    
    # Use financial analyzer for calculations
    financial = FinancialAnalyzer()
    calculated = financial.calculate_revenue(production_data, price_data)
    
    # Use verification for quality checks
    quality = DataQualityFramework()
    quality_results = quality.analyze(calculated)
    
    # Cross-reference results
    discrepancies = []
    if quality_results.has_issues():
        for issue in quality_results.issues:
            # Check if financial calculation caused issue
            if issue.field in calculated.columns:
                discrepancies.append({
                    'field': issue.field,
                    'calculated': calculated[issue.field],
                    'issue': issue.message
                })
    
    return discrepancies
```

### Pattern 3: Workflow Integration

```python
from worldenergydata.bsee.workflows import BSEEWorkflow
from worldenergydata.analysis.verification.engine import WorkflowEngine

class IntegratedVerificationWorkflow(BSEEWorkflow):
    """Integrate verification into BSEE workflows."""
    
    def __init__(self):
        super().__init__()
        self.verification_engine = WorkflowEngine()
    
    def execute(self, config):
        # Execute standard BSEE workflow steps
        data = self.load_data(config)
        data = self.process_data(data)
        
        # Insert verification step
        verification_results = self.verification_engine.verify_data(data)
        
        # Continue with BSEE workflow
        if verification_results.quality_score > 0.95:
            results = self.analyze_data(data)
            report = self.generate_report(results)
        else:
            # Handle verification failures
            self.handle_quality_issues(verification_results)
        
        return results
```

## Field Mappings

### BSEE to Verification Field Mapping

```python
# Field mapping configuration
BSEE_TO_VERIFICATION_MAPPING = {
    # BSEE field -> Verification field
    'LEASE_NUMBER': 'lease_number',
    'API_WELL_NUMBER': 'api_number',
    'PRODUCTION_DATE': 'production_date',
    'OIL_VOL': 'oil_production',
    'GAS_VOL': 'gas_production',
    'WATER_VOL': 'water_production',
    'DAYS_ON_PRODUCTION': 'production_days',
    'OIL_SALES_VOL': 'oil_sales',
    'GAS_SALES_VOL': 'gas_sales'
}

def map_bsee_to_verification(bsee_data):
    """Map BSEE fields to verification fields."""
    return bsee_data.rename(columns=BSEE_TO_VERIFICATION_MAPPING)
```

### Unit Conversions

```python
from worldenergydata.bsee.utils import UnitConverter

# BSEE unit conversions
converter = UnitConverter()

def convert_bsee_units(data):
    """Convert BSEE units to verification standards."""
    
    # Oil: BBL to m³ if needed
    if config.units == "metric":
        data["oil_production"] = converter.bbl_to_m3(data["oil_production"])
    
    # Gas: MCF to m³ if needed
    if config.units == "metric":
        data["gas_production"] = converter.mcf_to_m3(data["gas_production"])
    
    return data
```

## Examples

### Example 1: Complete BSEE Data Verification

```python
from worldenergydata.bsee.data import ProductionDataProcessor
from worldenergydata.bsee.analysis.financial import FinancialValidator
from worldenergydata.analysis.verification import VerificationEngine
from worldenergydata.bsee.reports.comprehensive import ReportExporter

def complete_bsee_verification(month="2024-01"):
    """Complete verification using BSEE infrastructure."""
    
    # 1. Load BSEE data
    processor = ProductionDataProcessor()
    production = processor.load_monthly_production(month)
    
    # 2. Apply BSEE validations
    financial_validator = FinancialValidator()
    financial_issues = financial_validator.validate(production)
    
    # 3. Run verification workflow
    engine = VerificationEngine()
    verification_results = engine.verify_data(production)
    
    # 4. Combine results
    combined_results = {
        'financial_issues': financial_issues,
        'verification_results': verification_results,
        'quality_score': verification_results.quality_score
    }
    
    # 5. Generate comprehensive report
    exporter = ReportExporter()
    report = exporter.create_comprehensive_report(
        data=production,
        validation_results=combined_results,
        format="pdf"
    )
    
    return report
```

### Example 2: Jack Field Specific Verification

```python
from worldenergydata.bsee.data import FieldDataProcessor
from worldenergydata.analysis.verification.cross_reference import CrossReferenceModule

def verify_jack_field():
    """Verify Jack Field production using BSEE data."""
    
    # Load Jack Field data
    field_processor = FieldDataProcessor()
    jack_data = field_processor.load_field_data("Jack")
    
    # Load Excel benchmark (if available)
    cross_ref = CrossReferenceModule()
    cross_ref.load_benchmark("specs/modules/bsee/comprehensive-report-system/sub-specs/go_by/Jack_field_data.xlsx")
    
    # Map fields
    cross_ref.add_mapping("oil_production", "Oil Production (BBL)")
    cross_ref.add_mapping("gas_production", "Gas Production (MCF)")
    
    # Compare and verify
    comparison_results = cross_ref.compare(jack_data)
    
    # Generate field-specific report
    report = generate_field_report(
        field_name="Jack",
        production_data=jack_data,
        comparison_results=comparison_results
    )
    
    return report
```

### Example 3: Batch Verification of Multiple Fields

```python
from worldenergydata.bsee.data import BatchProcessor
from worldenergydata.analysis.verification import BatchVerification

def batch_verify_fields(field_list):
    """Batch verification of multiple BSEE fields."""
    
    # Initialize batch processors
    bsee_batch = BatchProcessor()
    verification_batch = BatchVerification()
    
    results = {}
    
    # Process each field
    for field in field_list:
        # Load field data using BSEE processor
        field_data = bsee_batch.load_field(field)
        
        # Verify using verification engine
        verification_results = verification_batch.verify(field_data)
        
        # Store results
        results[field] = {
            'data': field_data,
            'verification': verification_results,
            'quality_score': verification_results.quality_score
        }
    
    # Generate comparative report
    comparative_report = generate_comparative_report(results)
    
    return comparative_report
```

### Example 4: Real-time BSEE Data Monitoring

```python
from worldenergydata.bsee.streaming import BSEEDataStream
from worldenergydata.analysis.verification.quality import RealTimeMonitor

def monitor_bsee_data():
    """Real-time monitoring of BSEE data quality."""
    
    # Initialize streaming
    stream = BSEEDataStream()
    monitor = RealTimeMonitor()
    
    # Configure monitoring
    monitor.configure({
        'alert_threshold': 0.90,
        'check_interval': 3600,  # 1 hour
        'metrics': ['completeness', 'outliers', 'consistency']
    })
    
    # Start monitoring
    for batch in stream.get_batches():
        # Process BSEE batch
        processed = process_bsee_batch(batch)
        
        # Monitor quality
        quality_metrics = monitor.check(processed)
        
        # Alert if issues
        if quality_metrics.score < 0.90:
            send_alert(quality_metrics)
        
        # Log metrics
        log_metrics(quality_metrics)
```

## Best Practices

### 1. Leverage Existing Infrastructure

Always check for existing BSEE functionality before implementing new features:

```python
# Good: Reuse existing processor
from worldenergydata.bsee.data import ProductionDataProcessor
processor = ProductionDataProcessor()

# Avoid: Reimplementing data loading
# custom_loader = CustomProductionLoader()  # Don't do this
```

### 2. Maintain Compatibility

Ensure verification outputs are compatible with BSEE modules:

```python
def format_for_bsee(verification_results):
    """Format verification results for BSEE compatibility."""
    return {
        'status': 'PASS' if verification_results.quality_score > 0.95 else 'FAIL',
        'metrics': verification_results.to_bsee_format(),
        'timestamp': datetime.now().isoformat()
    }
```

### 3. Use Configuration Inheritance

Extend BSEE configurations rather than duplicating:

```yaml
# verification_config.yaml
extends: "@bsee/config/production_config.yaml"

verification:
  # Add verification-specific settings
  quality_threshold: 0.95
```

### 4. Follow BSEE Naming Conventions

Use consistent field names and formats:

```python
# Follow BSEE conventions
BSEE_DATE_FORMAT = "%Y-%m-%d"
BSEE_DECIMAL_PLACES = 2
BSEE_UNITS = {
    'oil': 'BBL',
    'gas': 'MCF',
    'water': 'BBL'
}
```

This integration guide ensures seamless interoperability between the verification system and existing BSEE modules.