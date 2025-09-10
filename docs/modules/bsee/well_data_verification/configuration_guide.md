# Well Data Verification - Configuration Guide

## Table of Contents
1. [Configuration Overview](#configuration-overview)
2. [Main Configuration File](#main-configuration-file)
3. [Validation Rules Configuration](#validation-rules-configuration)
4. [Workflow Configuration](#workflow-configuration)
5. [Quality Checks Configuration](#quality-checks-configuration)
6. [Cross-Reference Configuration](#cross-reference-configuration)
7. [Audit Configuration](#audit-configuration)
8. [Report Configuration](#report-configuration)
9. [Performance Tuning](#performance-tuning)
10. [Environment-Specific Configuration](#environment-specific-configuration)

## Configuration Overview

The Well Data Verification System uses YAML configuration files to control all aspects of the verification process. Configuration files follow a hierarchical structure allowing for inheritance and overrides.

### Configuration Hierarchy

```
base_config.yaml          # Base configuration
├── production.yaml       # Production overrides
├── development.yaml      # Development overrides
└── field_specific/       # Field-specific configurations
    ├── jack_field.yaml
    └── mary_field.yaml
```

### Loading Configuration

```python
from worldenergydata.modules.analysis.verification.config import VerificationConfig

# Load single configuration
config = VerificationConfig.from_yaml("verification_config.yaml")

# Load with overrides
config = VerificationConfig.from_yaml("base_config.yaml")
config.merge("production.yaml")  # Apply production overrides

# Load from dictionary
config_dict = {
    "verification": {
        "validation_rules": {...}
    }
}
config = VerificationConfig.from_dict(config_dict)
```

## Main Configuration File

The main configuration file contains all verification settings.

### Complete Configuration Example

```yaml
# verification_config.yaml
verification:
  # Metadata
  name: "Production Data Verification"
  version: "1.0.0"
  description: "Comprehensive verification for BSEE production data"
  
  # Data Source Configuration
  data_source:
    type: "csv"  # Options: csv, excel, database
    file: "production_data.csv"
    encoding: "utf-8"
    delimiter: ","
    date_columns: ["production_date"]
    date_format: "%Y-%m-%d"
    
    # Excel-specific options
    excel:
      sheet_name: "Production"
      header_row: 0
      skip_rows: []
      
    # Database-specific options
    database:
      connection_string: "postgresql://user:pass@host/db"
      query: "SELECT * FROM production WHERE year = 2024"
      
  # Field Definitions
  fields:
    well_name:
      type: "string"
      required: true
      unique: false
      
    production_date:
      type: "date"
      required: true
      format: "%Y-%m-%d"
      
    oil_production:
      type: "numeric"
      required: true
      unit: "BBL/day"
      decimal_places: 2
      
    gas_production:
      type: "numeric"
      required: true
      unit: "MCF/day"
      decimal_places: 2
      
    water_production:
      type: "numeric"
      required: false
      unit: "BBL/day"
      decimal_places: 2
      
  # Validation Configuration
  validation:
    enabled: true
    stop_on_error: false
    max_errors: 100
    
    # Range validation
    ranges:
      oil_production:
        min: 0
        max: 100000
        severity: "error"
        
      gas_production:
        min: 0
        max: 500000
        severity: "warning"
        
      water_cut:
        min: 0
        max: 1
        severity: "error"
        
    # Pattern validation
    patterns:
      well_name:
        pattern: "^[A-Z]{2}-\\d{4}$"
        message: "Well name must match format XX-9999"
        severity: "error"
        
      api_number:
        pattern: "^\\d{14}$"
        message: "API number must be 14 digits"
        severity: "warning"
        
    # Custom validation rules
    custom_rules:
      - name: "total_production_check"
        expression: "oil_production + gas_production + water_production > 0"
        message: "Total production cannot be zero"
        severity: "error"
        
      - name: "date_sequence_check"
        type: "temporal"
        check: "no_gaps"
        message: "Missing dates in production sequence"
        severity: "warning"
        
  # Quality Checks
  quality:
    completeness:
      enabled: true
      threshold: 0.95
      required_fields: ["well_name", "production_date", "oil_production"]
      
    outliers:
      enabled: true
      method: "iqr"  # Options: iqr, z_score, isolation_forest
      threshold: 1.5
      columns: ["oil_production", "gas_production"]
      
    consistency:
      enabled: true
      rules:
        - "oil_production >= 0"
        - "gas_production >= 0"
        - "water_cut between 0 and 1"
        
  # Cross-Reference Configuration
  cross_reference:
    enabled: false
    benchmark_file: "benchmarks.xlsx"
    sheet_name: "Expected"
    tolerance: 0.05  # 5% tolerance
    
    field_mapping:
      well_name: "Well Name"
      oil_production: "Expected Oil (BBL)"
      gas_production: "Expected Gas (MCF)"
      
  # Audit Configuration
  audit:
    enabled: true
    database: "./audit.db"
    log_level: "INFO"  # DEBUG, INFO, WARNING, ERROR
    
    compliance:
      standards: ["SOX", "GDPR"]
      retention_days: 2555  # 7 years
      
  # Report Configuration
  reporting:
    output_directory: "./verification_results"
    formats: ["pdf", "excel"]
    
    pdf:
      template: "standard"
      include_charts: true
      include_summary: true
      include_details: true
      
    excel:
      include_pivot: true
      highlight_issues: true
      separate_sheets: true
      
    email:
      enabled: false
      smtp_server: "smtp.company.com"
      from_address: "verification@company.com"
      recipients: ["ops@company.com", "compliance@company.com"]
      
  # Performance Configuration
  performance:
    parallel_workers: 4
    batch_size: 1000
    memory_limit_mb: 2048
    timeout_seconds: 3600
    
    caching:
      enabled: true
      directory: "./.cache"
      ttl_seconds: 86400  # 24 hours
      
  # Logging Configuration
  logging:
    level: "INFO"
    file: "verification.log"
    format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    rotation:
      enabled: true
      max_bytes: 10485760  # 10MB
      backup_count: 5
```

## Validation Rules Configuration

Detailed configuration for validation rules.

### Range Rules

```yaml
# range_rules.yaml
validation_rules:
  ranges:
    # Simple range
    oil_production:
      min: 0
      max: 100000
      
    # Range with conditions
    gas_production:
      conditions:
        - when: "well_type == 'OIL'"
          min: 0
          max: 50000
        - when: "well_type == 'GAS'"
          min: 1000
          max: 200000
          
    # Dynamic range based on other fields
    water_cut:
      min: 0
      max: 1
      dynamic: true
      calculation: "water_production / (oil_production + water_production)"
      
    # Time-based ranges
    monthly_production:
      type: "temporal"
      aggregation: "sum"
      group_by: ["well_name", "month"]
      min: 1000
      max: 1000000
```

### Pattern Rules

```yaml
# pattern_rules.yaml
validation_rules:
  patterns:
    # Simple regex pattern
    well_name:
      pattern: "^[A-Z]{2}-\\d{4}$"
      
    # Multiple pattern options
    lease_number:
      patterns:
        - "^OCS-G-\\d{5}$"  # Federal lease
        - "^\\d{6}$"         # State lease
      match_any: true
      
    # Pattern with transformation
    api_number:
      pattern: "^\\d{14}$"
      transform: "remove_non_digits"
      
    # Conditional patterns
    identifier:
      conditions:
        - when: "source == 'BSEE'"
          pattern: "^\\d{10}$"
        - when: "source == 'State'"
          pattern: "^[A-Z]{2}\\d{8}$"
```

### Custom Rules

```yaml
# custom_rules.yaml
validation_rules:
  custom:
    # Python expression rules
    - name: "production_ratio"
      type: "expression"
      expression: "gas_production / oil_production < 100"
      message: "Unusual gas-oil ratio"
      applies_to: "well_type == 'OIL'"
      
    # SQL-like rules
    - name: "duplicate_check"
      type: "sql"
      query: |
        SELECT well_name, production_date, COUNT(*)
        FROM data
        GROUP BY well_name, production_date
        HAVING COUNT(*) > 1
      message: "Duplicate records found"
      
    # External validator
    - name: "api_validation"
      type: "external"
      module: "custom_validators"
      function: "validate_api_number"
      parameters:
        strict: true
        
    # Temporal rules
    - name: "production_decline"
      type: "temporal"
      window: 30  # days
      check: "decline_rate"
      threshold: 0.5  # 50% decline
      message: "Rapid production decline detected"
```

## Workflow Configuration

Configure verification workflows.

### Basic Workflow

```yaml
# workflow_config.yaml
workflow:
  name: "Standard Verification Workflow"
  description: "Complete verification process"
  version: "1.0"
  
  # Workflow metadata
  metadata:
    author: "Data Team"
    created: "2024-01-01"
    tags: ["production", "verification", "monthly"]
    
  # Workflow parameters
  parameters:
    input_file:
      type: "string"
      required: true
      description: "Input data file"
      
    output_directory:
      type: "string"
      default: "./output"
      description: "Output directory"
      
  # Workflow steps
  steps:
    - id: "load_data"
      name: "Load Production Data"
      type: "data_loader"
      config:
        source: "${input_file}"
        validation: "strict"
        
    - id: "clean_data"
      name: "Clean and Prepare Data"
      type: "data_cleaner"
      depends_on: ["load_data"]
      config:
        remove_duplicates: true
        handle_nulls: "interpolate"
        
    - id: "validate"
      name: "Validate Data"
      type: "validator"
      depends_on: ["clean_data"]
      config:
        rules_file: "validation_rules.yaml"
        stop_on_critical: true
        
    - id: "quality_check"
      name: "Quality Assessment"
      type: "quality_checker"
      depends_on: ["validate"]
      parallel: true
      config:
        checks: ["completeness", "outliers", "consistency"]
        
    - id: "cross_reference"
      name: "Cross-Reference"
      type: "cross_reference"
      depends_on: ["quality_check"]
      optional: true
      config:
        benchmark: "benchmarks.xlsx"
        
    - id: "generate_report"
      name: "Generate Report"
      type: "report_generator"
      depends_on: ["cross_reference"]
      config:
        format: "pdf"
        template: "comprehensive"
        
  # Error handling
  error_handling:
    strategy: "continue"  # Options: stop, continue, retry
    max_retries: 3
    retry_delay: 60
    
    # Step-specific error handling
    step_errors:
      load_data:
        strategy: "stop"
        message: "Cannot proceed without data"
        
      cross_reference:
        strategy: "skip"
        message: "Cross-reference is optional"
        
  # Notifications
  notifications:
    on_start:
      enabled: true
      message: "Workflow ${workflow.name} started"
      
    on_complete:
      enabled: true
      message: "Workflow completed successfully"
      include_summary: true
      
    on_error:
      enabled: true
      message: "Workflow failed: ${error.message}"
      include_stack_trace: false
```

### Conditional Workflow

```yaml
# conditional_workflow.yaml
workflow:
  name: "Conditional Verification"
  
  steps:
    - id: "check_data_size"
      name: "Check Data Size"
      type: "evaluator"
      config:
        expression: "len(data) > 10000"
        
    - id: "large_data_process"
      name: "Large Data Processing"
      type: "batch_processor"
      condition: "${check_data_size.result} == true"
      config:
        batch_size: 5000
        parallel: true
        
    - id: "small_data_process"
      name: "Small Data Processing"
      type: "simple_processor"
      condition: "${check_data_size.result} == false"
      config:
        in_memory: true
        
  # Branching logic
  branches:
    - name: "quality_branch"
      condition: "${validate.quality_score} < 0.8"
      steps:
        - id: "deep_analysis"
          type: "deep_analyzer"
          config:
            thorough: true
            
    - name: "fast_track"
      condition: "${validate.quality_score} >= 0.95"
      steps:
        - id: "quick_report"
          type: "report_generator"
          config:
            template: "summary"
```

## Quality Checks Configuration

Configure data quality assessments.

```yaml
# quality_config.yaml
quality_checks:
  # Completeness checks
  completeness:
    enabled: true
    
    # Overall completeness
    overall_threshold: 0.95
    
    # Field-specific thresholds
    field_thresholds:
      well_name: 1.0  # 100% required
      production_date: 1.0
      oil_production: 0.98
      gas_production: 0.95
      water_production: 0.90  # Optional field
      
    # Temporal completeness
    temporal:
      check_gaps: true
      max_gap_days: 3
      expected_frequency: "daily"
      
    # Reporting
    report:
      include_missing_summary: true
      include_field_statistics: true
      export_missing_records: true
      
  # Outlier detection
  outliers:
    enabled: true
    
    # Detection methods
    methods:
      - type: "z_score"
        threshold: 3.0
        columns: ["oil_production", "gas_production"]
        
      - type: "iqr"
        multiplier: 1.5
        columns: ["water_production"]
        
      - type: "isolation_forest"
        contamination: 0.01
        columns: ["oil_production", "gas_production", "water_production"]
        
    # Outlier handling
    handling:
      flag: true
      remove: false
      cap: false
      cap_percentile: [1, 99]
      
    # Context analysis
    context:
      check_neighbors: true
      neighbor_window: 7  # days
      cluster_analysis: true
      
  # Consistency checks
  consistency:
    enabled: true
    
    # Cross-field rules
    rules:
      - name: "production_sum"
        expression: "total_production == oil_production + gas_production + water_production"
        tolerance: 0.01
        
      - name: "water_cut_calculation"
        expression: "abs(water_cut - (water_production / total_liquids)) < 0.001"
        applies_when: "total_liquids > 0"
        
      - name: "gor_validation"
        expression: "gas_oil_ratio == gas_production / oil_production"
        applies_when: "oil_production > 0"
        
    # Temporal consistency
    temporal:
      - name: "production_continuity"
        check: "no_sudden_zeros"
        window: 7
        threshold: 0.1
        
      - name: "trend_consistency"
        check: "smooth_decline"
        window: 30
        max_change_percent: 20
```

## Cross-Reference Configuration

Configure benchmark comparisons.

```yaml
# cross_reference_config.yaml
cross_reference:
  # Benchmark source
  benchmark:
    file: "production_benchmarks.xlsx"
    sheet: "Q1_2024"
    
    # Alternative sources
    alternatives:
      - file: "backup_benchmarks.csv"
        priority: 2
      - database: "postgresql://host/benchmarks"
        query: "SELECT * FROM benchmarks WHERE period = '2024Q1'"
        priority: 3
        
  # Field mapping
  mapping:
    # Direct mappings
    direct:
      well_name: "Well Name"
      production_date: "Date"
      
    # Fuzzy mappings
    fuzzy:
      oil_production:
        target_patterns: ["Oil.*BBL", "Oil Production", "Oil Vol"]
        threshold: 0.8
        
      gas_production:
        target_patterns: ["Gas.*MCF", "Gas Production", "Gas Vol"]
        threshold: 0.8
        
    # Calculated mappings
    calculated:
      total_production:
        expression: "Oil (BBL) + Gas (MCF) / 6"
        
  # Comparison settings
  comparison:
    # Numeric comparison
    numeric:
      tolerance_percent: 5
      tolerance_absolute: 100
      use_relative: true
      
    # String comparison
    string:
      case_sensitive: false
      fuzzy_match: true
      fuzzy_threshold: 0.9
      
    # Date comparison
    date:
      tolerance_days: 1
      compare_time: false
      
  # Discrepancy handling
  discrepancies:
    # Severity classification
    severity:
      - level: "info"
        condition: "difference < 2%"
      - level: "warning"
        condition: "difference between 2% and 5%"
      - level: "error"
        condition: "difference > 5%"
        
    # Reporting
    reporting:
      group_by: ["well_name", "severity"]
      include_charts: true
      export_details: true
```

## Audit Configuration

Configure audit trail and compliance.

```yaml
# audit_config.yaml
audit:
  # Database configuration
  database:
    type: "sqlite"  # Options: sqlite, postgresql, mysql
    path: "./audit/verification_audit.db"
    
    # Connection pool (for non-sqlite)
    pool:
      min_connections: 2
      max_connections: 10
      timeout: 30
      
  # Logging configuration
  logging:
    level: "INFO"
    
    # What to log
    events:
      - "session_start"
      - "session_end"
      - "data_load"
      - "validation_start"
      - "validation_complete"
      - "issue_found"
      - "report_generated"
      - "user_action"
      
    # Additional metadata
    metadata:
      capture_user: true
      capture_ip: true
      capture_hostname: true
      capture_input_hash: true
      
  # Compliance configuration
  compliance:
    # Standards to comply with
    standards:
      - name: "SOX"
        requirements:
          - "user_authentication"
          - "change_tracking"
          - "data_integrity"
          - "audit_trail"
          
      - name: "GDPR"
        requirements:
          - "data_minimization"
          - "purpose_limitation"
          - "retention_policy"
          
    # Data retention
    retention:
      audit_logs: 2555  # 7 years
      verification_results: 365  # 1 year
      temporary_data: 30  # 30 days
      
    # Access control
    access_control:
      enabled: true
      roles:
        - name: "viewer"
          permissions: ["read"]
        - name: "operator"
          permissions: ["read", "execute"]
        - name: "admin"
          permissions: ["read", "execute", "configure", "delete"]
```

## Report Configuration

Configure report generation.

```yaml
# report_config.yaml
reporting:
  # Output settings
  output:
    directory: "./reports"
    naming_pattern: "verification_report_{date}_{field}"
    timestamp_format: "%Y%m%d_%H%M%S"
    
  # Report formats
  formats:
    pdf:
      enabled: true
      template: "comprehensive"
      
      # PDF settings
      page_size: "A4"
      orientation: "portrait"
      margins: [20, 20, 20, 20]  # top, right, bottom, left
      
      # Content settings
      include_toc: true
      include_summary: true
      include_charts: true
      include_appendix: true
      
      # Styling
      font_family: "Arial"
      font_size: 10
      header_color: "#003366"
      
    excel:
      enabled: true
      
      # Excel structure
      sheets:
        - name: "Summary"
          content: "summary_stats"
        - name: "Validation Results"
          content: "validation_details"
        - name: "Quality Metrics"
          content: "quality_scores"
        - name: "Issues"
          content: "issue_list"
        - name: "Audit Trail"
          content: "audit_log"
          
      # Formatting
      auto_filter: true
      freeze_panes: true
      conditional_formatting: true
      
    html:
      enabled: false
      template: "interactive"
      include_javascript: true
      include_css: true
      
  # Report sections
  sections:
    summary:
      enabled: true
      metrics: ["total_records", "quality_score", "issue_count"]
      
    validation:
      enabled: true
      group_by: ["severity", "rule_type"]
      include_examples: true
      max_examples: 10
      
    quality:
      enabled: true
      charts: ["completeness_bar", "outlier_scatter", "trend_line"]
      
    recommendations:
      enabled: true
      auto_generate: true
      priority_based: true
      
  # Distribution
  distribution:
    email:
      enabled: false
      smtp_server: "smtp.company.com"
      port: 587
      use_tls: true
      from: "reports@company.com"
      
      recipients:
        - address: "operations@company.com"
          reports: ["summary", "full"]
        - address: "compliance@company.com"
          reports: ["audit", "compliance"]
          
    file_share:
      enabled: false
      path: "\\\\fileserver\\reports"
      
    api:
      enabled: false
      endpoint: "https://api.company.com/reports"
      auth_token: "${REPORT_API_TOKEN}"
```

## Performance Tuning

Optimize verification performance.

```yaml
# performance_config.yaml
performance:
  # Parallel processing
  parallel:
    enabled: true
    workers: 4  # Number of parallel workers
    
    # Worker configuration
    worker_config:
      type: "process"  # Options: thread, process
      memory_limit: 512  # MB per worker
      timeout: 300  # seconds
      
    # Task distribution
    distribution:
      strategy: "round_robin"  # Options: round_robin, load_balanced
      chunk_size: 1000
      
  # Batch processing
  batch:
    enabled: true
    size: 5000
    
    # Adaptive batching
    adaptive:
      enabled: true
      min_size: 100
      max_size: 10000
      target_memory: 1024  # MB
      
  # Caching
  cache:
    enabled: true
    
    # Cache types
    types:
      - type: "memory"
        size_mb: 512
        ttl: 3600
        
      - type: "disk"
        directory: "./.cache"
        size_gb: 10
        ttl: 86400
        
    # What to cache
    cache_items:
      - "validation_rules"
      - "benchmark_data"
      - "calculated_metrics"
      - "report_templates"
      
  # Memory management
  memory:
    max_usage_mb: 4096
    
    # Garbage collection
    gc:
      aggressive: true
      threshold: 0.8  # Trigger at 80% usage
      
    # Data streaming
    streaming:
      enabled: true
      chunk_size: 10000
      
  # Database optimization
  database:
    # Connection pooling
    pool:
      min_size: 2
      max_size: 20
      timeout: 30
      
    # Query optimization
    query:
      use_prepared_statements: true
      batch_inserts: true
      batch_size: 1000
      
    # Indexing
    indexes:
      - "well_name"
      - "production_date"
      - ["well_name", "production_date"]
```

## Environment-Specific Configuration

Configure for different environments.

### Development Configuration

```yaml
# config/development.yaml
extends: "base_config.yaml"

verification:
  data_source:
    file: "test_data/sample_production.csv"
    
  validation:
    max_errors: 1000  # Show more errors in dev
    
  performance:
    parallel_workers: 2  # Less workers for dev
    
  logging:
    level: "DEBUG"
    
  reporting:
    output_directory: "./dev_reports"
    
  audit:
    database: "./dev_audit.db"
```

### Production Configuration

```yaml
# config/production.yaml
extends: "base_config.yaml"

verification:
  data_source:
    database:
      connection_string: "${PROD_DB_CONNECTION}"
      
  validation:
    stop_on_error: true
    max_errors: 10
    
  performance:
    parallel_workers: 16
    batch_size: 10000
    
  logging:
    level: "WARNING"
    file: "/var/log/verification/production.log"
    
  reporting:
    output_directory: "/data/reports/production"
    distribution:
      email:
        enabled: true
        
  audit:
    database:
      type: "postgresql"
      connection_string: "${AUDIT_DB_CONNECTION}"
    compliance:
      standards: ["SOX", "GDPR", "HIPAA"]
```

### Testing Configuration

```yaml
# config/testing.yaml
extends: "base_config.yaml"

verification:
  data_source:
    file: "test_fixtures/test_data.csv"
    
  validation:
    enabled: true
    stop_on_error: false
    
  quality:
    completeness:
      threshold: 0.90  # Lower threshold for tests
      
  performance:
    parallel_workers: 1  # Single threaded for tests
    cache:
      enabled: false  # No caching in tests
      
  audit:
    enabled: false  # No audit in tests
    
  reporting:
    formats: ["json"]  # Only JSON for test assertions
```

## Configuration Best Practices

1. **Use Environment Variables**: Store sensitive data in environment variables
   ```yaml
   database:
     connection_string: "${DATABASE_URL}"
     password: "${DB_PASSWORD}"
   ```

2. **Layer Configurations**: Use base configs with environment-specific overrides
   ```yaml
   extends: "base_config.yaml"
   # Override specific values
   ```

3. **Validate Configurations**: Always validate before use
   ```python
   config = VerificationConfig.from_yaml("config.yaml")
   errors = config.validate()
   if errors:
       raise ConfigurationError(errors)
   ```

4. **Version Control**: Track configuration changes
   ```yaml
   metadata:
     version: "1.2.3"
     last_modified: "2024-01-15"
     modified_by: "data_team"
   ```

5. **Document Options**: Include descriptions and examples
   ```yaml
   # Outlier detection method
   # Options: iqr, z_score, isolation_forest
   # Default: iqr
   method: "iqr"
   ```

This configuration guide provides comprehensive coverage of all configuration options in the Well Data Verification System.