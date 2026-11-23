# SODIR API Integration Guide

> Module: sodir  
> Version: 1.0.0  
> Last Updated: 2025-09-03  
> API Endpoint: factmaps.sodir.no/api/rest  

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [API Client Usage](#api-client-usage)
4. [Data Types and Endpoints](#data-types-and-endpoints)
5. [Advanced Features](#advanced-features)
6. [Error Handling](#error-handling)
7. [Performance Considerations](#performance-considerations)
8. [Code Examples](#code-examples)

## Overview

The SODIR (Norwegian Offshore Directorate) API integration provides access to comprehensive petroleum data from the Norwegian Continental Shelf. This module offers:

- **Complete REST API Integration**: Full access to blocks, wellbores, fields, discoveries, and surveys
- **Robust Error Handling**: Automatic retry logic with exponential backoff
- **Rate Limiting**: Maintains 10 requests/second limit to respect API guidelines
- **24-Hour Caching**: Reduces API load and improves performance
- **Data Processing**: Automatic unit conversion and normalization

## Getting Started

### Basic Usage

```python
from tests.modules.sodir_module.api_client import SodirAPIClient
from tests.modules.sodir_module.sodir import SodirModule

# Initialize the API client
api_client = SodirAPIClient()

# Or use the module router for comprehensive functionality
sodir = SodirModule()

# Fetch field data
fields = await api_client.fetch_fields()
print(f"Retrieved {len(fields)} Norwegian fields")

# Process and analyze the data
analysis_results = sodir.analyze_fields(fields)
```

### With Configuration File

```python
import yaml
from tests.modules.sodir_module.sodir import SodirModule

# Load configuration
with open("configs/sodir.yml", "r") as f:
    config = yaml.safe_load(f)

# Initialize with configuration
sodir = SodirModule(config=config)

# Collect data based on configuration
data = sodir.collect_data()
```

## API Client Usage

### Initialization Options

```python
from tests.modules.sodir_module.api_client import SodirAPIClient

# Default initialization
client = SodirAPIClient()

# Custom rate limiting
client = SodirAPIClient(rate_limit=5)  # 5 requests per second

# With caching disabled
client = SodirAPIClient(enable_cache=False)

# Custom timeout
client = SodirAPIClient(timeout=60)  # 60 seconds
```

### Making API Requests

```python
import asyncio

async def fetch_all_data():
    """Fetch all available data types from SODIR."""
    client = SodirAPIClient()
    
    # Fetch different data types
    blocks = await client.fetch_blocks()
    wellbores = await client.fetch_wellbores()
    fields = await client.fetch_fields()
    discoveries = await client.fetch_discoveries()
    surveys = await client.fetch_surveys()
    
    return {
        "blocks": blocks,
        "wellbores": wellbores,
        "fields": fields,
        "discoveries": discoveries,
        "surveys": surveys
    }

# Run the async function
data = asyncio.run(fetch_all_data())
```

## Data Types and Endpoints

### 1. Blocks (Type 1001)

Represents licensed blocks on the Norwegian Continental Shelf.

```python
# Fetch all blocks
blocks = await client.fetch_blocks()

# Example block structure
{
    "block_name": "35/2",
    "status": "PRODUCING",
    "operator": "Equinor Energy AS",
    "area_km2": 456.78,
    "water_depth_m": 350,
    "utm_north": 7234567,
    "utm_east": 456789,
    "utm_zone": 31
}
```

### 2. Wellbores (Type 5000)

Drilling and completion data for exploration and production wells.

```python
# Fetch all wellbores
wellbores = await client.fetch_wellbores()

# Example wellbore structure
{
    "wellbore_name": "35/2-1",
    "well_type": "EXPLORATION",
    "status": "PLUGGED AND ABANDONED",
    "total_depth_m": 4567,
    "water_depth_m": 350,
    "drill_date": "2020-05-15",
    "operator": "Equinor Energy AS"
}

# Filter by status
active_wells = [w for w in wellbores if w["status"] == "PRODUCING"]
```

### 3. Fields (Type 7100)

Production field information including reserves and economics.

```python
# Fetch all fields
fields = await client.fetch_fields()

# Example field structure
{
    "field_name": "JOHAN SVERDRUP",
    "status": "PRODUCING",
    "discovery_year": 2010,
    "production_start": 2019,
    "recoverable_oil_sm3": 350000000,
    "recoverable_gas_bsm3": 8000,
    "recovery_factor_oil": 0.70,
    "operator": "Equinor Energy AS"
}

# Convert units (Sm³ to barrels)
from tests.modules.sodir_module.processors.field_processor import FieldProcessor
processor = FieldProcessor()
fields_imperial = [processor.process(f, units="imperial") for f in fields]
```

### 4. Discoveries (Type 7000)

Hydrocarbon discoveries not yet in production.

```python
# Fetch all discoveries
discoveries = await client.fetch_discoveries()

# Example discovery structure
{
    "discovery_name": "35/2-1 FRAM",
    "discovery_year": 2019,
    "resource_estimate_sm3": 5000000,
    "discovery_type": "OIL",
    "evaluation_status": "UNDER EVALUATION",
    "operator": "Aker BP ASA"
}

# Filter recent discoveries
recent = [d for d in discoveries if d["discovery_year"] >= 2020]
```

### 5. Surveys (Type 4000)

Seismic and geological survey data.

```python
# Fetch all surveys
surveys = await client.fetch_surveys()

# Example survey structure
{
    "survey_id": "ST2020001",
    "survey_type": "3D_SEISMIC",
    "acquisition_year": 2020,
    "coverage_km2": 1234,
    "contractor": "PGS",
    "data_quality": "GOOD"
}
```

## Advanced Features

### Parallel Data Fetching

```python
from tests.modules.sodir_module.parallel import ParallelProcessor

async def fetch_parallel():
    """Fetch all data types in parallel for maximum efficiency."""
    processor = ParallelProcessor()
    
    # Define fetch tasks
    tasks = {
        "blocks": client.fetch_blocks,
        "wellbores": client.fetch_wellbores,
        "fields": client.fetch_fields,
        "discoveries": client.fetch_discoveries,
        "surveys": client.fetch_surveys
    }
    
    # Execute in parallel
    results = await processor.process_api_parallel(tasks)
    return results

# Parallel fetch completes much faster
data = asyncio.run(fetch_parallel())
```

### Batch Processing with Checkpoints

```python
from tests.modules.sodir_module.batch import BatchProcessor

# Initialize batch processor
batch_processor = BatchProcessor(config={
    "batch_size": 100,
    "enable_checkpointing": True,
    "checkpoint_dir": "checkpoints/sodir"
})

# Process large dataset with automatic checkpointing
results = batch_processor.process_batch(
    data_type="wellbores",
    processor=WellboreProcessor(),
    resume=True  # Resume from last checkpoint if interrupted
)
```

### Caching Strategies

```python
from tests.modules.sodir_module.cache_optimizer import CacheOptimizer

# Initialize optimized cache
cache = CacheOptimizer(
    max_size_mb=500,
    eviction_strategy="lfu",  # Least Frequently Used
    enable_predictive=True
)

# Pre-warm cache with common queries
await cache.warm_cache([
    "blocks",
    "fields",
    "recent_wellbores"
])

# Use cached data
fields = cache.get_or_fetch("fields", client.fetch_fields)
```

## Error Handling

### Retry Logic

The API client automatically retries failed requests with exponential backoff:

```python
# Automatic retry configuration
MAX_RETRIES = 5
RETRY_DELAY = 10  # seconds
BACKOFF_FACTOR = 2

# Custom retry configuration
from tests.modules.sodir_module.errors import SodirAPIError
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def fetch_with_custom_retry():
    try:
        return await client.fetch_fields()
    except SodirAPIError as e:
        print(f"API error: {e}")
        raise
```

### Exception Handling

```python
from tests.modules.sodir_module.errors import (
    SodirAPIError,
    SodirRateLimitError,
    SodirAuthenticationError,
    SodirDataNotFoundError
)

try:
    data = await client.fetch_fields()
except SodirRateLimitError:
    # Wait and retry
    await asyncio.sleep(60)
    data = await client.fetch_fields()
except SodirAuthenticationError:
    # Re-authenticate
    client.reset_session()
    data = await client.fetch_fields()
except SodirDataNotFoundError as e:
    print(f"Data not found: {e}")
    data = []
except SodirAPIError as e:
    print(f"General API error: {e}")
    raise
```

## Performance Considerations

### Rate Limiting

The client enforces a rate limit of 10 requests per second:

```python
# Rate limiting is automatic
for block_id in block_ids[:100]:
    # Client automatically throttles requests
    block_data = await client.fetch_block_details(block_id)
```

### Memory Management

For large datasets, use streaming and batch processing:

```python
# Stream large datasets
async def stream_wellbores():
    """Stream wellbores in chunks to manage memory."""
    offset = 0
    batch_size = 1000
    
    while True:
        batch = await client.fetch_wellbores(
            offset=offset,
            limit=batch_size
        )
        
        if not batch:
            break
            
        # Process batch
        process_batch(batch)
        
        # Clear batch from memory
        del batch
        
        offset += batch_size
```

### Connection Pooling

```python
# The client uses connection pooling by default
# Adjust pool size for heavy workloads
import httpx

client = SodirAPIClient(
    session_config={
        "limits": httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100
        )
    }
)
```

## Code Examples

### Complete Data Collection Workflow

```python
import asyncio
from datetime import datetime
from tests.modules.sodir_module.sodir import SodirModule
from tests.modules.sodir_module.storage import DataStorage

async def complete_workflow():
    """Complete workflow from collection to storage."""
    
    # Initialize components
    sodir = SodirModule()
    storage = DataStorage(base_path="data/sodir")
    
    # Collect all data
    print(f"Starting data collection at {datetime.now()}")
    data = await sodir.collect_all_data()
    
    # Process data
    print("Processing collected data...")
    processed = sodir.process_data(data)
    
    # Generate analysis datasets
    print("Generating analysis datasets...")
    datasets = sodir.generate_datasets(processed)
    
    # Store results
    print("Saving to storage...")
    storage.save(datasets, format="parquet")
    
    # Export summary
    storage.export_summary(
        datasets,
        output_path="exports/sodir_summary.xlsx"
    )
    
    print("Workflow completed successfully!")
    return datasets

# Run workflow
datasets = asyncio.run(complete_workflow())
```

### Cross-Regional Comparison

```python
from tests.modules.sodir_module.cross_regional import CrossRegionalAnalyzer

# Initialize analyzer
analyzer = CrossRegionalAnalyzer()

# Load data from both regions
sodir_fields = await client.fetch_fields()
bsee_fields = load_bsee_fields()  # Assuming BSEE data is available

# Normalize for comparison
normalized_sodir = analyzer.normalize_sodir_data(sodir_fields)
normalized_bsee = analyzer.normalize_bsee_data(bsee_fields)

# Perform comparison
comparison = analyzer.compare_regions(normalized_sodir, normalized_bsee)

# Generate report
report = analyzer.generate_comparison_report(comparison)
print(report)
```

### Production Analysis

```python
from tests.modules.sodir_module.analysis import SodirAnalysis
from tests.modules.sodir_module.forecasting import ProductionForecaster

# Initialize analysis
analysis = SodirAnalysis()
forecaster = ProductionForecaster()

# Analyze field production
field_data = await client.fetch_fields()
production_analysis = analysis.analyze_production(field_data)

# Forecast future production
forecast = forecaster.forecast_field_production(
    field_name="JOHAN SVERDRUP",
    historical_data=production_analysis["historical"],
    method="hyperbolic_decline",
    years_ahead=10
)

# Visualize results
from tests.modules.sodir_module.visualization import SodirVisualizer
viz = SodirVisualizer()
viz.plot_production_forecast(forecast)
```

## Best Practices

1. **Always use async/await** for API calls to maximize efficiency
2. **Enable caching** for production environments to reduce API load
3. **Implement proper error handling** for network failures
4. **Use batch processing** for large datasets
5. **Monitor rate limits** to avoid API throttling
6. **Validate data** after processing to ensure quality
7. **Use configuration files** for flexible deployments
8. **Implement logging** for debugging and monitoring

## Troubleshooting

### Common Issues

1. **Rate Limit Errors**: Reduce concurrent requests or add delays
2. **Timeout Errors**: Increase timeout or retry with smaller batches
3. **Memory Issues**: Use streaming and batch processing
4. **Cache Misses**: Pre-warm cache for common queries
5. **Data Quality**: Validate and clean data after fetching

### Debug Mode

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Initialize client with debug mode
client = SodirAPIClient(debug=True)

# Debug information will be printed
data = await client.fetch_fields()
```

## Related Documentation

- [Configuration Guide](config_guide.md) - YAML configuration reference
- [Cross-Regional Tutorial](cross_regional_tutorial.md) - Comparing SODIR and BSEE data
- [Module README](README.md) - Module overview and quick start

---

*For questions or issues, please refer to the WorldEnergyData documentation or contact the development team.*