# Examples

> Practical examples and use cases for energy analysis with WorldEnergyData
> Last Updated: 2025-07-24

## Overview

The Examples section provides practical, real-world use cases and code examples that demonstrate how to use WorldEnergyData for energy industry analysis. These examples are designed to help users quickly understand how to apply the library to their specific analysis needs.

## Example Categories

### 🚀 [Basic Usage](basic-usage/)

Simple examples to get started with WorldEnergyData fundamentals.

**Getting Started Examples:**
- **Hello World**: Your first WorldEnergyData analysis
- **Data Loading**: Loading data from different sources
- **Basic Plotting**: Creating simple visualizations
- **Data Export**: Saving results in different formats
- **Error Handling**: Common error scenarios and solutions

**Quick Analysis Examples:**
- **Production Summary**: Generate production summaries by field
- **Simple NPV**: Basic economic evaluation of a well
- **Decline Curves**: Fit and visualize production decline curves
- **Data Comparison**: Compare production across multiple wells
- **Cost Analysis**: Basic cost analysis and benchmarking

**Code Patterns:**
```python
import worldenergydata as wed

# Load production data

data = wed.bsee.load_production_data(field='Julia')

# Quick analysis

summary = wed.analysis.production_summary(data)
print(summary)

# Simple visualization

wed.plot.production_curves(data, save_path='julia_production.png')
```

### 🏗️ [Field Analysis](field-analysis/)

Complete field analysis workflows for comprehensive evaluation.

**Comprehensive Field Studies:**
- **Julia Field Analysis**: Complete analysis of a major deepwater field
- **Jack/St. Malo Comparison**: Comparative analysis of adjacent fields
- **Stones Field Development**: Development planning and optimization
- **Anchor Field Economics**: Economic evaluation and investment analysis
- **Cascade-Chinook Integration**: Multi-field development analysis

**Analysis Workflows:**
- **Data Collection**: Systematic data gathering and validation
- **Production Analysis**: Decline curve analysis and forecasting
- **Economic Evaluation**: NPV analysis and sensitivity studies
- **Development Planning**: Well placement and phasing optimization
- **Risk Assessment**: Uncertainty analysis and risk quantification

**Field Study Template:**
```python
import worldenergydata as wed

# Complete field analysis workflow

def analyze_field(field_name):
    # 1. Data collection

    production_data = wed.bsee.load_production_data(field=field_name)
    well_data = wed.bsee.load_well_data(field=field_name)
    economic_params = wed.economic.load_field_parameters(field_name)

    # 2. Production analysis

    decline_analysis = wed.analysis.decline_curve_analysis(production_data)
    forecast = wed.analysis.production_forecast(decline_analysis, years=20)

    # 3. Economic evaluation

    npv_analysis = wed.economic.field_npv_analysis(
        production_forecast=forecast,
        economic_parameters=economic_params
    )

    # 4. Reporting and visualization

    report = wed.reporting.field_analysis_report(
        field_name=field_name,
        production_analysis=decline_analysis,
        economic_analysis=npv_analysis
    )

    return report

# Example usage

julia_analysis = analyze_field('Julia')
```

### 💰 [Economic Modeling](economic-modeling/)

Detailed economic evaluation examples for investment decision-making.

**Economic Analysis Types:**
- **NPV Analysis**: Net present value calculations with sensitivity analysis
- **Cash Flow Modeling**: Detailed cash flow projections and analysis
- **Risk Analysis**: Monte Carlo simulation and uncertainty quantification
- **Portfolio Optimization**: Multi-asset portfolio analysis and optimization
- **Tax and Fiscal Modeling**: Incorporating tax effects and fiscal terms

**Advanced Economic Examples:**
- **Deepwater Economics**: High-cost, high-risk project evaluation
- **Unconventional Economics**: Shale and tight rock economic analysis
- **LNG Project Economics**: Liquefied natural gas project evaluation
- **Wind Farm Economics**: Renewable energy project analysis
- **Joint Venture Analysis**: Multi-party project economic evaluation

