# BSEE Test Data Documentation

## Overview
This directory contains BSEE-formatted test data for WorldEnergyData testing.

## File Descriptions

### Production Data (test_production.csv)
- Monthly production volumes for oil, gas, and water
- Production dates in YYYYMM format
- API well numbers (12-digit format)
- Days on production and average rates

### Well Data (test_wells.csv)
- Well identification and location information
- Spud and completion dates in YYYYMMDD format
- Depth measurements (MD, TVD)
- Surface coordinates

### Lease Data (test_leases.csv)
- OCS lease numbers and block information
- Lease effective and expiration dates
- Water depth ranges
- Lease holder information

### Completion Data (test_completions.csv)
- Completion information linked to wells
- Perforation depths (MD and TVD)
- Completion types and sand control methods
- Reservoir names

## Column Specifications

All files follow official BSEE data formats:
- Dates: YYYYMM (monthly) or YYYYMMDD (daily)
- API Numbers: 12-digit format (state + county + well + sidetrack)
- Volumes: Integer values in BBL (oil/water) or MCF (gas)
- Depths: Integer values in feet

## Usage

```python
import pandas as pd

# Load production data
production = pd.read_csv('test_production.csv')

# Convert date column to datetime
production['PRODUCTION_DATE'] = pd.to_datetime(
    production['PRODUCTION_DATE'], 
    format='%Y%m'
)
```

## Data Quality Notes

- All data is synthetic and for testing purposes only
- Production profiles follow realistic decline curves
- Well locations are within Gulf of Mexico OCS blocks
- Dates are internally consistent (spud < completion)
