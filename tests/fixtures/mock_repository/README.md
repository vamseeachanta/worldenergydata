# Mock Data Repository

## Overview

This directory contains correctly formatted mock data for testing WorldEnergyData modules. All data follows official BSEE and industry standards.

## Directory Structure

```
mock_repository/
├── bsee/
│   ├── production/          # Production data by field
│   ├── wells/               # Well master data
│   ├── leases/              # Lease information
│   └── completions/         # Completion data
├── financial/
│   ├── npv_inputs/          # NPV calculation inputs
│   └── economic_params/     # Economic parameters
└── reference/
    ├── field_mappings/      # Field name mappings
    └── api_lookups/         # API number references
```

## Data Formats

### BSEE Production Data
- **Format**: CSV with BSEE standard columns
- **Date Format**: YYYYMM for monthly production
- **Volumes**: Integer BBL (oil/water), MCF (gas)
- **API Numbers**: 12-digit format

### Financial Data
- **Format**: CSV/Excel with standardized templates
- **Currency**: USD
- **Dates**: YYYY-MM-DD format
- **Rates**: Decimal format (0.10 = 10%)

## Available Test Datasets

### 1. Small Dataset (Quick Tests)
- 5 wells, 12 months production
- File: `bsee/production/small_dataset.csv`
- Size: ~1 KB

### 2. Medium Dataset (Integration Tests)
- 50 wells, 36 months production
- File: `bsee/production/medium_dataset.csv`
- Size: ~50 KB

### 3. Large Dataset (Performance Tests)
- 500 wells, 60 months production
- File: `bsee/production/large_dataset.csv`
- Size: ~1 MB

### 4. Edge Cases Dataset
- Wells with missing data
- Negative production (adjustments)
- Zero production months
- File: `bsee/production/edge_cases.csv`

## Field-Specific Data

### Anchor Field
- Location: Walker Ridge, Gulf of Mexico
- Water Depth: ~5,000 feet
- Files: `bsee/production/anchor/`

### Julia Field
- Location: Walker Ridge, Gulf of Mexico
- Water Depth: ~7,000 feet
- Files: `bsee/production/julia/`

### Jack Field
- Location: Walker Ridge, Gulf of Mexico
- Water Depth: ~7,000 feet
- Files: `bsee/production/jack/`

### St. Malo Field
- Location: Walker Ridge, Gulf of Mexico
- Water Depth: ~7,000 feet
- Files: `bsee/production/st_malo/`

## Usage Examples

### Loading Production Data

```python
import pandas as pd
from pathlib import Path

# Load small dataset for unit tests
test_data_dir = Path('tests/data/mock_repository')
production = pd.read_csv(test_data_dir / 'bsee/production/small_dataset.csv')

# Convert date column
production['PRODUCTION_DATE'] = pd.to_datetime(
    production['PRODUCTION_DATE'], 
    format='%Y%m'
)
```

### Using in Tests

```python
import pytest
from pathlib import Path

@pytest.fixture
def mock_production_data():
    """Provide mock production data for tests."""
    data_path = Path('tests/data/mock_repository/bsee/production/small_dataset.csv')
    return pd.read_csv(data_path)

def test_production_analysis(mock_production_data):
    """Test production analysis with mock data."""
    assert len(mock_production_data) > 0
    assert 'MON_O_PROD_VOL' in mock_production_data.columns
```

## Data Generation

Mock data is generated using:
- `worldenergydata.testing.data.bsee_data_converter`
- Realistic production decline curves
- Statistically valid distributions
- Consistent relationships between fields

## Quality Assurance

All mock data is:
- ✅ Format validated against BSEE specifications
- ✅ Internally consistent (dates, volumes, etc.)
- ✅ Reproducible with seed values
- ✅ Free of personally identifiable information
- ✅ Safe for public repositories

## Updating Mock Data

To regenerate mock data:

```python
from worldenergydata.testing.data.bsee_data_converter import BSEEDataConverter

converter = BSEEDataConverter(seed=42)  # Use seed for reproducibility
converter.save_test_data('tests/data/mock_repository/bsee', prefix='test')
```

## Notes

- All data is synthetic and for testing only
- No real production data or confidential information
- Follows industry-standard formats for compatibility
- Optimized for testing different scenarios