**Economic Modeling Framework:**
```python
import worldenergydata as wed
import numpy as np

# Comprehensive economic analysis

def economic_evaluation(production_forecast, economic_assumptions):
    # Base case analysis

    base_npv = wed.economic.npv_analysis(
        production=production_forecast,
        oil_price=economic_assumptions['oil_price'],
        gas_price=economic_assumptions['gas_price'],
        discount_rate=economic_assumptions['discount_rate']
    )

    # Sensitivity analysis

    sensitivity_params = {
        'oil_price': np.linspace(40, 100, 13),
        'gas_price': np.linspace(2, 6, 9),
        'discount_rate': np.linspace(0.08, 0.15, 8)
    }

    sensitivity_results = wed.economic.sensitivity_analysis(
        base_case=base_npv,
        parameters=sensitivity_params
    )

    # Monte Carlo simulation

    monte_carlo_results = wed.economic.monte_carlo_analysis(
        production_forecast=production_forecast,
        price_distributions=economic_assumptions['price_distributions'],
        iterations=10000
    )

    return {
        'base_case': base_npv,
        'sensitivity': sensitivity_results,
        'monte_carlo': monte_carlo_results
    }
```

## Example Usage Patterns

### Data-Driven Analysis

Common patterns for data-driven energy analysis:

1. **Data Collection → Processing → Analysis → Visualization**
2. **Comparative Analysis**: Benchmarking and peer comparison
3. **Time Series Analysis**: Trend analysis and forecasting
4. **Statistical Analysis**: Correlation analysis and regression
5. **Machine Learning**: Predictive modeling and pattern recognition

### Industry-Specific Workflows

Specialized workflows for different industry segments:

- **Upstream**: Exploration, development, and production analysis
- **Midstream**: Transportation and processing analysis
- **Downstream**: Refining and marketing analysis
- **Integrated**: Full value chain analysis and optimization
- **Renewables**: Wind, solar, and storage analysis

### Decision Support Systems

Examples for business decision support:

- **Investment Decisions**: Go/no-go analysis and capital allocation
- **Operational Optimization**: Production optimization and cost reduction
- **Strategic Planning**: Long-term planning and portfolio management
- **Risk Management**: Risk identification and mitigation strategies
- **Regulatory Compliance**: Meeting regulatory requirements and reporting

## Interactive Examples

### Jupyter Notebooks

Complete analysis examples in interactive notebook format:

- **Field Development Planning**: Step-by-step field development analysis
- **Economic Sensitivity Studies**: Interactive sensitivity analysis
- **Production Forecasting**: Decline curve analysis with visualizations
- **Equipment Selection**: Equipment sizing and selection analysis
- **Market Analysis**: Energy market analysis and forecasting

### Web Applications

Browser-based interactive examples:

- **Field Dashboard**: Interactive field performance monitoring
- **Economic Calculator**: Web-based economic evaluation tool
- **Data Explorer**: Interactive data visualization and exploration
- **Comparison Tool**: Side-by-side field and well comparisons
- **Reporting System**: Automated report generation and distribution

## Code Quality and Standards

### Example Standards

- **Complete Workflows**: End-to-end analysis examples
- **Real Data**: Examples using actual field data where possible
- **Documentation**: Comprehensive comments and explanations
- **Error Handling**: Robust error handling and validation
- **Performance**: Optimized code for large datasets

### Testing and Validation

- **Reproducibility**: All examples can be reproduced independently
- **Validation**: Results validated against known benchmarks
- **Version Control**: Examples updated with library versions
- **Cross-Platform**: Examples work across different operating systems

### Learning Path

Recommended progression through examples:

1. **Start with Basic Usage**: Learn fundamental concepts
2. **Progress to Field Analysis**: Apply concepts to real problems
3. **Advanced Economic Modeling**: Master complex analysis techniques
4. **Custom Applications**: Develop specialized analysis workflows

---

*Choose an example category above to explore practical applications of WorldEnergyData for your specific analysis needs.*