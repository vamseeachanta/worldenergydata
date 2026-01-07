# Data Validators Module

## Overview

Data validation utilities with quality scoring and interactive reporting.

**Installed from**: workspace-hub skill `data-validation-reporter`
**Source**: `skills/workspace-hub/data-validation-reporter/`

## Quick Start

```python
from src.validators import DataValidator
import pandas as pd
from pathlib import Path

# Initialize
validator = DataValidator(config_path=Path("config/validation/validation_config.yaml"))

# Validate
df = pd.read_csv("data/your_data.csv")
results = validator.validate_dataframe(
    df=df,
    required_fields=["id", "name"],
    unique_field="id"
)

# Generate report
validator.generate_interactive_report(
    results,
    Path("reports/validation/report.html")
)
```

## Features

- Quality scoring (0-100 scale)
- Missing data analysis
- Type validation
- Duplicate detection
- Interactive Plotly dashboards
- YAML configuration

## Examples

Run the examples:
```bash
python examples/validation_examples.py
```

## Documentation

- Full skill docs: workspace-hub/skills/data-validation-reporter/SKILL.md
- Configuration: config/validation/validation_config.yaml

## Dependencies

Required (add to your dependency file):
- pandas>=1.5.0
- plotly>=5.14.0
- pyyaml>=6.0
