# Package Reorganization Migration Guide

## Overview

This guide documents the worldenergydata package reorganization completed in January 2026. The reorganization improves code discoverability, establishes clearer module boundaries, and creates a more maintainable codebase structure.

## What Changed

### 1. New Common Layer
A shared `worldenergydata.common` module was created to house utilities used across multiple modules:

```
src/worldenergydata/common/
├── __init__.py           # Re-exports common utilities
├── logging.py            # Centralized logging configuration
├── paths.py              # Path management utilities
├── config.py             # Configuration management
├── datetime.py           # Date/time utilities
├── validators.py         # Common validators
├── decorators.py         # Shared decorators
└── legacy/               # Legacy utilities (deprecated)
    ├── data.py
    └── io.py
```

### 2. BSEE Module Restructuring
The BSEE data module was reorganized from underscore-prefixed directories to semantic names:

```
# Before (deprecated):
_by_api/     -> API-based data access
_by_block/   -> Block-based data access
_by_lease/   -> Lease-based data access
_from_bin/   -> Binary file sources
_from_zip/   -> ZIP file sources

# After (new structure):
loaders/     -> Data loading strategies
├── api/     -> API-based data access
├── block/   -> Block-based data access
└── lease/   -> Lease-based data access

sources/     -> Data source handlers
├── bin/     -> Binary file sources
└── zip/     -> ZIP file sources
```

### 3. Unified CLI
A new unified CLI was created that orchestrates all module-specific commands:

```bash
# Main entry point
python -m worldenergydata --help

# Module-specific commands
python -m worldenergydata bsee --help
python -m worldenergydata marine-safety --help
python -m worldenergydata fdas --help
```

## Import Migration

### BSEE Data Loaders (by API)

| Old Import Path (Deprecated) | New Import Path |
|------------------------------|-----------------|
| `from worldenergydata.modules.bsee.data._by_api.well import WellData` | `from worldenergydata.modules.bsee.data.loaders.api.well import WellData` |
| `from worldenergydata.modules.bsee.data._by_api.router import WellRouter` | `from worldenergydata.modules.bsee.data.loaders.api.router import WellRouter` |
| `from worldenergydata.modules.bsee.data._by_api import *` | `from worldenergydata.modules.bsee.data.loaders.api import *` |

### BSEE Data Loaders (by Block)

| Old Import Path (Deprecated) | New Import Path |
|------------------------------|-----------------|
| `from worldenergydata.modules.bsee.data._by_block.router import BlockRouter` | `from worldenergydata.modules.bsee.data.loaders.block.router import BlockRouter` |
| `from worldenergydata.modules.bsee.data._by_block.data_from_local_files import DataFromLocalFiles` | `from worldenergydata.modules.bsee.data.loaders.block.local_files import DataFromLocalFiles` |
| `from worldenergydata.modules.bsee.data._by_block.war_data import WARDataFromBin` | `from worldenergydata.modules.bsee.data.loaders.block.war_data import WARDataFromBin` |

### BSEE Data Loaders (by Lease)

| Old Import Path (Deprecated) | New Import Path |
|------------------------------|-----------------|
| `from worldenergydata.modules.bsee.data._by_lease.router import LeaseRouter` | `from worldenergydata.modules.bsee.data.loaders.lease.router import LeaseRouter` |
| `from worldenergydata.modules.bsee.data._by_lease.data_from_local_files import DataFromLocalFiles` | `from worldenergydata.modules.bsee.data.loaders.lease.local_files import DataFromLocalFiles` |

### BSEE Data Sources (Binary)

| Old Import Path (Deprecated) | New Import Path |
|------------------------------|-----------------|
| `from worldenergydata.modules.bsee.data._from_bin.api_data import APIData` | `from worldenergydata.modules.bsee.data.sources.bin.api_data import APIData` |
| `from worldenergydata.modules.bsee.data._from_bin.block_data import BlockData` | `from worldenergydata.modules.bsee.data.sources.bin.block_data import BlockData` |
| `from worldenergydata.modules.bsee.data._from_bin.lease_data import LeaseData` | `from worldenergydata.modules.bsee.data.sources.bin.lease_data import LeaseData` |

### BSEE Data Sources (ZIP)

| Old Import Path (Deprecated) | New Import Path |
|------------------------------|-----------------|
| `from worldenergydata.modules.bsee.data._from_zip.production_data import GetProdDataFromZip` | `from worldenergydata.modules.bsee.data.sources.zip.production_data import GetProdDataFromZip` |
| `from worldenergydata.modules.bsee.data._from_zip.well_data import WellDataFromZip` | `from worldenergydata.modules.bsee.data.sources.zip.well_data import WellDataFromZip` |

## Deprecation Timeline

| Phase | Version | Date | Action |
|-------|---------|------|--------|
| **Current** | 1.x | Now | Deprecation warnings issued for old import paths |
| **Warning Period** | 1.x | 6 months | Old paths work but emit DeprecationWarning |
| **Removal** | 2.0.0 | TBD | Old paths will be removed entirely |

## How to Update Your Code

### Step 1: Enable Deprecation Warnings

Run your code with deprecation warnings enabled to identify all affected imports:

```bash
python -W default::DeprecationWarning your_script.py
```

Or in your test configuration:

```ini
# pytest.ini
[pytest]
filterwarnings =
    default::DeprecationWarning
```

### Step 2: Find and Replace Imports

Use these search patterns to find deprecated imports:

```bash
# Find all deprecated _by_api imports
grep -r "from worldenergydata.modules.bsee.data._by_api" .

# Find all deprecated _by_block imports
grep -r "from worldenergydata.modules.bsee.data._by_block" .

# Find all deprecated _from_bin imports
grep -r "from worldenergydata.modules.bsee.data._from_bin" .

# Find all deprecated _from_zip imports
grep -r "from worldenergydata.modules.bsee.data._from_zip" .
```

