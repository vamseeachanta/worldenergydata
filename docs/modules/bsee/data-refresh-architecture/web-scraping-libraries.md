# Web Scraping Libraries Documentation

## Overview

The Enhanced Data Refresh Architecture uses a carefully selected set of Python libraries for web scraping, data processing, and file handling. This document details each library, its purpose, and why it was chosen.

## Core Web Scraping Libraries

### 1. requests (v2.31.0+)

**Purpose**: HTTP library for downloading data from BSEE servers

**Key Features Used**:
- `requests.get()` - Basic HTTP GET requests
- `stream=True` parameter - Memory-efficient large file downloads
- `timeout` parameter - Configurable request timeouts
- `headers` - Custom user-agent and accept headers
- `Session` objects - Connection pooling and persistence

**Usage Example**:
```python
import requests

response = requests.get(
    url="https://www.data.bsee.gov/Production/Files/ProductionRawData.zip",
    stream=True,
    timeout=1200,
    headers={'User-Agent': 'BSEE-Data-Refresh/1.0'}
)
```

**Why Chosen**:
- Industry standard for HTTP requests
- Excellent streaming support for large files
- Built-in retry and timeout mechanisms
- Lightweight with minimal dependencies

### 2. urllib3 (v2.0.0+)

**Purpose**: Advanced HTTP client, used as backend for requests

**Key Features Used**:
- Connection pooling
- Retry configuration
- SSL/TLS verification
- Timeout management

**Usage Example**:
```python
from urllib3.util.retry import Retry

retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504]
)
```

**Why Chosen**:
- Provides low-level control when needed
- Excellent retry mechanisms
- Thread-safe connection pooling
- Production-ready reliability

### 3. BeautifulSoup4 (bs4) (v4.12.0+)

**Purpose**: HTML parsing for portal page analysis

**Key Features Used**:
- HTML parsing
- Link extraction
- DOM navigation
- Text extraction

**Usage Example**:
```python
from bs4 import BeautifulSoup

soup = BeautifulSoup(html_content, 'html.parser')
download_links = soup.find_all('a', {'class': 'download-button'})
```

**Why Chosen**:
- Simple API for HTML parsing
- Robust error handling
- Handles malformed HTML gracefully
- Lightweight for simple scraping tasks

## Data Processing Libraries

### 4. pandas (v2.0.0+)

**Purpose**: DataFrame operations for data manipulation

**Key Features Used**:
- `read_csv()` - Parse CSV/TSV files
- `to_pickle()` - Binary serialization
- Memory optimization functions
- Data type inference
- Chunked reading for large files

**Usage Example**:
```python
import pandas as pd

df = pd.read_csv(
    file_content,
    sep='\t',
    low_memory=False,
    dtype_backend='numpy_nullable'
)
```

**Why Chosen**:
- Industry standard for data manipulation
- Excellent memory management options
- Native pickle support
- Extensive data type handling

### 5. numpy (v1.24.0+)

**Purpose**: Numerical operations and memory-mapped arrays

**Key Features Used**:
- Memory-mapped files for large datasets
- Efficient array operations
- Data type optimization
- Memory usage monitoring

**Usage Example**:
```python
import numpy as np

# Memory-mapped array for large files
mmap_array = np.memmap(
    'large_file.dat',
    dtype='float32',
    mode='r',
    shape=(1000000, 100)
)
```

**Why Chosen**:
- Foundation for pandas operations
- Memory-efficient large array handling
- Fast numerical computations
- Memory mapping support

## File Handling Libraries

### 6. zipfile (Standard Library)

**Purpose**: ZIP archive handling without extraction to disk

**Key Features Used**:
- `ZipFile` class - Read ZIP archives
- `namelist()` - List archive contents
- `read()` - Extract files to memory
- `extractall()` - Batch extraction (when needed)

**Usage Example**:
```python
import zipfile
import io

zip_buffer = io.BytesIO(zip_content)
with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
    for filename in zip_file.namelist():
        file_content = zip_file.read(filename)
```

**Why Chosen**:
- Part of Python standard library
- No additional dependencies
- Supports in-memory operations
- Reliable and well-maintained

### 7. io (Standard Library)

**Purpose**: In-memory file operations

**Key Features Used**:
- `BytesIO` - In-memory bytes buffer
- `StringIO` - In-memory text buffer
- Stream interfaces
- Buffer management

**Usage Example**:
```python
import io

# Create in-memory buffer for ZIP content
zip_buffer = io.BytesIO(downloaded_bytes)

# Create string buffer for CSV content
csv_buffer = io.StringIO(csv_text)
```

**Why Chosen**:
- Zero disk I/O for temporary files
- Perfect for memory-constrained environments
- Part of standard library
- Seamless integration with other libraries

### 8. pickle (Standard Library)

