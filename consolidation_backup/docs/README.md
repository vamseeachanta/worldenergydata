# WorldEnergyData Documentation

> Comprehensive Python data library for energy industry analysis
> Last Updated: 2025-07-24

## Welcome to WorldEnergyData

WorldEnergyData is a comprehensive Python data library that provides energy industry professionals, data analysts, researchers, and consultants with unified access to public energy data sources and standardized economic evaluation tools.

## Documentation Structure

### 📚 [User Guide](user-guide/)
Start here if you're new to WorldEnergyData or want to learn how to use the library effectively.

- **[Getting Started](user-guide/getting-started/)** - Installation and first steps
- **[Installation](user-guide/installation/)** - Detailed installation instructions
- **[Quick Examples](user-guide/quick-examples/)** - Common usage patterns
- **[API Reference](user-guide/api-reference/)** - Complete API documentation

### 🗄️ [Data Sources](data-sources/)
Documentation for all supported energy data sources and their integration.

- **[BSEE](data-sources/bsee/)** - Bureau of Safety and Environmental Enforcement data
- **[SODIR](data-sources/sodir/)** - Norwegian offshore directorate data
- **[Wind Energy](data-sources/wind/)** - Wind energy databases and analysis
- **[LNG](data-sources/lng/)** - Liquefied natural gas data sources
- **[Equipment](data-sources/equipment/)** - Energy equipment specifications
- **[Onshore](data-sources/onshore/)** - Onshore energy data sources

### 📊 [Analysis Guides](analysis-guides/)
Comprehensive guides for energy data analysis methodologies.

- **[Economic Evaluation](analysis-guides/economic-evaluation/)** - NPV analysis and economic modeling
- **[Production Analysis](analysis-guides/production-analysis/)** - Well and field production analysis
- **[Field Development](analysis-guides/field-development/)** - Field development analysis techniques

### 🛠️ [Development](development/)
Resources for contributors and developers working on WorldEnergyData.

- **[UV Usage](development/uv_usage.md)** - Modern Python package management

### 📖 [Reference](reference/)
Reference materials, literature, and industry standards.

- **[Literature](reference/literature/)** - Academic papers and industry publications
- **[Equipment Specs](reference/equipment-specs/)** - Technical equipment specifications
- **[Industry Standards](reference/industry-standards/)** - Industry standards and best practices

### 💡 [Examples](examples/)
Practical examples and use cases for different analysis scenarios.

- **[Basic Usage](examples/basic-usage/)** - Simple examples to get started
- **[Field Analysis](examples/field-analysis/)** - Complete field analysis workflows
- **[Economic Modeling](examples/economic-modeling/)** - Economic evaluation examples

## Quick Start

```python
import worldenergydata as wed

# Load BSEE production data
bsee_data = wed.bsee.load_production_data()

# Perform NPV analysis
npv_result = wed.analysis.calculate_npv(
    production_data=bsee_data,
    oil_price=70.0,
    discount_rate=0.10
)
```

## Getting Help

- 📚 Check the [User Guide](user-guide/) for comprehensive documentation
- 💡 Browse [Examples](examples/) for practical use cases
- 🐛 Report issues on [GitHub Issues](https://github.com/worldenergydata/worldenergydata/issues)
- 💬 Join our community discussions

## Contributing

WorldEnergyData is an open-source project. We welcome contributions from the energy community! See our [Development Guide](development/) for information on how to contribute.

---

*Built for the energy industry by energy professionals*