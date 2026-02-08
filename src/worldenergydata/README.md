# WorldEnergyData Package

This is the main source package for WorldEnergyData.

## Package Structure

```
worldenergydata/
├── __init__.py              # Package initialization
├── cli/                     # Command-line interface
│   ├── __init__.py
│   ├── main.py              # Main CLI entry point
│   └── commands/            # Module-specific CLI commands
│       ├── bsee.py          # BSEE CLI commands
│       ├── marine_safety.py # Marine safety CLI commands
│       └── fdas.py          # FDAS CLI commands
├── common/                  # Shared utilities (cross-cutting concerns)
│   ├── __init__.py          # Re-exports common utilities
│   ├── logging.py           # Centralized logging configuration
│   ├── config.py            # Configuration management
│   ├── exceptions.py        # Custom exception hierarchy
│   ├── constants.py         # Energy unit constants
│   ├── types.py             # Type definitions and protocols
│   ├── validators.py        # Common validators
│   └── decorators.py        # Shared decorators
└── modules/                 # Domain-specific modules
    ├── bsee/                # BSEE data module
    ├── marine_safety/       # Marine safety module
    ├── fdas/                # Field Development Analysis System
    ├── hse/                 # HSE (Health, Safety, Environment)
    └── vessel_hull_models/  # Vessel hull model data
```

## Common Layer Usage

The `common` module provides shared utilities across all modules:

```python
# Logging
from worldenergydata.common import get_logger, configure_logging
logger = get_logger(__name__)

# Exceptions
from worldenergydata.common import (
    WorldEnergyDataError,
    DataError,
    ValidationError,
    ConfigError,
    APIError,
)

# Configuration
from worldenergydata.common import Settings, get_settings
settings = get_settings()

# Constants
from worldenergydata.common import EnergyUnits, UNIT_CONVERSIONS

# Types
from worldenergydata.common import (
    JSONDict,
    PathLike,
    DataFrameLike,
    DataSourceProtocol,
)
```

## Module Organization

Each module follows a consistent structure:

```
modules/<module_name>/
├── __init__.py           # Module exports
├── config.py             # Module-specific configuration
├── constants.py          # Module-specific constants
├── exceptions.py         # Module-specific exceptions
├── data/                 # Data layer
│   ├── loaders/          # Data loading strategies
│   └── sources/          # Data source handlers
├── analysis/             # Analysis layer
├── reports/              # Report generation
└── utils/                # Module-specific utilities
```

## Importing from Modules

### BSEE Module

```python
# Main classes
from worldenergydata.bsee import (
    bsee,
    BSEEData,
    BSEEAnalysis,
    WellData,
    ProductionRouter,
)

# Data loaders
from worldenergydata.bsee.data.loaders.api import WellData
from worldenergydata.bsee.data.loaders.block import BlockRouter
from worldenergydata.bsee.data.loaders.lease import LeaseRouter

# Data sources
from worldenergydata.bsee.data.sources.bin import APIData
from worldenergydata.bsee.data.sources.zip import GetProdDataFromZip
```

### Marine Safety Module

```python
from worldenergydata.marine_safety import (
    config,
    constants,
    exceptions,
    database,
    scrapers,
    utils,
)

# Scrapers
from worldenergydata.marine_safety.scrapers.uscg_scraper import USCGMarineCasualtyScraper

# Database
from worldenergydata.marine_safety.database.db_manager import get_db_manager
```

### FDAS Module

```python
from worldenergydata.fdas import (
    # Financial functions
    excel_like_mirr,
    calculate_npv,
    calculate_irr,
    calculate_all_metrics,

    # Configuration
    AssumptionsManager,
    PriceDeckManager,
    classify_dev_system_by_depth,

    # Adapters
    BseeAdapter,
    LeaseMapping,
)
```

## CLI Entry Point

The package provides a unified CLI:

```python
from worldenergydata.cli import app

# Or run from command line:
# python -m worldenergydata --help
# worldenergydata bsee --help
# worldenergydata marine-safety --help
# worldenergydata fdas --help
```

## Best Practices

1. **Use the common layer** for shared functionality
2. **Import from module `__init__.py`** for stable public API
3. **Check `__all__` exports** to see what's officially supported
4. **Avoid importing from internal modules** (prefixed with `_`)

## Migration Notes

See [MIGRATION_GUIDE.md](../../docs/MIGRATION_GUIDE.md) for migrating from deprecated import paths.
