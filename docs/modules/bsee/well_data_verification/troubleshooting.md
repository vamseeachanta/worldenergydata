# Troubleshooting Guide and FAQs

## Table of Contents
1. [Common Issues](#common-issues)
2. [Error Messages](#error-messages)
3. [Performance Issues](#performance-issues)
4. [Data Issues](#data-issues)
5. [Configuration Problems](#configuration-problems)
6. [Integration Issues](#integration-issues)
7. [FAQs](#faqs)
8. [Getting Help](#getting-help)

## Common Issues

### Installation Issues

#### Problem: Module Import Error
```python
ImportError: No module named 'worldenergydata.analysis.verification'
```

**Solution:**
1. Ensure the package is installed:
   ```bash
   pip install -e .
   # or with uv
   uv pip install -e .
   ```

2. Check Python path:
   ```python
   import sys
   print(sys.path)
   # Ensure project directory is in path
   ```

3. Verify module structure:
   ```bash
   ls -la src/worldenergydata/modules/analysis/verification/
   ```

#### Problem: Missing Dependencies
```
ERROR: jsonschema not found
```

**Solution:**
```bash
# Install required dependencies
uv pip install jsonschema openpyxl reportlab pandas numpy pyyaml

# Or install from requirements
uv pip install -r requirements.txt
```

### CLI Issues

#### Problem: Command Not Found
```bash
$ wdv verify --help
bash: wdv: command not found
```

**Solution:**
1. Use full module path:
   ```bash
   python -m worldenergydata.analysis.verification.cli --help
   ```

2. Or create an alias:
   ```bash
   alias wdv="python -m worldenergydata.analysis.verification.cli"
   ```

#### Problem: Invalid Arguments
```
Error: Invalid value for '--format': 'json' is not one of 'pdf', 'excel', 'both'
```

**Solution:**
Check valid options using help:
```bash
python -m worldenergydata.analysis.verification.cli verify --help
```

## Error Messages

### Verification Errors

#### Error: `VerificationError: No data to verify`

**Cause:** Empty or invalid data file

**Solution:**
1. Check file exists and has data:
   ```bash
   head -n 10 production_data.csv
   wc -l production_data.csv
   ```

2. Verify file format:
   ```python
   import pandas as pd
   data = pd.read_csv("production_data.csv")
   print(data.info())
   ```

#### Error: `ValidationError: Required columns missing`

**Cause:** Data file missing required columns

**Solution:**
1. Check required columns in config:
   ```yaml
   # verification_config.yaml
   validation:
     required_fields: ["well_name", "production_date", "oil_production"]
   ```

2. Verify columns in data:
   ```python
   data = pd.read_csv("production_data.csv")
   print(data.columns.tolist())
   ```

3. Rename columns if needed:
   ```python
   data = data.rename(columns={
       'Well': 'well_name',
       'Date': 'production_date',
       'Oil_BBL': 'oil_production'
   })
   ```

#### Error: `ConfigurationError: Invalid configuration`

**Cause:** Malformed YAML configuration

**Solution:**
1. Validate YAML syntax:
   ```python
   import yaml
   with open("config.yaml") as f:
       config = yaml.safe_load(f)
   ```

2. Check for common YAML errors:
   - Incorrect indentation
   - Missing colons
   - Unclosed quotes
   - Tab characters (use spaces)

3. Use configuration validator:
   ```python
   from worldenergydata.analysis.verification.config import VerificationConfig
   config = VerificationConfig.from_yaml("config.yaml")
   errors = config.validate()
   if errors:
       print("Configuration errors:", errors)
   ```

## Performance Issues

### Slow Processing

#### Problem: Verification Takes Too Long

**Symptoms:**
- Processing hangs or takes hours
- High memory usage
- System becomes unresponsive

**Solutions:**

1. **Enable Parallel Processing:**
   ```yaml
   # config.yaml
   performance:
     parallel_workers: 8  # Increase workers
     batch_size: 5000    # Optimize batch size
   ```

2. **Use Batch Processing:**
   ```python
   # Process in chunks
   chunk_size = 10000
   for i in range(0, len(data), chunk_size):
       chunk = data[i:i+chunk_size]
       results = engine.verify_data(chunk)
   ```

3. **Enable Caching:**
   ```yaml
   performance:
     cache:
       enabled: true
       directory: "./.cache"
   ```

4. **Reduce Validation Complexity:**
   ```yaml
   validation:
     stop_on_error: true  # Stop early on errors
     max_errors: 100      # Limit error reporting
   ```

### Memory Issues

#### Problem: Out of Memory Error

**Solutions:**

1. **Stream Large Files:**
   ```python
   # Use chunked reading
   chunks = pd.read_csv("large_file.csv", chunksize=10000)
   for chunk in chunks:
       results = engine.verify_data(chunk)
   ```

2. **Limit Memory Usage:**
   ```yaml
   performance:
     memory_limit_mb: 2048
     streaming:
       enabled: true
       chunk_size: 5000
   ```

3. **Clear Cache Periodically:**
   ```python
   import gc
   
   # Process data
   results = engine.verify_data(data)
   
   # Clear memory
   del data
   gc.collect()
   ```

## Data Issues

### Data Quality Problems

#### Problem: Too Many Validation Errors

**Solutions:**

1. **Clean Data First:**
   ```python
   # Remove obvious issues
   data = data.dropna(subset=['well_name', 'production_date'])
   data = data[data['oil_production'] >= 0]
   ```

2. **Adjust Validation Rules:**
   ```yaml
   validation:
     ranges:
       oil_production:
         min: 0
         max: 150000  # Increase if needed
         severity: "warning"  # Change from "error"
   ```

3. **Use Data Cleaning Workflow:**
   ```python
   from worldenergydata.analysis.verification.utils import DataCleaner
   
   cleaner = DataCleaner()
   cleaned_data = cleaner.clean(data, {
       'remove_duplicates': True,
       'handle_nulls': 'interpolate',
       'fix_dates': True
   })
   ```

#### Problem: Inconsistent Date Formats

**Solutions:**

1. **Specify Date Format:**
   ```yaml
   data_source:
     date_columns: ["production_date"]
     date_format: "%Y-%m-%d"  # or "%m/%d/%Y"
   ```

2. **Use Date Parser:**
   ```python
   data['production_date'] = pd.to_datetime(
       data['production_date'],
       infer_datetime_format=True
   )
   ```

### Cross-Reference Issues

#### Problem: Excel Benchmark Not Matching

**Solutions:**

1. **Check Field Mappings:**
   ```yaml
   cross_reference:
     field_mapping:
       well_name: "Well Name"  # Exact Excel column name
       oil_production: "Oil Production (BBL)"
   ```

2. **Use Fuzzy Matching:**
   ```python
   cross_ref = CrossReferenceModule()
   cross_ref.fuzzy_match_columns(
       threshold=0.8  # 80% similarity
   )
   ```

3. **Adjust Tolerance:**
   ```yaml
   cross_reference:
     tolerance: 0.10  # 10% tolerance instead of 5%
   ```

## Configuration Problems

### YAML Configuration Issues

#### Problem: Configuration Not Loading

**Solutions:**

1. **Check File Path:**
   ```python
   import os
   config_path = "verification_config.yaml"
   if not os.path.exists(config_path):
       print(f"Config file not found: {config_path}")
   ```

2. **Validate YAML Syntax:**
   ```bash
   # Install yamllint
   pip install yamllint
   
   # Check syntax
   yamllint verification_config.yaml
   ```

3. **Use Default Configuration:**
   ```python
   from worldenergydata.analysis.verification.config import get_default_config
   
   config = get_default_config()
   # Modify as needed
   config['verification']['quality_threshold'] = 0.90
   ```

### Environment-Specific Issues

#### Problem: Different Behavior in Production

**Solutions:**

1. **Use Environment-Specific Configs:**
   ```python
   import os
   
   env = os.getenv('ENVIRONMENT', 'development')
   config_file = f"config/{env}.yaml"
   config = VerificationConfig.from_yaml(config_file)
   ```

2. **Check Environment Variables:**
   ```python
   # List all environment variables
   import os
   for key, value in os.environ.items():
       if key.startswith('WDV_'):
           print(f"{key}={value}")
   ```

## Integration Issues

### BSEE Module Integration

#### Problem: Cannot Import BSEE Modules

**Solutions:**

1. **Check Module Installation:**
   ```python
   try:
       from worldenergydata.bsee.data import ProductionDataProcessor
       print("BSEE modules available")
   except ImportError as e:
       print(f"BSEE modules not found: {e}")
   ```

2. **Use Adapter Pattern:**
   ```python
   from worldenergydata.analysis.verification.processors import BSEEDataAdapter
   
   adapter = BSEEDataAdapter()
   # Adapter handles import issues gracefully
   ```

### Database Connection Issues

#### Problem: Cannot Connect to Database

**Solutions:**

1. **Check Connection String:**
   ```python
   import os
   conn_string = os.getenv('DATABASE_URL')
   if not conn_string:
       print("DATABASE_URL not set")
   ```

2. **Test Connection:**
   ```python
   from sqlalchemy import create_engine
   
   try:
       engine = create_engine(conn_string)
       conn = engine.connect()
       print("Connection successful")
       conn.close()
   except Exception as e:
       print(f"Connection failed: {e}")
   ```

## FAQs

### General Questions

**Q: What data formats are supported?**
A: The system supports:
- CSV files (.csv)
- Excel files (.xlsx, .xls)
- JSON files (.json)
- Direct database connections (PostgreSQL, MySQL, SQLite)

**Q: How much data can the system handle?**
A: The system can process:
- Up to 10 million records in memory
- Unlimited records using streaming/batch mode
- Typical performance: 1000+ wells in <30 seconds

**Q: Can I customize validation rules?**
A: Yes, you can:
- Define custom rules in YAML configuration
- Create Python validation functions
- Use regex patterns for string validation
- Set field-specific thresholds

### Workflow Questions

**Q: Can I pause and resume workflows?**
A: Yes, workflows support checkpointing:
```python
# Create checkpoint
checkpoint = engine.create_checkpoint(session)
checkpoint.save("session_checkpoint.json")

# Resume later
session = engine.load_checkpoint("session_checkpoint.json")
```

**Q: How do I run verification on multiple fields?**
A: Use batch processing:
```python
fields = ["Jack", "Mary", "John"]
for field in fields:
    field_data = data[data['field_name'] == field]
    results = engine.verify_data(field_data)
```

**Q: Can I schedule automatic verification?**
A: Yes, use scheduling tools:
```python
import schedule

def run_verification():
    engine.verify_data(load_latest_data())

schedule.every().day.at("06:00").do(run_verification)
```

### Report Questions

**Q: What report formats are available?**
A: The system generates:
- PDF reports with charts and tables
- Excel workbooks with multiple sheets
- HTML interactive reports
- JSON data exports
- CSV summaries

**Q: Can I customize report templates?**
A: Yes:
```yaml
reporting:
  template: "custom_template"
  sections:
    - summary
    - validation_results
    - custom_section
```

**Q: How do I email reports automatically?**
A: Configure email settings:
```yaml
reporting:
  email:
    enabled: true
    smtp_server: "smtp.company.com"
    recipients: ["team@company.com"]
```

### Performance Questions

**Q: How can I speed up verification?**
A: 
1. Enable parallel processing (set workers to CPU count)
2. Use batch processing for large datasets
3. Enable caching for repeated operations
4. Optimize validation rules (remove unnecessary checks)

**Q: Why is memory usage high?**
A:
1. Large datasets loaded entirely in memory
2. Multiple validation results stored
3. Report generation caching

Solutions: Use streaming, clear cache, process in batches

**Q: Can I run verification on a cluster?**
A: Yes, using distributed processing:
```python
from dask.distributed import Client

client = Client('scheduler-address:8786')
results = client.map(engine.verify_data, data_chunks)
```

## Getting Help

### Resources

1. **Documentation:**
   - User Guide: `docs/modules/bsee/well_data_verification/user_guide.md`
   - API Reference: `docs/modules/bsee/well_data_verification/api_reference.md`
   - Configuration Guide: `docs/modules/bsee/well_data_verification/configuration_guide.md`

2. **Code Examples:**
   - Workflow examples: `tests/modules/analysis/well-data-verification/`
   - Configuration templates: `tests/modules/analysis/well-data-verification/configs/`

3. **Source Code:**
   - Main module: `src/worldenergydata/modules/analysis/verification/`
   - Tests: `tests/modules/analysis/well-data-verification/`

### Debug Mode

Enable debug logging for detailed information:

```python
import logging

# Set debug level
logging.basicConfig(level=logging.DEBUG)

# Or in configuration
```

```yaml
logging:
  level: "DEBUG"
  file: "debug.log"
```

### Contact Support

For additional help:

1. **Check existing issues:** Review the issue tracker for similar problems
2. **Create detailed bug report:** Include:
   - Error message and stack trace
   - Configuration file
   - Sample data (if possible)
   - Steps to reproduce
3. **Contact development team:** Reach out to the WorldEnergyData team

### Diagnostic Script

Run this script to gather diagnostic information:

```python
#!/usr/bin/env python
"""Diagnostic script for verification system."""

import sys
import os
import platform
import importlib

def run_diagnostics():
    print("=== System Information ===")
    print(f"Python: {sys.version}")
    print(f"Platform: {platform.platform()}")
    print(f"Working Directory: {os.getcwd()}")
    
    print("\n=== Package Versions ===")
    packages = ['pandas', 'numpy', 'pyyaml', 'jsonschema', 'openpyxl', 'reportlab']
    for pkg in packages:
        try:
            mod = importlib.import_module(pkg)
            version = getattr(mod, '__version__', 'unknown')
            print(f"{pkg}: {version}")
        except ImportError:
            print(f"{pkg}: NOT INSTALLED")
    
    print("\n=== Verification Module ===")
    try:
        from worldenergydata.analysis.verification import VerificationEngine
        print("✓ Verification module imported successfully")
    except ImportError as e:
        print(f"✗ Import error: {e}")
    
    print("\n=== BSEE Modules ===")
    try:
        from worldenergydata.bsee.data import ProductionDataProcessor
        print("✓ BSEE modules available")
    except ImportError as e:
        print(f"✗ BSEE modules not found: {e}")
    
    print("\n=== Environment Variables ===")
    env_vars = ['WDV_CONFIG_DIR', 'WDV_LOG_LEVEL', 'DATABASE_URL']
    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"{var}: {value[:20]}..." if len(value) > 20 else f"{var}: {value}")
        else:
            print(f"{var}: NOT SET")

if __name__ == "__main__":
    run_diagnostics()
```

Save this as `diagnose.py` and run:
```bash
python diagnose.py > diagnostic_report.txt
```

This troubleshooting guide covers the most common issues and provides practical solutions for the Well Data Verification System.