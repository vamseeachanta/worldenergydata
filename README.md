# WorldEnergyData

A comprehensive Python data library and analysis repository for the energy industry, providing integrated access to public energy data sources with built-in economic evaluation and production forecasting tools.

## Overview

WorldEnergyData helps energy industry professionals, data analysts, researchers, and consultants make data-driven decisions by providing:

- **Unified Data Access**: Automated collection and processing from multiple public sources (BSEE, SODIR, wind databases)
- **Economic Analysis**: Built-in NPV analysis and production forecasting capabilities
- **Cross-Sector Integration**: Modular architecture supporting oil & gas, wind, shipping, and other energy sectors

## Key Features

### Data Integration
- **BSEE Data**: Bureau of Safety and Environmental Enforcement data including well production, directional surveys, and completion data
- **Field Analysis**: Specialized tools for major deepwater fields (Anchor, Julia, Jack, St. Malo)
- **Web Scraping**: Automated data collection using Scrapy, Selenium, and BeautifulSoup

### Analysis Capabilities
- **Economic Evaluation**: NPV analysis with numpy-financial
- **Production Forecasting**: Timeline visualization and forecasting tools
- **Data Visualization**: Interactive charts with matplotlib and plotly
- **YAML Configuration**: Flexible workflow customization

### Development Features
- **Modern Python**: 3.9+ with UV package management
- **Testing Framework**: Comprehensive pytest-based testing
- **Code Quality**: black, isort, ruff, and mypy integration
- **Modular Architecture**: Clean separation of data sources, processing, and analysis

## Quick Start

### Installation

#### Using UV (Recommended)

```bash
# Install UV package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/username/worldenergydata.git
cd worldenergydata

# Setup development environment
./scripts/uv_setup.sh         # Linux/Mac
./scripts/uv_migrate.bat       # Windows

# Install dependencies
uv sync

# Run the application
uv run python -m worldenergydata
```

#### Using pip

```bash
# Install from source
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_bsee.py
```

### Code Formatting and Linting

```bash
# Format code
uv run black .
uv run isort .

# Run linting
uv run ruff check .

# Type checking
uv run mypy src/
```

## Project Structure

```
worldenergydata/
├── src/
│   └── worldenergydata/
│       ├── modules/
│       │   ├── bsee/              # BSEE data analysis
│       │   └── well_production_dashboard/
│       ├── common/                 # Shared utilities
│       └── engine.py               # Core engine
├── data/
│   └── modules/                    # Data storage
├── tests/                          # Test suite
├── scripts/                        # Utility scripts
├── docs/                           # Documentation
│   ├── analysis-guides/
│   ├── data-sources/
│   ├── development/
│   └── modules/
├── pyproject.toml                  # Project configuration
└── uv.lock                         # Dependency lock file
```

## Modules

### BSEE Module
Comprehensive BSEE (Bureau of Safety and Environmental Enforcement) data analysis:
- Production data analysis
- Directional surveys
- Well completion data
- Financial analysis with NPV calculations
- Lease grouping and aggregation

### Well Production Dashboard
Interactive dashboard for well production visualization and analysis.

## Configuration

WorldEnergyData uses YAML-based configuration for flexible data processing:

```yaml
# Example configuration
data_sources:
  bsee:
    enabled: true
    fields: [Anchor, Julia, Jack, St. Malo]

analysis:
  npv:
    discount_rate: 0.10
    price_deck: oil_gas_prices.csv
```

## Development

### Setting Up Development Environment

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Run pre-commit hooks
pre-commit install
```

### Running Analysis Scripts

```bash
# BSEE data analysis
uv run python -m worldenergydata.modules.bsee.analysis.bsee_analysis

# Financial analysis
uv run python -m worldenergydata.modules.bsee.analysis.financial.cli_interface
```

### Adding Dependencies

```bash
# Add a new dependency
uv add requests

# Add a development dependency
uv add --dev pytest-asyncio
```

## Building and Publishing

### Local Development Build

```bash
# Build the package
python -m build

# Install locally in editable mode
pip install -e .
```

### Publishing to PyPI

```bash
# Update version
bumpver update --patch

# Build distribution
python -m build

# Upload to PyPI
twine upload dist/*
```

## Testing

The project uses pytest for comprehensive testing:

```bash
# Run all tests
uv run pytest

# Run specific module tests
uv run pytest tests/modules/test_bsee.py

# Run with coverage report
uv run pytest --cov=src --cov-report=term-missing --cov-report=html

# Run integration tests
uv run python scripts/integration_test_directional_surveys.py
```

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Analysis Guides](docs/analysis-guides/)**: Step-by-step analysis tutorials
- **[Data Sources](docs/data-sources/)**: Information about data sources
- **[Development](docs/development/)**: Development guidelines and UV usage
- **[Module Docs](docs/modules/)**: Module-specific documentation

## Contributing

We welcome contributions! Please follow these guidelines:

1. **Code Style**: Use black, isort, and ruff for formatting
2. **Testing**: Add tests for new features
3. **Documentation**: Update docs for significant changes
4. **Commits**: Follow conventional commit messages

```bash
# Format before committing
uv run black .
uv run isort .

# Run linting
uv run ruff check .

# Ensure tests pass
uv run pytest
```

## Technology Stack

- **Language**: Python 3.9+
- **Package Manager**: UV
- **Data Processing**: pandas, numpy, numpy-financial
- **Web Scraping**: Scrapy, Selenium, BeautifulSoup4
- **Visualization**: matplotlib, plotly
- **Testing**: pytest
- **Code Quality**: black, isort, ruff, mypy

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Authors

Development Team - [dev@example.com](mailto:dev@example.com)

## Support

- **Issues**: [GitHub Issues](https://github.com/username/worldenergydata/issues)
- **Documentation**: [Project Wiki](https://github.com/username/worldenergydata#readme)

## Acknowledgments

- Bureau of Safety and Environmental Enforcement (BSEE) for public data access
- Open-source community for excellent Python libraries

---

**Note**: This project is designed for analysis of public energy data sources. Always verify data accuracy and comply with data usage terms from source providers.
