# Data Sources

> Comprehensive documentation for all supported energy data sources
> Last Updated: 2025-07-24

## Overview

WorldEnergyData integrates multiple public energy data sources to provide unified access to energy industry information. Each data source is carefully processed and standardized to ensure consistency across different analysis workflows.

## Available Data Sources

### 🛢️ [BSEE - Bureau of Safety and Environmental Enforcement](bsee/)
The most comprehensive data source in WorldEnergyData, covering US Gulf of Mexico offshore operations.

**Data Types:**
- Well production data (oil, gas, water)
- Directional surveys and well paths
- Completion data and tubulars
- Regulatory filings and permits
- Field development plans

**Coverage:** US Gulf of Mexico offshore wells and platforms  
**Update Frequency:** Ongoing integration with public BSEE data releases  
**Key Use Cases:** Production analysis, economic evaluation, field development studies

### 🌊 [SODIR - Norwegian Offshore Directorate](sodir/)
Norwegian offshore petroleum data for the North Sea and Norwegian Continental Shelf.

**Data Types:**
- Production data by field and well
- Reserves and resources reporting
- Drilling and completion activities
- Environmental and safety data

**Coverage:** Norwegian Continental Shelf  
**Update Frequency:** Regular updates from SODIR public data  
**Key Use Cases:** International comparisons, North Sea analysis, regulatory compliance

### 💨 [Wind Energy](wind/)
Wind energy databases and analysis capabilities for renewable energy integration.

**Data Types:**
- Wind resource assessments
- Turbine specifications and performance
- Offshore wind development data
- Energy production forecasts

**Coverage:** Global wind energy projects and resources  
**Update Frequency:** Annual technology updates and project data  
**Key Use Cases:** Renewable energy analysis, technology comparisons, site assessments

### 🚢 [LNG - Liquefied Natural Gas](lng/)
Market data and analysis tools for the global LNG industry.

**Data Types:**
- Export/import facility data
- Shipping and logistics information
- Market pricing and contracts
- Regulatory and policy updates

**Coverage:** Global LNG markets and infrastructure  
**Update Frequency:** Monthly market updates  
**Key Use Cases:** Market analysis, supply chain optimization, price forecasting

### ⚙️ [Equipment](equipment/)
Technical specifications and performance data for energy industry equipment.

**Data Types:**
- Drilling and completion equipment
- Production equipment specifications
- Subsea systems and components
- Equipment performance databases

**Coverage:** Major equipment manufacturers and specifications  
**Update Frequency:** As manufacturer data becomes available  
**Key Use Cases:** Equipment selection, cost estimation, technical analysis

### 🏗️ [Onshore](onshore/)
Onshore energy data sources including unconventional resources.

**Data Types:**
- Unconventional well data
- Hydraulic fracturing information
- Land and mineral rights data
- Production and completion data

**Coverage:** Major US onshore basins  
**Update Frequency:** Regular updates from public sources  
**Key Use Cases:** Unconventional analysis, land management, completion optimization

## Data Integration Architecture

### Standardized Data Formats
All data sources are processed into consistent formats:
- **Pandas DataFrames** for structured data
- **Standardized column names** across sources
- **Consistent date/time formats** using ISO standards
- **Quality validation** and data cleaning

### Configuration Management
- **YAML configuration files** for data source parameters
- **Flexible data filtering** and selection options
- **Custom data transformation** capabilities
- **Version control** for data processing workflows

### Data Quality Assurance
- **Automated validation** of data integrity
- **Duplicate detection** and handling
- **Missing data** identification and treatment
- **Quality metrics** and reporting

## Getting Started with Data Sources

### Basic Usage Pattern
```python
import worldenergydata as wed

# Load data from a specific source
bsee_data = wed.bsee.load_production_data(
    start_date='2020-01-01',
    end_date='2023-12-31',
    fields=['Julia', 'Jack', 'St Malo']
)

# Process and analyze
analysis_result = wed.analysis.production_trends(bsee_data)
```

### Data Source Selection Guide

| Use Case | Primary Source | Secondary Sources |
|----------|---------------|-------------------|
| US Gulf of Mexico analysis | [BSEE](bsee/) | [Equipment](equipment/) |
| International comparisons | [SODIR](sodir/) | [BSEE](bsee/) |
| Renewable energy studies | [Wind](wind/) | [LNG](lng/) |
| Market analysis | [LNG](lng/) | [Wind](wind/) |
| Equipment studies | [Equipment](equipment/) | [BSEE](bsee/) |
| Unconventional analysis | [Onshore](onshore/) | [Equipment](equipment/) |

## Data Access and Usage

### Supported Output Formats
- **Pandas DataFrames** for Python analysis
- **Excel files** for spreadsheet applications
- **CSV files** for database import
- **JSON files** for web applications

### Integration with Analysis Tools
- **Direct integration** with WorldEnergyData analysis functions
- **matplotlib/plotly** visualization support
- **numpy-financial** economic calculations
- **Statistical analysis** packages compatibility

---

*Choose a data source above to dive into specific documentation and examples.*