# Performance Tuning Guide

## Table of Contents
1. [Overview](#overview)
2. [Performance Benchmarks](#performance-benchmarks)
3. [Caching Strategies](#caching-strategies)
4. [Parallel Processing](#parallel-processing)
5. [Memory Optimization](#memory-optimization)
6. [Database Optimization](#database-optimization)
7. [Report Generation Optimization](#report-generation-optimization)
8. [Monitoring and Profiling](#monitoring-and-profiling)
9. [Configuration Examples](#configuration-examples)
10. [Troubleshooting Performance Issues](#troubleshooting-performance-issues)

## Overview

The BSEE Comprehensive Report System is designed to handle large-scale data processing efficiently. This guide provides strategies and configurations to optimize performance for various use cases.

### Performance Goals
- **Processing Speed**: 100+ leases in <60 seconds
- **Memory Usage**: <2GB for typical operations
- **Scalability**: Handle entire Gulf of Mexico dataset
- **Concurrency**: Support 10+ simultaneous report generations

## Performance Benchmarks

### Baseline Performance

| Operation | Small Dataset (10 wells) | Medium Dataset (100 wells) | Large Dataset (1000 wells) |
|-----------|-------------------------|---------------------------|---------------------------|
| Data Loading | <1 second | 2-5 seconds | 10-30 seconds |
| Aggregation | <1 second | 3-8 seconds | 30-60 seconds |
| Report Generation | 2-5 seconds | 15-30 seconds | 5-10 minutes |
| Excel Export | 1-2 seconds | 5-10 seconds | 30-60 seconds |
| PDF Export | 2-3 seconds | 10-15 seconds | 60-90 seconds |

### Optimized Performance (with tuning)

| Operation | Small Dataset | Medium Dataset | Large Dataset |
|-----------|--------------|----------------|---------------|
| Data Loading | <0.5 second | 1-2 seconds | 5-10 seconds |
| Aggregation | <0.5 second | 1-3 seconds | 10-20 seconds |
| Report Generation | 1-2 seconds | 5-10 seconds | 2-5 minutes |
| Excel Export | <1 second | 2-5 seconds | 15-30 seconds |
| PDF Export | 1-2 seconds | 5-8 seconds | 30-45 seconds |

## Caching Strategies

### Redis-like In-Memory Caching

The system implements a Redis-like caching mechanism for frequently accessed data.

```yaml
# cache_config.yaml
cache:
  enabled: true
  backend: memory  # memory or redis
  ttl: 3600  # Time to live in seconds
  max_size: 1000  # Maximum cache entries
  
  # Cache specific data types
  cache_levels:
    aggregated_data: true
    well_summaries: true
    production_metrics: true
    calculated_economics: true
    
  # Cache key patterns
  key_patterns:
    aggregation: "{level}:{unit}:{date_range}"
    well_data: "well:{api_number}:{metric}"
    report: "report:{unit}:{template}:{date}"
```

### Implementation Example

```python
from worldenergydata.bsee.reports.comprehensive.cache import CacheManager

# Configure cache
cache_config = {
    'ttl': 3600,  # 1 hour
    'max_size': 1000,
    'eviction_policy': 'lru'  # Least recently used
}

cache = CacheManager(cache_config)

# Use cache in data loading
def load_production_data(unit: str, date_range: tuple):
    # Generate cache key
    cache_key = f"production:{unit}:{date_range[0]}:{date_range[1]}"
    
    # Check cache
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data
    
    # Load data from source
    data = load_from_database(unit, date_range)
    
    # Store in cache
    cache.set(cache_key, data)
    return data
```

### Cache Warming

Pre-populate cache for better performance:

```python
def warm_cache(units: list, date_range: tuple):
    """Pre-load frequently accessed data into cache."""
    
    for unit in units:
        # Load and cache production data
        load_production_data(unit, date_range)
        
        # Load and cache well summaries
        load_well_summaries(unit)
        
        # Pre-calculate and cache aggregations
        calculate_aggregations(unit, date_range)
```

## Parallel Processing

### Multi-threading Configuration

```yaml
# parallel_config.yaml
parallel:
  enabled: true
  max_workers: 4  # Number of parallel workers
  chunk_size: 10  # Units to process per worker
  
  # Operations to parallelize
  operations:
    data_loading: true
    aggregation: true
    report_generation: true
    export: true
    
  # Thread pool settings
  thread_pool:
    type: adaptive  # fixed or adaptive
    min_workers: 2
    max_workers: 8
    queue_size: 100
```

### Parallel Report Generation

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing

class ParallelReportGenerator:
    def __init__(self, max_workers=None):
        # Use CPU count if not specified
        self.max_workers = max_workers or multiprocessing.cpu_count()
        
    def generate_reports(self, units: list, template: str):
        """Generate reports for multiple units in parallel."""
        
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(self.generate_single, unit, template): unit
                for unit in units
            }
            
            # Process completed tasks
            for future in as_completed(futures):
                unit = futures[future]
                try:
                    report = future.result()
                    results.append(report)
                    print(f"Completed: {unit}")
                except Exception as e:
                    print(f"Failed: {unit} - {e}")
                    
        return results
```

### Async Operations

```python
import asyncio
import aiofiles

async def generate_reports_async(units: list):
    """Asynchronous report generation for better I/O handling."""
    
    tasks = []
    for unit in units:
        task = asyncio.create_task(generate_report_async(unit))
        tasks.append(task)
    
    # Wait for all tasks to complete
    reports = await asyncio.gather(*tasks)
    return reports

async def generate_report_async(unit: str):
    """Generate single report asynchronously."""
    
    # Async data loading
    data = await load_data_async(unit)
    
    # Process data (CPU-bound, use thread pool)
    loop = asyncio.get_event_loop()
    report = await loop.run_in_executor(None, process_data, data)
    
    # Async file writing
    async with aiofiles.open(f'{unit}_report.json', 'w') as f:
        await f.write(report.to_json())
    
    return report
```

## Memory Optimization

### Streaming Large Datasets

```python
class StreamingDataProcessor:
    """Process large datasets without loading everything into memory."""
    
    def __init__(self, chunk_size=10000):
        self.chunk_size = chunk_size
        
    def process_production_data(self, file_path: str):
        """Stream process production data."""
        
        aggregated_results = {}
        
        # Process in chunks
        for chunk in pd.read_csv(file_path, chunksize=self.chunk_size):
            # Process chunk
            chunk_results = self.aggregate_chunk(chunk)
            
            # Merge with overall results
            self.merge_results(aggregated_results, chunk_results)
            
            # Clear chunk from memory
            del chunk
            
        return aggregated_results
    
    def aggregate_chunk(self, chunk: pd.DataFrame):
        """Aggregate single chunk of data."""
        
        return {
            'oil_total': chunk['oil_bbls'].sum(),
            'gas_total': chunk['gas_mcf'].sum(),
            'well_count': chunk['api_number'].nunique()
        }
```

### Memory-Efficient Data Structures

```python
# Use generators for large sequences
def get_well_data(wells: list):
    """Generator to yield well data one at a time."""
    
    for well in wells:
        data = load_well_data(well)
        yield data
        # Data is released after processing

# Use numpy arrays for numerical data
import numpy as np

class EfficientMetricsStorage:
    """Store metrics using memory-efficient numpy arrays."""
    
    def __init__(self, size: int):
        # Pre-allocate arrays
        self.dates = np.empty(size, dtype='datetime64[D]')
        self.oil = np.zeros(size, dtype=np.float32)
        self.gas = np.zeros(size, dtype=np.float32)
        self.water = np.zeros(size, dtype=np.float32)
        self.index = 0
        
    def add_metric(self, date, oil, gas, water):
        """Add metric to pre-allocated arrays."""
        
        self.dates[self.index] = date
        self.oil[self.index] = oil
        self.gas[self.index] = gas
        self.water[self.index] = water
        self.index += 1
```

### Garbage Collection Optimization

```python
import gc

def process_large_batch(units: list):
    """Process large batch with explicit garbage collection."""
    
    for i, unit in enumerate(units):
        # Process unit
        report = generate_report(unit)
        save_report(report)
        
        # Explicit cleanup
        del report
        
        # Periodic garbage collection
        if i % 10 == 0:
            gc.collect()
            
        # Log memory usage
        if i % 50 == 0:
            memory_usage = get_memory_usage()
            print(f"Processed {i} units, Memory: {memory_usage}MB")
```

## Database Optimization

### Query Optimization

```sql
-- Use indexes for common queries
CREATE INDEX idx_production_date ON production_data(production_date);
CREATE INDEX idx_well_api ON wells(api_number);
CREATE INDEX idx_composite ON production_data(api_number, production_date);

-- Optimize aggregation queries
CREATE MATERIALIZED VIEW monthly_production AS
SELECT 
    api_number,
    DATE_TRUNC('month', production_date) as month,
    SUM(oil_bbls) as total_oil,
    SUM(gas_mcf) as total_gas,
    SUM(water_bbls) as total_water
FROM production_data
GROUP BY api_number, DATE_TRUNC('month', production_date);
```

### Connection Pooling

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

# Configure connection pool
engine = create_engine(
    'postgresql://user:pass@localhost/db',
    poolclass=QueuePool,
    pool_size=10,  # Number of connections to maintain
    max_overflow=20,  # Maximum overflow connections
    pool_timeout=30,  # Timeout for getting connection
    pool_recycle=3600  # Recycle connections after 1 hour
)

class OptimizedDataLoader:
    """Data loader with connection pooling."""
    
    def __init__(self, engine):
        self.engine = engine
        
    def load_data(self, query: str):
        """Load data using connection from pool."""
        
        with self.engine.connect() as conn:
            return pd.read_sql(query, conn)
```

### Batch Loading

```python
def batch_load_wells(api_numbers: list, batch_size: int = 100):
    """Load well data in batches to reduce query overhead."""
    
    all_data = []
    
    for i in range(0, len(api_numbers), batch_size):
        batch = api_numbers[i:i+batch_size]
        
        # Single query for batch
        query = f"""
        SELECT * FROM wells 
        WHERE api_number IN ({','.join(['?']*len(batch))})
        """
        
        data = load_data(query, batch)
        all_data.append(data)
    
    return pd.concat(all_data)
```

## Report Generation Optimization

### Template Compilation

```python
from jinja2 import Environment, FileSystemLoader, select_autoescape

class OptimizedTemplateEngine:
    """Template engine with compilation caching."""
    
    def __init__(self, template_dir: str):
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml']),
            cache_size=100,  # Cache compiled templates
            auto_reload=False  # Disable in production
        )
        
        # Pre-compile frequently used templates
        self.precompile_templates()
        
    def precompile_templates(self):
        """Pre-compile templates for better performance."""
        
        templates = ['economic.html', 'operational.html', 'compliance.html']
        for template_name in templates:
            self.env.get_template(template_name)
```

### Lazy Loading

```python
class LazyReportGenerator:
    """Generate reports with lazy loading of sections."""
    
    def __init__(self):
        self._sections = {}
        
    @property
    def summary(self):
        """Lazy load summary section."""
        
        if 'summary' not in self._sections:
            self._sections['summary'] = self.generate_summary()
        return self._sections['summary']
    
    @property
    def production(self):
        """Lazy load production section."""
        
        if 'production' not in self._sections:
            self._sections['production'] = self.generate_production()
        return self._sections['production']
```

## Monitoring and Profiling

### Performance Monitoring

```python
import time
import psutil
from functools import wraps

def monitor_performance(func):
    """Decorator to monitor function performance."""
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Start monitoring
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Execute function
        result = func(*args, **kwargs)
        
        # Calculate metrics
        duration = time.time() - start_time
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_used = end_memory - start_memory
        
        # Log metrics
        print(f"{func.__name__}:")
        print(f"  Duration: {duration:.2f} seconds")
        print(f"  Memory used: {memory_used:.2f} MB")
        
        return result
    
    return wrapper

@monitor_performance
def generate_report(unit: str):
    """Generate report with monitoring."""
    # Report generation logic
    pass
```

### Profiling Tools

```python
import cProfile
import pstats
from io import StringIO

def profile_report_generation(unit: str):
    """Profile report generation for bottlenecks."""
    
    profiler = cProfile.Profile()
    
    # Start profiling
    profiler.enable()
    
    # Generate report
    report = generate_report(unit)
    
    # Stop profiling
    profiler.disable()
    
    # Analyze results
    stream = StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions
    
    print(stream.getvalue())
    return report
```

### Memory Profiling

```python
from memory_profiler import profile

@profile
def memory_intensive_operation():
    """Profile memory usage line by line."""
    
    # Large data structure
    data = load_large_dataset()  # Line 1: +500 MB
    
    # Processing
    processed = process_data(data)  # Line 2: +200 MB
    
    # Cleanup
    del data  # Line 3: -500 MB
    
    return processed
```

## Configuration Examples

### High-Performance Configuration

```yaml
# high_performance.yaml
performance:
  # Caching
  cache:
    enabled: true
    backend: redis
    ttl: 7200  # 2 hours
    max_size: 10000
    warm_on_startup: true
    
  # Parallel processing
  parallel:
    enabled: true
    max_workers: 8
    chunk_size: 20
    use_process_pool: true  # For CPU-intensive tasks
    
  # Memory management
  memory:
    max_usage: 4096  # 4GB
    streaming_threshold: 100  # MB
    chunk_size: 50000  # rows
    garbage_collection_interval: 10  # operations
    
  # Database
  database:
    connection_pool_size: 20
    query_timeout: 30  # seconds
    use_materialized_views: true
    batch_size: 500
    
  # Report generation
  reports:
    lazy_loading: true
    template_caching: true
    compress_output: true
    async_export: true
```

### Memory-Constrained Configuration

```yaml
# low_memory.yaml
performance:
  # Minimal caching
  cache:
    enabled: true
    backend: memory
    ttl: 600  # 10 minutes
    max_size: 100
    
  # Limited parallelism
  parallel:
    enabled: true
    max_workers: 2
    chunk_size: 5
    
  # Aggressive memory management
  memory:
    max_usage: 1024  # 1GB
    streaming_threshold: 50  # MB
    chunk_size: 5000  # rows
    garbage_collection_interval: 5
    aggressive_cleanup: true
    
  # Streaming mode
  streaming:
    enabled: true
    buffer_size: 10  # MB
    process_in_chunks: true
```

### Balanced Configuration

```yaml
# balanced.yaml
performance:
  cache:
    enabled: true
    backend: memory
    ttl: 1800  # 30 minutes
    max_size: 500
    
  parallel:
    enabled: true
    max_workers: 4
    adaptive: true  # Adjust based on load
    
  memory:
    max_usage: 2048  # 2GB
    streaming_threshold: 100  # MB
    smart_caching: true  # Cache based on usage patterns
    
  optimization:
    profile_enabled: false  # Enable for debugging
    monitor_enabled: true
    alert_thresholds:
      memory_percent: 80
      cpu_percent: 90
      response_time: 60  # seconds
```

## Troubleshooting Performance Issues

### Common Performance Issues

#### Issue: Slow Report Generation

**Symptoms:**
- Reports take >5 minutes for medium datasets
- CPU usage remains low
- Memory usage is normal

**Solutions:**
1. Enable caching:
   ```yaml
   cache:
     enabled: true
     warm_on_startup: true
   ```

2. Increase parallel workers:
   ```yaml
   parallel:
     max_workers: 8
   ```

3. Check database queries:
   ```python
   # Enable query logging
   logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
   ```

#### Issue: Out of Memory Errors

**Symptoms:**
- Memory usage exceeds available RAM
- Process killed by OS
- MemoryError exceptions

**Solutions:**
1. Enable streaming mode:
   ```python
   processor = StreamingDataProcessor(chunk_size=5000)
   ```

2. Reduce cache size:
   ```yaml
   cache:
     max_size: 100
     ttl: 300  # 5 minutes
   ```

3. Process in smaller batches:
   ```python
   for batch in chunks(units, size=10):
       process_batch(batch)
       gc.collect()
   ```

#### Issue: Database Connection Timeouts

**Symptoms:**
- Connection pool exhausted
- Timeout errors
- Slow query response

**Solutions:**
1. Increase connection pool:
   ```python
   engine = create_engine(url, pool_size=20, max_overflow=30)
   ```

2. Optimize queries:
   ```sql
   -- Add appropriate indexes
   CREATE INDEX idx_date_api ON production_data(production_date, api_number);
   ```

3. Use read replicas for reports:
   ```python
   read_engine = create_engine('postgresql://readonly@replica/db')
   ```

### Performance Checklist

Before deploying to production, verify:

- [ ] Caching is enabled and configured
- [ ] Parallel processing is optimized for server specs
- [ ] Database has appropriate indexes
- [ ] Connection pooling is configured
- [ ] Memory limits are set appropriately
- [ ] Monitoring is enabled
- [ ] Error handling doesn't impact performance
- [ ] Logs are rotated to prevent disk issues
- [ ] Temporary files are cleaned up
- [ ] Test with production-size datasets

---

For more optimization strategies, see the [Developer Guide](developer-guide.md) or [Troubleshooting Guide](troubleshooting-faq.md).