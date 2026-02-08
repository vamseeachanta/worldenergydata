# Comprehensive Report Generation Workflow

## Overview
This document provides a step-by-step workflow for generating comprehensive reports using the new reporting system.

## Prerequisites
- BSEE data repository access
- Python environment with required packages
- Report templates configured
- Price deck and cost assumptions defined

## Workflow Steps

### Phase 1: Data Collection (Steps 1-3)

#### Step 1: Initialize Report Parameters
```python
# Define report scope
parameters = {
    "report_type": "field",  # Options: well, lease, field, block
    "entity_name": "Jack",   # Target entity
    "date_range": {
        "start": "2020-01-01",
        "end": "2024-12-31"
    },
    "output_formats": ["excel", "pdf", "html"]
}
```

#### Step 2: Query BSEE Data Sources
```python
# Collect data from multiple sources
data_sources = {
    "production": query_production_data(parameters),
    "well_data": query_well_master(parameters),
    "lease_info": query_lease_data(parameters),
    "directional": query_directional_surveys(parameters)
}
```

#### Step 3: Data Validation
- Validate API numbers format
- Check date consistency
- Identify missing values
- Flag data anomalies
- Generate data quality report

### Phase 2: Data Processing (Steps 4-6)

#### Step 4: Hierarchical Aggregation
```python
# Build hierarchy from bottom up
hierarchy = {
    "wells": aggregate_well_data(data_sources),
    "leases": aggregate_to_lease_level(wells),
    "fields": aggregate_to_field_level(leases),
    "blocks": aggregate_to_block_level(fields)
}
```

#### Step 5: Apply Business Logic
- Calculate derived metrics
  - Days to drill = Last BSEE Date - Spud Date
  - Well productivity = Cumulative Production / Days Online
  - Field decline rate = Monthly production trend
- Apply allocation rules
- Handle joint ventures and partnerships

#### Step 6: Economic Calculations
```python
# Apply economic model
economics = {
    "revenue": calculate_revenue(production, price_deck),
    "costs": apply_cost_model(operations, cost_assumptions),
    "cash_flow": generate_cash_flow(revenue, costs),
    "npv": calculate_npv(cash_flow, discount_rate=0.10),
    "metrics": calculate_economic_metrics(cash_flow)
}
```

### Phase 3: Report Generation (Steps 7-9)

#### Step 7: Template Selection
```python
# Select appropriate template based on report type
template_map = {
    "field": "field_summary_template.jinja2",
    "lease": "lease_detail_template.jinja2",
    "well": "well_analysis_template.jinja2",
    "block": "block_overview_template.jinja2"
}
template = load_template(template_map[report_type])
```

#### Step 8: Data Population
```python
# Populate template with processed data
report_data = {
    "metadata": {
        "report_date": datetime.now(),
        "data_source": "BSEE",
        "entity": entity_name
    },
    "summary": hierarchy[report_type],
    "details": detailed_data,
    "economics": economics,
    "visualizations": charts
}
rendered_report = template.render(report_data)
```

#### Step 9: Visualization Generation
- Production trend charts
- Well timeline Gantt charts
- Economic waterfall charts
- Field comparison bar charts
- Interactive dashboards

### Phase 4: Export and Delivery (Steps 10-12)

#### Step 10: Multi-Format Export
```python
# Generate output formats
exporters = {
    "excel": ExcelExporter(),
    "pdf": PDFExporter(),
    "html": HTMLExporter(),
    "json": JSONExporter()
}

for format in output_formats:
    exporter = exporters[format]
    output_file = exporter.export(rendered_report)
    print(f"Generated: {output_file}")
```

#### Step 11: Quality Assurance
- Verify calculations against go-by reports
- Check formatting and layout
- Validate visualizations
- Review economic metrics
- Ensure data consistency across formats

#### Step 12: Report Delivery
```python
# Package and deliver reports
delivery = {
    "location": "reports/output/",
    "files": generated_files,
    "metadata": report_metadata,
    "timestamp": datetime.now()
}
archive_reports(delivery)
notify_stakeholders(delivery)
```

## Execution Commands

### Command Line Interface
```bash
# Generate field report
python -m worldenergydata.reports.comprehensive \
    --type field \
    --name "Jack" \
    --start-date 2020-01-01 \
    --end-date 2024-12-31 \
    --output excel,pdf,html

# Generate multiple reports
python -m worldenergydata.reports.comprehensive \
    --type field \
    --names "Jack,Julia,St. Malo,Stones" \
    --batch \
    --parallel
```

### Python API
```python
from worldenergydata.bsee.reports.comprehensive import ReportController

# Initialize controller
controller = ReportController()

# Generate single report
report = controller.generate_report(
    report_type="field",
    entity_name="Jack",
    date_range=("2020-01-01", "2024-12-31"),
    output_formats=["excel", "pdf"]
)

# Batch processing
reports = controller.batch_generate(
    report_type="field",
    entity_names=["Jack", "Julia", "St. Malo", "Stones"],
    parallel=True
)
```

## Performance Optimization

### Caching Strategy
- Cache aggregated data at lease and field levels
- Store calculated metrics for reuse
- Implement incremental updates for new data

### Parallel Processing
- Process multiple entities concurrently
- Parallelize aggregation calculations
- Async visualization generation

### Memory Management
- Stream large datasets
- Chunk processing for massive reports
- Garbage collection after each phase

## Error Handling

### Data Issues
- Missing data: Use interpolation or last known value
- Invalid data: Flag and exclude from calculations
- Inconsistent data: Apply validation rules and corrections

### System Issues
- Database timeout: Implement retry logic
- Memory overflow: Switch to chunked processing
- Export failure: Save intermediate results

## Validation Checklist

### Pre-Generation
- [ ] Data sources accessible
- [ ] Templates configured
- [ ] Price deck updated
- [ ] Cost assumptions verified

### During Generation
- [ ] Data quality checks passed
- [ ] Aggregations calculated correctly
- [ ] Economics computed accurately
- [ ] Visualizations generated

### Post-Generation
- [ ] All formats exported successfully
- [ ] Reports match go-by structure
- [ ] Calculations verified
- [ ] Documentation complete

## Troubleshooting Guide

### Common Issues

1. **Missing Well Data**
   - Check API number format
   - Verify well exists in BSEE database
   - Review date range parameters

2. **Incorrect Aggregations**
   - Validate hierarchy relationships
   - Check allocation factors
   - Review aggregation rules

3. **Economic Discrepancies**
   - Verify price deck values
   - Check royalty rates
   - Review cost assumptions

4. **Export Failures**
   - Check disk space
   - Verify write permissions
   - Review template syntax

## Appendix

### A. Data Field Mappings
See `hierarchical_data_flow.json` for complete field mappings

### B. Template Variables
See `report_template.json` for available template variables

### C. Visualization Types
See `visualization_config.json` for chart configurations

### D. Economic Formulas
See `economic_framework.json` for calculation details

---
*Version 1.0 - Comprehensive Report System Workflow*
*Last Updated: 2025-08-22*