# SODIR Configuration Guide

> Module: sodir  
> Version: 1.0.0  
> Last Updated: 2025-09-03  
> Configuration Format: YAML  

## Table of Contents

1. [Overview](#overview)
2. [Configuration Structure](#configuration-structure)
3. [Core Settings](#core-settings)
4. [Data Collection Options](#data-collection-options)
5. [Processing Parameters](#processing-parameters)
6. [Storage Configuration](#storage-configuration)
7. [Analysis Settings](#analysis-settings)
8. [Performance Tuning](#performance-tuning)
9. [Example Configurations](#example-configurations)

## Overview

The SODIR module uses YAML configuration files to control data collection, processing, and analysis workflows. This guide covers all available configuration parameters and their usage.

## Configuration Structure

The configuration file follows a hierarchical structure:

```yaml
sodir:
  api:
    # API connection settings
  data_collection:
    # Data types and filters
  processing:
    # Processing options
  storage:
    # Storage paths and formats
  analysis:
    # Analysis parameters
  performance:
    # Performance optimization
```

## Core Settings

### Basic Configuration Template

```yaml
# configs/sodir.yml
sodir:
  # Module version for compatibility checking
  version: "1.0.0"
  
  # Enable/disable the module
  enabled: true
  
  # Logging configuration
  logging:
    level: "INFO"  # DEBUG, INFO, WARNING, ERROR
    file: "logs/sodir.log"
    rotate: true
    max_size: "10MB"
  
  # Module metadata
  metadata:
    description: "SODIR Norwegian Continental Shelf Data Integration"
    author: "WorldEnergyData Team"
    last_modified: "2025-09-03"
```

## Data Collection Options

### API Configuration

```yaml
sodir:
  api:
    # Base URL for SODIR API
    base_url: "https://factmaps.sodir.no/api/rest"
    
    # Request timeout in seconds
    timeout: 30
    
    # Rate limiting
    rate_limit:
      requests_per_second: 10
      burst_size: 20
      wait_on_limit: true
    
    # Retry configuration
    retry:
      max_attempts: 5
      initial_delay: 10  # seconds
      backoff_factor: 2
      max_delay: 300
    
    # Connection pooling
    connection:
      max_connections: 100
      keepalive_connections: 20
      keepalive_expiry: 300  # seconds
```

### Data Types Selection

```yaml
sodir:
  data_collection:
    # Select which data types to collect
    data_types:
      blocks:
        enabled: true
        type_id: 1001
        filters:
          status: ["PRODUCING", "EXPLORATION"]
          area: ["NORTH_SEA", "NORWEGIAN_SEA", "BARENTS_SEA"]
      
      wellbores:
        enabled: true
        type_id: 5000
        filters:
          well_type: ["EXPLORATION", "PRODUCTION", "APPRAISAL"]
          min_depth_m: 1000
          max_depth_m: 10000
          year_from: 2010
      
      fields:
        enabled: true
        type_id: 7100
        filters:
          status: ["PRODUCING", "SHUT_DOWN"]
          min_recoverable_oil_sm3: 1000000
      
      discoveries:
        enabled: true
        type_id: 7000
        filters:
          discovery_year_from: 2015
          resource_type: ["OIL", "GAS", "OIL_GAS"]
      
      surveys:
        enabled: true
        type_id: 4000
        filters:
          survey_type: ["2D_SEISMIC", "3D_SEISMIC", "4D_SEISMIC"]
          year_from: 2018
```

### Collection Schedule

```yaml
sodir:
  data_collection:
    # Scheduling for automated collection
    schedule:
      enabled: true
      cron: "0 2 * * *"  # Daily at 2 AM
      timezone: "Europe/Oslo"
      
    # Incremental updates
    incremental:
      enabled: true
      lookback_days: 7
      full_refresh_interval: 30  # days
```

## Processing Parameters

### Data Processing Options

```yaml
sodir:
  processing:
    # Unit system for output
    units:
      system: "dual"  # metric, imperial, or dual
      
      # Specific unit preferences
      oil_volume: "both"  # sm3, barrels, or both
      gas_volume: "both"  # bsm3, bcf, or both
      depth: "meters"      # meters or feet
      pressure: "bar"      # bar or psi
      temperature: "celsius"  # celsius or fahrenheit
    
    # Coordinate system
    coordinates:
      output_format: "WGS84"  # WGS84 or UTM
      include_utm: true
      decimal_places: 6
    
    # Data validation
    validation:
      enabled: true
      strict_mode: false
      log_warnings: true
      
      # Validation rules
      rules:
        check_coordinates: true
        validate_dates: true
        check_numeric_ranges: true
        verify_references: true
    
    # Data quality
    quality:
      remove_duplicates: true
      handle_missing:
        strategy: "flag"  # flag, drop, or impute
        flag_value: "NO_DATA"
      
      # Outlier detection
      outliers:
        detect: true
        method: "iqr"  # iqr or zscore
        threshold: 3
        action: "flag"  # flag or remove
```

### Normalization Settings

```yaml
sodir:
  processing:
    normalization:
      # Standardize field names
      standardize_names: true
      name_mapping:
        "wellbore_name": "well_name"
        "discovery_wellbore": "discovery_well"
      
      # Date formatting
      date_format: "%Y-%m-%d"
      datetime_format: "%Y-%m-%d %H:%M:%S"
      
      # Status normalization
      status_mapping:
        "P&A": "PLUGGED_ABANDONED"
        "PROD": "PRODUCING"
        "EXPL": "EXPLORATION"
```

## Storage Configuration

### File Storage Options

```yaml
sodir:
  storage:
    # Base directory for all data
    base_path: "data/sodir"
    
    # Directory structure
    structure:
      raw: "raw/{data_type}/{year}/{month}"
      processed: "processed/{data_type}"
      analysis: "analysis/{analysis_type}"
      cache: "cache"
      exports: "exports/{export_date}"
    
    # File formats
    formats:
      raw: "json"         # json or csv
      processed: "parquet"  # parquet, csv, or json
      analysis: "parquet"
      exports: "excel"    # excel, csv, or json
    
    # Compression
    compression:
      enabled: true
      algorithm: "gzip"  # gzip, bz2, or xz
      level: 6  # 1-9
    
    # Retention policy
    retention:
      raw_data: 90  # days
      processed_data: 365
      cache: 7
      exports: 30
```

### Cache Configuration

```yaml
sodir:
  storage:
    cache:
      # Cache settings
      enabled: true
      type: "hybrid"  # memory, disk, or hybrid
      
      # Memory cache
      memory:
        max_size_mb: 500
        ttl_hours: 24
        eviction: "lru"  # lru, lfu, or fifo
      
      # Disk cache
      disk:
        path: "cache/sodir"
        max_size_gb: 10
        ttl_days: 7
      
      # Cache warming
      warm_on_start: true
      warm_queries:
        - "active_fields"
        - "recent_wellbores"
        - "producing_blocks"
```

## Analysis Settings

### Analysis Configuration

```yaml
sodir:
  analysis:
    # Field analysis
    fields:
      calculate_economics: true
      npv_parameters:
        discount_rate: 0.08
        oil_price_usd: 80
        gas_price_usd_mmbtu: 4
        tax_rate: 0.78  # Norwegian petroleum tax
      
      # Recovery analysis
      recovery:
        calculate_efficiency: true
        benchmark_recovery: 0.45
    
    # Production analysis
    production:
      forecast:
        enabled: true
        methods: ["exponential", "hyperbolic", "harmonic"]
        forecast_years: 10
      
      decline_analysis:
        enabled: true
        min_production_months: 12
    
    # Cross-regional comparison
    cross_regional:
      enabled: true
      compare_with: ["BSEE"]
      metrics:
        - "drilling_efficiency"
        - "recovery_factors"
        - "discovery_success_rate"
        - "production_curves"
```

### Visualization Settings

```yaml
sodir:
  analysis:
    visualization:
      # Chart settings
      charts:
        theme: "seaborn"
        dpi: 300
        format: "png"  # png, svg, or pdf
        save_path: "reports/charts"
      
      # Map settings
      maps:
        projection: "mercator"
        include_boundaries: true
        color_scheme: "viridis"
        
        # Norwegian Continental Shelf bounds
        bounds:
          north: 72.0
          south: 56.0
          east: 35.0
          west: -5.0
      
      # Dashboard
      dashboard:
        enabled: true
        refresh_interval: 3600  # seconds
        export_format: "html"
```

## Performance Tuning

### Parallel Processing

```yaml
sodir:
  performance:
    parallel:
      enabled: true
      
      # Worker configuration
      workers:
        api_fetch: 5     # Concurrent API requests
        processing: 8    # CPU cores for processing
        analysis: 4      # Analysis workers
      
      # Batch processing
      batch:
        size: 1000
        queue_size: 10000
        timeout: 300  # seconds per batch
    
    # Memory management
    memory:
      max_usage_gb: 8
      garbage_collection:
        enabled: true
        threshold: 0.8  # Trigger at 80% usage
      
      # Streaming for large datasets
      streaming:
        enabled: true
        chunk_size: 10000
```

### Monitoring

```yaml
sodir:
  performance:
    monitoring:
      enabled: true
      
      # Metrics collection
      metrics:
        collect_interval: 60  # seconds
        export_path: "metrics/sodir"
        
        track:
          - "api_response_time"
          - "processing_throughput"
          - "cache_hit_rate"
          - "memory_usage"
          - "error_rate"
      
      # Alerts
      alerts:
        enabled: true
        channels: ["log", "email"]
        
        thresholds:
          error_rate: 0.05  # 5%
          api_timeout_rate: 0.1
          memory_usage: 0.9  # 90%
```

## Example Configurations

### Minimal Configuration

```yaml
# Minimal configuration for basic data collection
sodir:
  enabled: true
  api:
    base_url: "https://factmaps.sodir.no/api/rest"
  data_collection:
    data_types:
      fields:
        enabled: true
      wellbores:
        enabled: true
```

### Production Configuration

```yaml
# Production environment configuration
sodir:
  enabled: true
  
  logging:
    level: "INFO"
    file: "/var/log/sodir/sodir.log"
    rotate: true
  
  api:
    base_url: "https://factmaps.sodir.no/api/rest"
    timeout: 60
    rate_limit:
      requests_per_second: 10
    retry:
      max_attempts: 5
  
  data_collection:
    data_types:
      blocks: { enabled: true }
      wellbores: { enabled: true }
      fields: { enabled: true }
      discoveries: { enabled: true }
      surveys: { enabled: true }
    
    schedule:
      enabled: true
      cron: "0 2 * * *"
    
    incremental:
      enabled: true
  
  processing:
    units:
      system: "dual"
    validation:
      enabled: true
      strict_mode: true
  
  storage:
    base_path: "/data/sodir"
    formats:
      processed: "parquet"
    compression:
      enabled: true
    cache:
      enabled: true
      type: "hybrid"
  
  analysis:
    fields:
      calculate_economics: true
    cross_regional:
      enabled: true
  
  performance:
    parallel:
      enabled: true
      workers:
        api_fetch: 10
        processing: 16
    monitoring:
      enabled: true
      alerts:
        enabled: true
```

### Development Configuration

```yaml
# Development environment configuration
sodir:
  enabled: true
  
  logging:
    level: "DEBUG"
    file: "logs/sodir_dev.log"
  
  api:
    base_url: "https://factmaps.sodir.no/api/rest"
    timeout: 10
    rate_limit:
      requests_per_second: 2  # Lower for development
  
  data_collection:
    data_types:
      fields:
        enabled: true
        filters:
          status: ["PRODUCING"]
          # Limit to specific fields for testing
          field_names: ["JOHAN SVERDRUP", "TROLL", "EKOFISK"]
  
  processing:
    validation:
      enabled: true
      strict_mode: false  # More lenient for development
      log_warnings: true
  
  storage:
    base_path: "test_data/sodir"
    cache:
      enabled: false  # Disable cache for testing
  
  performance:
    parallel:
      enabled: false  # Sequential for debugging
```

### Research Configuration

```yaml
# Configuration for research and analysis
sodir:
  enabled: true
  
  data_collection:
    data_types:
      blocks: { enabled: true }
      wellbores: { enabled: true }
      fields: { enabled: true }
      discoveries: { enabled: true }
      surveys: { enabled: true }
    
    # Collect all historical data
    filters:
      year_from: 1970
  
  processing:
    units:
      system: "metric"  # Consistent units for analysis
    quality:
      remove_duplicates: true
      outliers:
        detect: true
        method: "zscore"
        action: "flag"
  
  analysis:
    fields:
      calculate_economics: true
      npv_parameters:
        # Multiple scenarios
        scenarios:
          - name: "base"
            oil_price_usd: 80
            gas_price_usd_mmbtu: 4
          - name: "high"
            oil_price_usd: 100
            gas_price_usd_mmbtu: 6
          - name: "low"
            oil_price_usd: 60
            gas_price_usd_mmbtu: 3
    
    production:
      forecast:
        enabled: true
        methods: ["exponential", "hyperbolic", "harmonic", "ensemble"]
        forecast_years: 20
        confidence_intervals: [0.1, 0.9]
    
    cross_regional:
      enabled: true
      compare_with: ["BSEE", "UK", "BRAZIL"]
      statistical_tests: true
```

## Configuration Validation

### Using Configuration Validator

```python
from tests.modules.sodir_module.config_validator import validate_config
import yaml

# Load configuration
with open("configs/sodir.yml", "r") as f:
    config = yaml.safe_load(f)

# Validate configuration
is_valid, errors = validate_config(config)

if not is_valid:
    print("Configuration errors:")
    for error in errors:
        print(f"  - {error}")
else:
    print("Configuration is valid!")
```

### Common Configuration Errors

1. **Missing required fields**: Ensure all required fields are present
2. **Invalid data types**: Check that values match expected types
3. **Out of range values**: Verify numeric values are within valid ranges
4. **Invalid cron expressions**: Use standard cron format
5. **Path permissions**: Ensure write access to specified directories

## Environment Variables

Configuration values can be overridden using environment variables:

```bash
# Override API settings
export SODIR_API_BASE_URL="https://custom.api.url"
export SODIR_API_TIMEOUT=120
export SODIR_RATE_LIMIT=5

# Override storage paths
export SODIR_DATA_PATH="/custom/data/path"
export SODIR_CACHE_ENABLED=false

# Override logging
export SODIR_LOG_LEVEL=DEBUG
```

## Best Practices

1. **Version control**: Keep configuration files in version control
2. **Environment-specific**: Use separate configs for dev/staging/production
3. **Secrets management**: Never store credentials in configuration files
4. **Validation**: Always validate configuration before deployment
5. **Documentation**: Comment complex configuration sections
6. **Defaults**: Provide sensible defaults for optional parameters
7. **Monitoring**: Enable monitoring in production environments
8. **Backup**: Keep backup copies of production configurations

## Related Documentation

- [API Guide](api_guide.md) - API usage and examples
- [Cross-Regional Tutorial](cross_regional_tutorial.md) - Comparative analysis setup
- [Module README](README.md) - Quick start guide

---

*For configuration support, consult the WorldEnergyData documentation or development team.*