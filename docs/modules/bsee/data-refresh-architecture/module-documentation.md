# Enhanced Data Refresh Module Documentation

## Core Modules

### data_refresh_enhanced.py

**Location**: `src/worldenergydata/modules/bsee/data/refresh/data_refresh_enhanced.py`

**Purpose**: Main orchestrator for the enhanced data refresh system. Coordinates the entire refresh workflow from configuration reading to final binary output.

**Key Functions**:
```python
class DataRefreshEnhanced:
    def __init__(self, config_file):
        """Initialize with configuration file path"""
        
    def run(self):
        """Main execution entry point"""
        
    def refresh_well_data_enhanced(self):
        """Process well (APD) data"""
        
    def refresh_production_data_enhanced(self):
        """Process production data"""
        
    def refresh_war_data_enhanced(self):
        """Process WAR data"""
```

**Important Techniques**:
1. **Configuration-based Execution**: Reads `enhanced_refresh` flag to determine execution
2. **Modular Processing**: Separate methods for each data type (well, production, WAR)
3. **Error Isolation**: Each data source processed independently with error handling
4. **Progress Tracking**: Logs processing status for each data source

### web_scraper.py

**Location**: `src/worldenergydata/modules/bsee/data/scrapers/web_scraper.py`

**Purpose**: Handles all web scraping operations for downloading BSEE data files directly from their servers.

**Key Functions**:
```python
class BSEEWebScraper:
    def __init__(self):
        """Initialize with BSEE URLs and configurations"""
        
    def download_data(self, data_type, timeout=600):
        """Download specific data type with configurable timeout"""
        
    def verify_connectivity(self):
        """Pre-flight check for BSEE server availability"""
        
    def handle_retry(self, url, max_retries=3):
        """Retry logic with exponential backoff"""
```

**Important Techniques**:
1. **Direct URL Access**: Uses hardcoded BSEE URLs for reliable access
   - Well: `https://www.data.bsee.gov/Well/Files/APDRawData.zip`
   - Production: `https://www.data.bsee.gov/Production/Files/ProductionRawData.zip`
   - WAR: `https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip`
2. **Adaptive Timeouts**: Different timeouts for different file sizes (600s, 1200s, 2400s)
3. **Stream Download**: Uses `requests.get(stream=True)` for memory efficiency
4. **Retry Mechanism**: Exponential backoff for transient failures
5. **Progress Tracking**: Optional progress bar for large downloads

### memory_processor.py

**Location**: `src/worldenergydata/modules/bsee/data/processors/memory_processor.py`

**Purpose**: Processes ZIP files entirely in memory without extracting to disk, maintaining repository size limits.

**Key Functions**:
```python
class MemoryProcessor:
    def __init__(self):
        """Initialize processor with memory limits"""
        
    def process_zip_in_memory(self, zip_content, data_type):
        """Extract and process ZIP content in memory"""
        
    def convert_to_dataframe(self, file_content, filename):
        """Convert raw file content to pandas DataFrame"""
        
    def save_dataframe_to_binary(self, df, output_path):
        """Save DataFrame as .bin file using pickle"""
```

**Important Techniques**:
1. **In-Memory ZIP Processing**: Uses `io.BytesIO()` to handle ZIP files without disk I/O
2. **Streaming Extraction**: Processes files one at a time from ZIP
3. **Dynamic Column Detection**: Auto-detects delimiter and column structure
4. **Binary Serialization**: Uses `pickle.dump()` with protocol 4 for compatibility
5. **Memory Monitoring**: Tracks memory usage to prevent overflow
6. **Filename Preservation**: Maintains original filenames with .bin extension

### optimized_processor.py

**Location**: `src/worldenergydata/modules/bsee/data/processors/optimized_processor.py`

**Purpose**: Provides performance optimizations for large data processing operations.

**Key Functions**:
```python
class OptimizedProcessor:
    def __init__(self, chunk_size=10000):
        """Initialize with configurable chunk size"""
        
    def process_large_file(self, file_path, processor_func):
        """Process large files in chunks"""
        
    def optimize_dataframe(self, df):
        """Optimize DataFrame memory usage"""
        
    def parallel_process(self, data_list, func, n_workers=4):
        """Process data in parallel using multiprocessing"""
```

**Important Techniques**:
1. **Chunked Reading**: Processes large files in configurable chunks (default 10,000 rows)
2. **Data Type Optimization**: Downcasts numeric types to save memory
3. **Categorical Conversion**: Converts string columns to categorical for memory efficiency
4. **Parallel Processing**: Uses multiprocessing for CPU-bound operations
5. **Memory Profiling**: Tracks and reports memory usage statistics
6. **Lazy Evaluation**: Defers operations until necessary

