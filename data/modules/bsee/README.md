# BSEE Data Module

> Bureau of Safety and Environmental Enforcement (BSEE) Data Repository
> Last Updated: 2025-08-21
> Status: Production Ready

## Overview

This module contains comprehensive offshore oil and gas data from the Bureau of Safety and Environmental Enforcement (BSEE), covering Gulf of Mexico operations. The data has been consolidated and organized for efficient access and analysis.

## Directory Structure

```
bsee/
├── current/              # Latest authoritative data (actively maintained)
│   ├── production/       # Production volumes and metrics
│   ├── wells/           # Well information and surveys
│   ├── completions/     # Completion data and perforations
│   ├── operations/      # Operational activities and tests
│   ├── geology/         # Geological markers and intervals
│   └── infrastructure/  # Blocks and field infrastructure
├── archive/             # Historical data (compressed)
├── analysis_data/       # Analysis-specific datasets
├── bin/                 # Binary format files
├── raw/                 # Unprocessed source data
└── zip/                 # Compressed source files
```

## Quick Start

### Loading Production Data
```python
import pandas as pd
from pathlib import Path

# Define base path
bsee_data = Path("data/modules/bsee/current")

# Load production data
production = pd.read_csv(bsee_data / "production/production.csv")
print(f"Loaded {len(production)} production records")
```

### Loading Well Data
```python
# Load well master data
wells = pd.read_csv(bsee_data / "wells/well_data.csv")

# Load directional surveys
surveys = pd.read_csv(bsee_data / "wells/well_directional_surveys.csv")

# Load tubular information
tubulars = pd.read_csv(bsee_data / "wells/well_tubulars.csv")
```

### Loading Completion Data
```python
# Load completion summary
completions = pd.read_csv(bsee_data / "completions/completion_summary.csv")

# Load perforation data
perforations = pd.read_csv(bsee_data / "completions/completion_perforations.csv")
```

## Data Categories

### 1. Production Data (`current/production/`)
- **production.csv**: Monthly oil and gas production volumes by well
  - Fields: Well API, Production Date, Oil (BBL), Gas (MCF), Water (BBL)
  - Update Frequency: Monthly
  - Records: ~100 sample records

### 2. Wells Data (`current/wells/`)
- **well_data.csv**: Comprehensive well information (57,281 records)
  - Well identifiers, locations, operators, status
  - Spud dates, completion dates, depths
  
- **well_directional_surveys.csv**: Directional drilling data
  - Measured depth, inclination, azimuth
  - True vertical depth calculations
  
- **well_tubulars.csv**: Casing and tubing specifications
  - Pipe sizes, weights, grades
  - Setting depths

### 3. Completions Data (`current/completions/`)
- **completion_summary.csv**: Overview of well completions
  - Completion types, dates, intervals
  
- **completion_perforations.csv**: Perforation details
  - Top/bottom depths, shot density
  
- **completion_properties.csv**: Completion characteristics
  - Sand control, artificial lift methods

### 4. Operations Data (`current/operations/`)
- **well_activity_summary.csv**: Drilling and workover activities
- **well_activity_bop_tests.csv**: Blowout preventer test records
- **well_activity_open_hole.csv**: Open hole operations
- **well_activity_remarks.csv**: Operational notes and comments
- **ST_BP_and_tree_height.csv**: Subsea tree and BOP stack data
- **cut_casings.csv**: Casing cut and pull records

### 5. Geology Data (`current/geology/`)
- **geology_markers.csv**: Geological formation tops
  - Formation names, depths, ages
  
- **hydrocarbon_bearing_interval.csv**: Pay zone information
  - Net pay thickness, porosity, permeability

### 6. Infrastructure Data (`current/infrastructure/`)
- **all_bsee_blocks.csv**: Offshore block information
  - Block numbers, water depths, operators

## Data Access Patterns

### Best Practices

1. **Always use the `current/` directory for analysis**
   ```python
   # Good
   data_path = Path("data/modules/bsee/current/production/production.csv")
   
   # Avoid (legacy path)
   # data_path = Path("data/modules/bsee/legacy/...")
   ```

2. **Handle large files efficiently**
   ```python
   # For large files, use chunking
   chunk_size = 10000
   for chunk in pd.read_csv(file_path, chunksize=chunk_size):
       process_chunk(chunk)
   ```

3. **Use consistent date parsing**
   ```python
   # Parse dates consistently
   df = pd.read_csv(file_path, parse_dates=['PRODUCTION_DATE'])
   ```

### Common Queries

#### Get Production by Field
```python
# Load and aggregate production by field
production = pd.read_csv(bsee_data / "production/production.csv")
field_production = production.groupby('FIELD_NAME').agg({
    'OIL_BBL': 'sum',
    'GAS_MCF': 'sum'
}).sort_values('OIL_BBL', ascending=False)
```

#### Find Active Wells
```python
# Load well data and filter for active wells
wells = pd.read_csv(bsee_data / "wells/well_data.csv")
active_wells = wells[wells['WELL_STATUS'] == 'ACTIVE']
print(f"Found {len(active_wells)} active wells")
```

#### Analyze Completion Types
```python
# Analyze completion methods
completions = pd.read_csv(bsee_data / "completions/completion_summary.csv")
completion_types = completions['COMPLETION_TYPE'].value_counts()
```

## Data Quality Notes

### Validation Status
- ✅ All files validated for row count integrity
- ✅ Checksums verified for critical files
- ✅ No data loss during consolidation
- ✅ Performance tested for fast loading

### Known Limitations
1. Sample data files contain first 100 rows for testing
2. Some historical data is archived and compressed
3. Binary files in `bin/` require special readers

### Data Updates
- Source: BSEE public data portal
- Update Frequency: Varies by dataset (monthly to annually)
- Last Update: Check file modification dates

## Migration History

### 2025-08-21 Consolidation
- Consolidated 666 files into organized structure
- Removed 44 duplicate files
- Archived 378 legacy files
- Reduced storage by 18% (66MB saved)
- Created logical categorization

### Rollback Instructions
If needed, the original structure can be restored:
```bash
# Restore from backup
rm -rf data/modules/bsee
mv data/modules/bsee.backup_20250821_064447 data/modules/bsee
```

## Technical Specifications

### File Formats
- **CSV**: Primary format for structured data
- **Binary (.bin)**: Historical format for some datasets
- **Compressed (.zip, .tar.gz)**: Archived and source files

### Character Encoding
- UTF-8 for all text files
- Handle with `encoding='utf-8', errors='ignore'` for compatibility

### Large Files
Files over 50MB are tracked with Git LFS:
- `archive/*.tar.gz`
- Some files in `bin/`

## Support and Maintenance

### Directory Ownership
- Module: BSEE
- Maintainer: WorldEnergyData Team
- Contact: Via GitHub Issues

### Reporting Issues
1. Check if file exists in `current/` directory
2. Verify path construction is correct
3. Report issues with file path and error message

### Contributing
- Follow existing structure when adding new data
- Update this README when adding new datasets
- Maintain backward compatibility where possible

## Related Modules

- **Financial Analysis**: Uses production data for NPV calculations
- **Field Analysis**: Deepwater field performance studies
- **Well Engineering**: Directional drilling and completion analysis

## License and Attribution

Data Source: U.S. Bureau of Safety and Environmental Enforcement (BSEE)
- Public domain data
- No warranty implied
- Users responsible for data validation

---

*For questions or improvements, please submit a GitHub issue or pull request.*