**Purpose**: Binary serialization for DataFrame storage

**Key Features Used**:
- `dump()` - Serialize objects to binary
- `load()` - Deserialize binary to objects
- Protocol versioning
- Compression support

**Usage Example**:
```python
import pickle

with open('data.bin', 'wb') as f:
    pickle.dump(dataframe, f, protocol=4)
```

**Why Chosen**:
- Native Python serialization
- Maintains full DataFrame structure
- Compatible with legacy system
- Fast serialization/deserialization

## Utility Libraries

### 9. pathlib (Standard Library)

**Purpose**: Modern path handling

**Key Features Used**:
- Cross-platform path operations
- Path validation
- Directory creation
- File existence checks

**Usage Example**:
```python
from pathlib import Path

output_path = Path('data/modules/bsee/bin/production')
output_path.mkdir(parents=True, exist_ok=True)
```

**Why Chosen**:
- Modern Python path handling
- Cross-platform compatibility
- Clean API
- Part of standard library

### 10. logging (Standard Library)

**Purpose**: Comprehensive logging system

**Key Features Used**:
- Multiple log levels
- File and console handlers
- Log rotation
- Formatted output

**Usage Example**:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('enhanced_refresh.log'),
        logging.StreamHandler()
    ]
)
```

**Why Chosen**:
- Standard Python logging
- Highly configurable
- Production-ready
- No external dependencies

### 11. concurrent.futures (Standard Library)

**Purpose**: Parallel processing support

**Key Features Used**:
- `ThreadPoolExecutor` - Thread-based parallelism
- `ProcessPoolExecutor` - Process-based parallelism
- Future objects
- Timeout handling

**Usage Example**:
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [
        executor.submit(download_data, 'well'),
        executor.submit(download_data, 'production'),
        executor.submit(download_data, 'war')
    ]
```

**Why Chosen**:
- Built-in parallelism support
- Clean API
- Good error handling
- Part of standard library

## Optional Enhancement Libraries

### 12. tqdm (v4.65.0+) [Optional]

**Purpose**: Progress bars for long-running operations

**Key Features Used**:
- Progress bars
- Time estimates
- Download progress
- Iteration tracking

**Usage Example**:
```python
from tqdm import tqdm

for chunk in tqdm(chunks, desc="Processing chunks"):
    process_chunk(chunk)
```

**Why Chosen**:
- User-friendly progress indication
- Minimal performance overhead
- Works in various environments
- Optional - not required for core functionality

### 13. psutil (v5.9.0+) [Optional]

**Purpose**: System and process monitoring

**Key Features Used**:
- Memory usage monitoring
- CPU usage tracking
- Disk space checks
- Process management

**Usage Example**:
```python
import psutil

memory_percent = psutil.virtual_memory().percent
if memory_percent > 90:
    switch_to_chunked_mode()
```

**Why Chosen**:
- Cross-platform system monitoring
- Accurate memory measurements
- Process control capabilities
- Helpful for optimization

## Library Selection Criteria

All libraries were chosen based on:

1. **Reliability**: Production-tested and stable
2. **Performance**: Efficient for large-scale operations
3. **Memory Efficiency**: Support for streaming and chunking
4. **Maintenance**: Actively maintained and updated
5. **Dependencies**: Minimal external dependencies
6. **Compatibility**: Works across platforms (Windows/Linux/Mac)
7. **License**: Compatible open-source licenses

## Installation

All required libraries can be installed via UV:

```bash
# Core dependencies (in pyproject.toml)
uv add requests pandas numpy beautifulsoup4

# Optional enhancements
uv add tqdm psutil
```

## Version Compatibility Matrix

| Library | Minimum Version | Recommended | Maximum Tested |
|---------|----------------|-------------|----------------|
| Python | 3.9 | 3.11 | 3.12 |
| requests | 2.28.0 | 2.31.0 | 2.32.x |
| pandas | 1.5.0 | 2.0.0 | 2.1.x |
| numpy | 1.21.0 | 1.24.0 | 1.26.x |
| beautifulsoup4 | 4.11.0 | 4.12.0 | 4.12.x |
| urllib3 | 1.26.0 | 2.0.0 | 2.1.x |

## Security Considerations

1. **SSL Verification**: Always enabled for HTTPS requests
2. **Input Validation**: All downloaded data validated before processing
3. **Memory Limits**: Enforced to prevent DoS via large files
4. **Timeout Protection**: All network operations have timeouts
5. **Error Handling**: Comprehensive try-catch blocks
6. **No Code Execution**: Downloaded content never executed

## Performance Tips

1. Use `stream=True` for large downloads
2. Process data in chunks when possible
3. Monitor memory usage with psutil
4. Use connection pooling for multiple requests
5. Enable compression where supported
6. Implement proper retry logic
7. Use appropriate timeouts for each data source