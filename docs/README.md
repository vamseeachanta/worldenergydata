# WorldEnergyData Documentation

Welcome to the comprehensive documentation for **WorldEnergyData** - a Python library and analysis repository for energy industry professionals, data analysts, researchers, and consultants.

## Quick Navigation by User Type

### 🛢️ For Energy Professionals

*Engineers, analysts, and managers in oil & gas, wind, and energy sectors*

**Start Here:**
- [**User Guide**](user-guide/) - Installation and getting started
- [**Data Sources**](data-sources/) - BSEE, SODIR, equipment, and onshore data
- [**Analysis Guides**](analysis-guides/) - Methodologies and best practices
- [**Examples**](examples/) - Practical analysis examples

### 📊 For Data Analysts & Researchers

*Research scientists and data professionals studying energy trends*

**Start Here:**
- [**Data Sources**](data-sources/) - Comprehensive data documentation
- [**Analysis Guides**](analysis-guides/) - Statistical and analytical methodologies
- [**Reference**](reference/) - API documentation and technical specs
- [**Examples**](examples/) - Code examples and tutorials

### 💻 For Developers

*Software developers and contributors to WorldEnergyData*

**Start Here:**
- [**Development**](development/) - Setup, standards, and contribution guidelines
- [**Reference**](reference/) - API specifications and technical documentation
- [**User Guide**](user-guide/) - Understanding user-facing features
- [**Examples**](examples/) - Integration examples and code samples

## Documentation Sections

### [📋 User Guide](user-guide/)

Getting started guides, installation instructions, and basic tutorials for all users.

### [🗃️ Data Sources](data-sources/)

Comprehensive documentation for all energy data sources:
- **[BSEE](data-sources/bsee/)** - US Bureau of Safety and Environmental Enforcement data
- **[SODIR](data-sources/sodir/)** - Norwegian offshore directorate data
- **[Equipment](data-sources/equipment/)** - Anchor systems, Christmas trees, and equipment data
- **[Onshore](data-sources/onshore/)** - Wyoming and other onshore energy data

### [📈 Analysis Guides](analysis-guides/)

Methodologies, best practices, and analytical frameworks for energy data analysis.

### [🔧 Development](development/)

Technical documentation for developers, including setup guides, coding standards, and contribution guidelines.

### [📚 Reference](reference/)

API documentation, technical specifications, and comprehensive reference materials.

### [💡 Examples](examples/)

Practical code examples, sample analyses, and step-by-step tutorials.

## Features & Capabilities

### 🔄 Data Integration

- **BSEE Integration:** Complete US offshore production, drilling, and economic data
- **SODIR Integration:** Norwegian offshore regulatory and production data
- **Equipment Analysis:** Deepwater equipment specifications and performance
- **Economic Modeling:** NPV analysis with numpy-financial integration

### 📊 Analysis Tools

- **Production Forecasting:** Decline curve analysis and production modeling
- **Economic Evaluation:** Comprehensive NPV and economic risk analysis
- **Field Performance:** Multi-field benchmarking and comparison tools
- **Visualization:** Interactive charts and production curve analysis

### 🛠️ Developer Features

- **Modern Python:** Built with Python 3.9+ and UV package management
- **Modular Architecture:** Clean separation of data sources and analysis components
- **Comprehensive Testing:** Pytest-based testing with automated quality checks
- **AI-Native Development:** Structured specification system with Agent OS integration

## Getting Started

### 1. Quick Installation

```bash

# Install with pip

pip install worldenergydata

# Or with UV (recommended)

uv add worldenergydata
```

### 2. First Analysis

```python
import worldenergydata as wed

# Load BSEE production data

bsee_data = wed.load_bsee_production()

# Perform NPV analysis

npv_result = wed.analyze_npv(bsee_data, discount_rate=0.10)

# Visualize results

wed.plot_production_forecast(npv_result)
```

### 3. Explore Documentation

- **Energy Professionals:** Start with [User Guide](user-guide/) and [BSEE Data](data-sources/bsee/)
- **Data Analysts:** Explore [Analysis Guides](analysis-guides/) and [Examples](examples/)
- **Developers:** Check [Development](development/) and [Reference](reference/)

## Recent Updates

- ✅ **Documentation Reorganization** - Comprehensive restructuring for better navigation
- ✅ **Link Validation** - All internal links verified and updated
- ✅ **Navigation Indexes** - Section-specific README files with detailed contents
- ✅ **Duplicate Cleanup** - Eliminated redundant documentation files
- ✅ **Cross-References** - Enhanced linking between related sections

## Support & Contributing

### Getting Help

- 📖 **Documentation Issues:** Review the appropriate section above
- 🐛 **Bug Reports:** Check the [Development](development/) section for issue reporting
- 💬 **Questions:** See [User Guide](user-guide/) for FAQ and support resources

### Contributing

- 👨‍💻 **Developers:** Start with [Development Setup](development/)
- 📝 **Documentation:** All documentation improvements welcome
- 🧪 **Testing:** Help expand our test coverage
- 🌟 **Features:** Contribute new data sources or analysis methods

## Project Information

**WorldEnergyData** provides comprehensive energy data analysis capabilities for economic evaluation, production forecasting, and strategic decision-making using public data sources.

- **Primary Focus:** Oil & gas, wind, shipping, and energy industry analysis
- **Target Users:** Energy professionals, data analysts, researchers, consultants
- **Technical Approach:** Modern Python with AI-assisted development workflows
- **Data Sources:** BSEE, SODIR, equipment specifications, and public energy databases

---

*Last updated: 2025-07-24*
*This documentation is automatically maintained and continuously updated*

### Navigation Tips

- 🔍 Use section-specific README files for detailed contents
- 🔗 Follow cross-references to explore related topics
- 📱 All links are validated and regularly updated
- 🏠 Return here anytime using the main documentation link