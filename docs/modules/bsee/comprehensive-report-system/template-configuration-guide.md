# Template Configuration Guide

## Table of Contents
1. [Overview](#overview)
2. [Template Types](#template-types)
3. [Configuration Structure](#configuration-structure)
4. [Customization Options](#customization-options)
5. [Template Variables](#template-variables)
6. [Examples](#examples)
7. [Advanced Configuration](#advanced-configuration)

## Overview

The BSEE Comprehensive Report System uses Jinja2-based templates for flexible report generation. Templates can be configured through YAML files, allowing customization of content, formatting, and data presentation without modifying code.

## Template Types

### Available Templates

| Template | Purpose | Key Sections | Best Use Case |
|----------|---------|--------------|---------------|
| **Compliance** | Regulatory reporting | Quotas, Environmental, Safety | Audits, Regulatory submissions |
| **Economic** | Financial analysis | NPV, Revenue, Costs, Sensitivity | Investment decisions, Planning |
| **Operational** | Performance metrics | Efficiency, Reliability, Maintenance | Operations management |
| **Executive** | High-level overview | KPIs, Traffic lights, Benchmarks | Board presentations |

## Configuration Structure

### Basic Template Configuration

```yaml
# template_config.yaml
template:
  type: economic  # compliance, economic, operational, executive
  version: "1.0"
  
  # Template-specific settings
  settings:
    currency: USD
    decimal_places: 2
    date_format: "%Y-%m-%d"
    
  # Sections to include
  sections:
    - summary
    - production_metrics
    - financial_analysis
    - visualizations
    
  # Custom variables
  variables:
    company_name: "BSEE Operations"
    report_title: "Monthly Economic Report"
    logo_path: "assets/logo.png"
```

### Hierarchical Configuration

```yaml
# Configure templates for different organizational levels
templates:
  block:
    type: executive
    sections:
      - executive_summary
      - field_rollup
      - strategic_metrics
      
  field:
    type: economic
    sections:
      - field_summary
      - well_economics
      - production_forecast
      
  lease:
    type: operational
    sections:
      - well_status
      - production_details
      - maintenance_schedule
```

## Customization Options

### Section Configuration

#### Summary Section
```yaml
sections:
  summary:
    enabled: true
    position: 1
    settings:
      include_logo: true
      show_period: true
      highlight_changes: true
    fields:
      - organization_unit
      - reporting_period
      - total_production
      - total_revenue
      - key_metrics
```

#### Production Metrics Section
```yaml
sections:
  production_metrics:
    enabled: true
    position: 2
    settings:
      group_by: product  # product, well, time
      aggregation: monthly
      show_trends: true
    metrics:
      - oil_production
      - gas_production
      - water_production
      - injection_volumes
    charts:
      - type: line
        title: "Production Trends"
      - type: bar
        title: "Monthly Comparison"
```

#### Financial Analysis Section
```yaml
sections:
  financial_analysis:
    enabled: true
    position: 3
    settings:
      currency: USD
      show_calculations: true
    components:
      revenue:
        show_breakdown: true
        include_netback: true
      costs:
        categories:
          - operating
          - capital
          - abandonment
      profitability:
        metrics:
          - npv
          - irr
          - payback_period
```

### Visualization Configuration

```yaml
visualizations:
  enabled: true
  
  charts:
    production_chart:
      type: line
      data_source: production_metrics
      settings:
        height: 400
        width: 800
        colors:
          oil: "#8B4513"
          gas: "#FF6B6B"
          water: "#4169E1"
    
    revenue_waterfall:
      type: waterfall
      data_source: financial_analysis
      settings:
        show_connectors: true
        show_totals: true
    
    well_map:
      type: geographic
      data_source: well_locations
      settings:
        zoom_level: 10
        show_production: true
```

### Formatting Configuration

```yaml
formatting:
  numbers:
    decimal_separator: "."
    thousands_separator: ","
    decimal_places:
      production: 0
      financial: 2
      percentages: 1
  
  dates:
    format: "%B %d, %Y"  # January 15, 2024
    timezone: "US/Central"
  
  currency:
    symbol: "$"
    position: before  # before or after
    
  tables:
    style: "bordered"  # bordered, striped, hover
    header_color: "#2C3E50"
    alternating_rows: true
    
  colors:
    primary: "#2C3E50"
    secondary: "#34495E"
    success: "#27AE60"
    warning: "#F39C12"
    danger: "#E74C3C"
```

## Template Variables

### System Variables
These variables are automatically available in all templates:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{report_date}}` | Current date | 2024-01-15 |
| `{{organization_unit}}` | Unit being reported | Jack Field |
| `{{organization_level}}` | Hierarchy level | field |
| `{{reporting_period}}` | Period covered | 2024-01 to 2024-12 |
| `{{data_source}}` | Data source info | BSEE Repository |
| `{{generation_time}}` | Report generation timestamp | 2024-01-15 14:30:00 |

### Data Variables
Access aggregated data in templates:

```jinja2
<!-- Production data -->
{{production.oil.total | format_barrels}}
{{production.gas.total | format_mcf}}
{{production.water.total | format_barrels}}

<!-- Financial data -->
{{revenue.total | format_currency}}
{{costs.operating | format_currency}}
{{metrics.npv | format_currency}}

<!-- Well data -->
{% for well in wells %}
  {{well.api_number}} - {{well.status}}
  Production: {{well.production.oil | format_barrels}}
{% endfor %}
```

### Custom Variables
Define custom variables in configuration:

```yaml
variables:
  company:
    name: "Energy Corporation"
    logo: "path/to/logo.png"
    website: "www.example.com"
  
  report:
    author: "Analytics Team"
    classification: "Internal Use Only"
    distribution: ["Management", "Operations"]
  
  thresholds:
    min_production: 100  # barrels/day
    target_efficiency: 0.85
    max_water_cut: 0.95
```

Use in templates:
```jinja2
<header>
  <img src="{{company.logo}}" alt="{{company.name}}">
  <h1>{{report_title}}</h1>
  <p>Prepared by: {{report.author}}</p>
</header>
```

## Examples

### Example 1: Compliance Report Configuration

```yaml
# compliance_report.yaml
template:
  type: compliance
  version: "2.0"
  
settings:
  regulatory_framework: "BSEE 2024"
  include_citations: true
  
sections:
  production_compliance:
    enabled: true
    quotas:
      oil: 50000  # barrels/month
      gas: 100000  # mcf/month
    thresholds:
      variance_allowed: 0.05  # 5%
      
  environmental_compliance:
    enabled: true
    metrics:
      - spill_incidents
      - emissions
      - water_discharge
    limits:
      spills_per_year: 0
      emissions_threshold: 1000  # tons CO2
      
  safety_compliance:
    enabled: true
    metrics:
      - trir  # Total Recordable Incident Rate
      - ltir  # Lost Time Incident Rate
    targets:
      trir: 1.0
      ltir: 0.5
      
visualizations:
  compliance_dashboard:
    type: gauge
    metrics: [quota_compliance, environmental_score, safety_score]
    colors:
      good: "#27AE60"
      warning: "#F39C12"
      critical: "#E74C3C"
```

### Example 2: Economic Report with Sensitivity Analysis

```yaml
# economic_report.yaml
template:
  type: economic
  
settings:
  discount_rate: 0.10  # 10%
  tax_rate: 0.35
  inflation_rate: 0.03
  
sections:
  sensitivity_analysis:
    enabled: true
    variables:
      oil_price:
        base: 75
        range: [50, 60, 70, 80, 90, 100]
      gas_price:
        base: 3.50
        range: [2.50, 3.00, 3.50, 4.00, 4.50, 5.00]
    metrics:
      - npv
      - irr
      - payback_period
      
  cash_flow:
    enabled: true
    periods: 20  # years
    components:
      - revenue
      - operating_costs
      - capital_costs
      - taxes
      - net_cash_flow
      
visualizations:
  sensitivity_matrix:
    type: heatmap
    x_axis: oil_price
    y_axis: gas_price
    value: npv
    color_scale: "RdYlGn"
```

### Example 3: Executive Dashboard Configuration

```yaml
# executive_dashboard.yaml
template:
  type: executive
  
settings:
  refresh_interval: 3600  # seconds
  comparison_period: year_over_year
  
sections:
  kpi_summary:
    enabled: true
    layout: grid  # grid, list, cards
    kpis:
      - id: total_production
        title: "Total Production"
        unit: "BOE"
        target: 1000000
        traffic_light: true
        
      - id: revenue
        title: "Revenue"
        unit: "USD"
        format: currency
        comparison: true
        
      - id: operating_efficiency
        title: "Efficiency"
        unit: "%"
        format: percentage
        threshold:
          good: 0.85
          warning: 0.70
          critical: 0.60
          
  competitive_benchmark:
    enabled: true
    peers: ["Competitor A", "Competitor B", "Industry Avg"]
    metrics:
      - production_per_well
      - operating_cost_per_boe
      - finding_cost
      
visualizations:
  executive_charts:
    - type: gauge
      title: "Performance Score"
      max: 100
      zones:
        - [0, 60, "red"]
        - [60, 80, "yellow"]
        - [80, 100, "green"]
        
    - type: radar
      title: "Competitive Position"
      categories: [Production, Costs, Efficiency, Safety, Environment]
```

## Advanced Configuration

### Template Inheritance

```yaml
# base_template.yaml
base_template:
  common_settings:
    company_name: "BSEE Operations"
    date_format: "%Y-%m-%d"
    currency: USD
    
  common_sections:
    header:
      logo: true
      title: true
      date: true
    footer:
      page_numbers: true
      confidentiality: "Internal Use Only"

# Extended template
template:
  extends: base_template
  type: economic
  
  # Override specific settings
  settings:
    currency: EUR  # Override base currency
    
  # Add new sections
  sections:
    - financial_analysis
    - sensitivity_analysis
```

### Conditional Sections

```yaml
sections:
  production_forecast:
    enabled: true
    condition: "{{wells|length > 10}}"  # Only show if more than 10 wells
    
  decline_analysis:
    enabled: true
    condition: "{{production_history_months >= 12}}"  # Need 12 months of data
    
  peer_comparison:
    enabled: true
    condition: "{{organization_level == 'field'}}"  # Only for field level
```

### Custom Filters

```yaml
filters:
  custom:
    - name: format_api
      function: "lambda x: f'{x[:2]}-{x[2:5]}-{x[5:]}'"
      
    - name: risk_category
      function: |
        lambda x: 'High' if x > 0.7 else 'Medium' if x > 0.3 else 'Low'
        
    - name: production_status
      function: |
        lambda x: 'Producing' if x > 0 else 'Shut-in'
```

### Multi-Language Support

```yaml
localization:
  default: en
  supported:
    - en
    - es
    
  translations:
    en:
      title: "Production Report"
      oil: "Oil"
      gas: "Gas"
      revenue: "Revenue"
      
    es:
      title: "Informe de Producción"
      oil: "Petróleo"
      gas: "Gas"
      revenue: "Ingresos"
```

## Best Practices

1. **Version Control**: Always version your template configurations
2. **Validation**: Test configurations with sample data before production use
3. **Documentation**: Comment complex configurations
4. **Modularity**: Use template inheritance for common elements
5. **Performance**: Disable unused sections to improve generation speed
6. **Consistency**: Maintain consistent naming conventions
7. **Security**: Never include sensitive data in template configurations

## Troubleshooting

### Common Issues

**Issue**: Template not found
```yaml
# Solution: Verify template path
template:
  path: "templates/custom/"  # Relative to module root
  type: "my_custom_template"
```

**Issue**: Variable not rendering
```yaml
# Solution: Check variable name and availability
debug:
  show_available_variables: true
  log_missing_variables: true
```

**Issue**: Chart not displaying
```yaml
# Solution: Verify data source and format
visualizations:
  debug: true
  fallback: table  # Show table if chart fails
```

---

For more customization options, see the [Template Customization Guide](template-customization-guide.md) or [Developer Guide](developer-guide.md).