### chunk_manager.py

**Location**: `src/worldenergydata/modules/bsee/data/cache/chunk_manager.py`

**Purpose**: Manages chunked data processing for files too large to fit in memory.

**Key Functions**:
```python
class ChunkManager:
    def __init__(self, max_chunk_size_mb=100):
        """Initialize with maximum chunk size"""
        
    def create_chunks(self, data_source, chunk_size):
        """Split data source into manageable chunks"""
        
    def process_chunk(self, chunk, processor):
        """Process individual chunk"""
        
    def merge_results(self, chunk_results):
        """Combine processed chunks into final result"""
```

**Important Techniques**:
1. **Dynamic Chunk Sizing**: Adjusts chunk size based on available memory
2. **Streaming Processing**: Processes chunks as they arrive
3. **Checkpoint Support**: Can resume from last successful chunk
4. **Memory-Mapped Files**: Uses numpy memmap for very large datasets
5. **Result Aggregation**: Efficiently combines chunk results
6. **Progress Tracking**: Reports processing progress per chunk

### config_router.py

**Location**: `src/worldenergydata/modules/bsee/data/config/config_router.py`

**Purpose**: Routes execution between legacy and enhanced systems based on configuration flags.

**Key Functions**:
```python
class ConfigRouter:
    def __init__(self, config_path):
        """Load configuration from YAML file"""
        
    def determine_execution_path(self):
        """Decide whether to use legacy or enhanced system"""
        
    def get_data_sources(self):
        """Return enabled data sources from config"""
        
    def validate_config(self):
        """Ensure configuration is valid and complete"""
```

**Important Techniques**:
1. **Flag-Based Routing**: Checks `enhanced_refresh` vs `refresh` flags
2. **Backward Compatibility**: Defaults to legacy if enhanced flag not present
3. **Configuration Validation**: Ensures all required fields present
4. **Dynamic Import**: Loads appropriate module based on configuration
5. **Environment Detection**: Adjusts behavior for git bash vs standard terminal
6. **Conflict Resolution**: Handles cases where both flags are set

## Processing Flow Details

### 1. Initialization Phase
```python
# Entry point in data_refresh_enhanced.py
config = load_config('data_refresh_enhanced.yml')
router = ConfigRouter(config)
execution_path = router.determine_execution_path()
```

### 2. Download Phase
```python
# Web scraper downloads data
scraper = BSEEWebScraper()
zip_content = scraper.download_data('production', timeout=1200)
```

### 3. Processing Phase
```python
# Memory processor handles ZIP content
processor = MemoryProcessor()
dataframes = processor.process_zip_in_memory(zip_content, 'production')
```

### 4. Optimization Phase
```python
# Optimize large DataFrames
optimizer = OptimizedProcessor()
for df in dataframes:
    optimized_df = optimizer.optimize_dataframe(df)
```

### 5. Chunking Phase (for large files)
```python
# Handle very large files with chunking
chunk_mgr = ChunkManager(max_chunk_size_mb=100)
chunks = chunk_mgr.create_chunks(large_data, chunk_size=10000)
results = [chunk_mgr.process_chunk(chunk, processor) for chunk in chunks]
final_result = chunk_mgr.merge_results(results)
```

### 6. Output Phase
```python
# Save to binary format
output_path = 'data/modules/bsee/bin/production/mv_production_data.bin'
processor.save_dataframe_to_binary(final_result, output_path)
```

## Error Handling Strategy

Each module implements comprehensive error handling:

1. **Network Errors**: Retry with exponential backoff
2. **Memory Errors**: Fall back to chunked processing
3. **Data Errors**: Validate and clean corrupted data
4. **File System Errors**: Check permissions and space
5. **Configuration Errors**: Provide clear error messages

## Performance Considerations

1. **Memory Usage**: Peak <500MB for largest files
2. **Processing Speed**: 2-3x faster than legacy system
3. **Network Efficiency**: Minimal redundant downloads
4. **CPU Utilization**: Parallel processing where applicable
5. **Disk I/O**: Minimized through in-memory processing

## Testing Integration

Each module has corresponding test files in:
- `tests/modules/bsee/data/refresh/`
- `tests/modules/bsee/analysis/2025-08-06-data-refresh-architecture/`

Tests cover:
- Unit testing of individual functions
- Integration testing of module interactions
- Performance benchmarking
- Error scenario validation
- Binary format compatibility