### Step 3: Update Imports

Replace deprecated imports with new paths:

```python
# Before (deprecated)
from worldenergydata.modules.bsee.data._by_api.well import WellData
from worldenergydata.modules.bsee.data._from_bin.api_data import APIData

# After
from worldenergydata.modules.bsee.data.loaders.api.well import WellData
from worldenergydata.modules.bsee.data.sources.bin.api_data import APIData
```

### Step 4: Use Common Utilities

For shared utilities, prefer the new common module:

```python
# New common utilities
from worldenergydata.common import get_logger, get_data_path
from worldenergydata.common.datetime import DateTimeUtility
from worldenergydata.common.validators import validate_api_number
```

## Common Migration Patterns

### Pattern 1: Wildcard Imports

```python
# Before
from worldenergydata.modules.bsee.data._by_api import *

# After
from worldenergydata.modules.bsee.data.loaders.api import *
```

### Pattern 2: Router Classes

```python
# Before
from worldenergydata.modules.bsee.data._by_api.router import WellRouter
from worldenergydata.modules.bsee.data._by_block.router import BlockRouter

# After
from worldenergydata.modules.bsee.data.loaders.api.router import WellRouter
from worldenergydata.modules.bsee.data.loaders.block.router import BlockRouter
```

### Pattern 3: Data Source Classes

```python
# Before
from worldenergydata.modules.bsee.data._from_bin.api_data import APIData
from worldenergydata.modules.bsee.data._from_zip.production_data import GetProdDataFromZip

# After
from worldenergydata.modules.bsee.data.sources.bin.api_data import APIData
from worldenergydata.modules.bsee.data.sources.zip.production_data import GetProdDataFromZip
```

## Backward Compatibility

The old import paths continue to work during the deprecation period. Shim modules at the old locations automatically forward imports to the new locations while emitting deprecation warnings.

Example of what happens with old imports:

```python
>>> import warnings
>>> warnings.filterwarnings('default')
>>> from worldenergydata.modules.bsee.data._by_api import *
DeprecationWarning: Importing from 'worldenergydata.modules.bsee.data._by_api' is deprecated.
Please use 'worldenergydata.modules.bsee.data.loaders.api' instead.
This import path will be removed in version 2.0.0.
```

## Testing Your Migration

After updating imports, verify everything works:

```bash
# Run import tests
uv run python -c "from worldenergydata import *"
uv run python -c "from worldenergydata.common import *"
uv run python -c "from worldenergydata.modules.bsee.data.loaders import *"
uv run python -c "from worldenergydata.modules.bsee.data.sources import *"

# Run your test suite with warnings as errors
uv run pytest --fail-on-warnings -W error::DeprecationWarning
```

## Questions and Support

For questions about this migration:

1. Check this migration guide for import mappings
2. Review the module docstrings for usage examples
3. Consult the API documentation in `docs/api/`
4. Open an issue in the project repository

## CLI Migration

The new unified CLI replaces individual module entry points.

### Old CLI Commands (Deprecated)

```bash
# Old BSEE commands
python -m worldenergydata.modules.bsee.analysis.bsee_analysis
python -m worldenergydata.modules.bsee.analysis.financial.cli_interface

# Old Marine Safety commands
python -m worldenergydata.modules.marine_safety.scrapers.uscg_scraper

# Old FDAS commands
python -m worldenergydata.modules.fdas.core.financial
```

### New CLI Commands

```bash
# Unified entry point
worldenergydata --help

# BSEE module
worldenergydata bsee analyze --block 759
worldenergydata bsee report --type field --id "Jack" --format excel
worldenergydata bsee data --api 608114001200
worldenergydata bsee refresh --type production
worldenergydata bsee stats

# Marine Safety module
worldenergydata marine-safety scrape uscg --start-year 2020
worldenergydata marine-safety db init --dev-mode
worldenergydata marine-safety stats --source uscg
worldenergydata marine-safety export csv --output incidents.csv

# FDAS module
worldenergydata fdas calculate-npv --cashflows "[-1000,100,200,300]"
worldenergydata fdas calculate-mirr --cashflows "[-5000,1000,1500,2000]"
worldenergydata fdas calculate-all --cashflows "[-1000,100,200,300,400,500]"
worldenergydata fdas analyze --field "Thunder Horse" --discount-rate 0.10
worldenergydata fdas classify 5000
```

### CLI Migration Table

| Old Command | New Command |
|-------------|-------------|
| `python -m worldenergydata.modules.bsee.analysis.bsee_analysis --block 759` | `worldenergydata bsee analyze --block 759` |
| `python -m worldenergydata.modules.bsee.analysis.financial.cli_interface` | `worldenergydata fdas analyze` |
| Direct scraper execution | `worldenergydata marine-safety scrape uscg` |
| Direct financial calculation scripts | `worldenergydata fdas calculate-npv` |

## Summary

The reorganization provides:

- **Semantic naming**: Directories named by function (loaders, sources) rather than implementation details (_by_api, _from_bin)
- **Common utilities**: Shared code in `worldenergydata.common` reduces duplication
- **Unified CLI**: Single entry point for all module commands
- **Backward compatibility**: Shims ensure existing code continues to work with deprecation warnings
- **Clear migration path**: 6-month deprecation period before removal in version 2.0.0

## Related Documentation

- [CLI.md](CLI.md): Complete CLI command reference
- [README.md](../README.md): Project overview
- [src/worldenergydata/README.md](../src/worldenergydata/README.md): Package structure
