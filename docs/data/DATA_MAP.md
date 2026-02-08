# WorldEnergyData - Data Map & Organization

**Last Updated:** 2025-10-02
**Total Data Size:** 2.1 GB (before cleanup) → ~600 MB (after cleanup)
**Total Files:** 2,997

---

## 📊 Data Modules Overview

| Module | Location | Size | Files | Status | Description |
|--------|----------|------|-------|--------|-------------|
| **BSEE** | `data/modules/bsee/` | 264 MB | ~2,500 | ✅ Active | US offshore oil & gas data |
| **SODIR** | `data/modules/sodir_zip_data/` | 156 MB | ~50 | ✅ Active | Norwegian offshore data |
| **Posters** | `data/modules/posters/` | 135 MB | ~100 | ✅ Active | Maps & visualizations |
| **LNGC** | `data/modules/lngc/` | 43 MB | ~50 | ✅ Active | LNG carrier fleet data |
| **Drilling Rigs** | `data/modules/drilling_rigs/` | 15 MB | ~20 | ✅ Active | Offshore rig information |
| **Wind** | `data/modules/wind/` | 7.1 MB | ~30 | ✅ Active | Wind energy data |
| **Equipment** | `data/modules/equipment/` | 300 KB | ~10 | ✅ Active | Equipment specifications |
| **Oil Price** | `data/modules/oil_price/` | 88 KB | ~5 | ✅ Active | Historical price data |
| **BSEE Backups** | `data/modules/bsee.backup*` | 1.5 GB | ~2,000 | ❌ DELETE | Duplicate backups |

---

## 🗺️ BSEE Data Structure (Primary Module)

### Current Active Data (`data/modules/bsee/current/`)

```
bsee/current/
│
├── completions/              # Well Completion Data
│   ├── completion_perforations.csv      # Perforation intervals
│   ├── completion_properties.csv        # Completion specifications
│   └── completion_summary.csv           # Summary information
│
├── geology/                  # Geological Data
│   ├── geology_markers.csv              # Formation markers
│   └── hydrocarbon_bearing_interval.csv # HC intervals
│
├── infrastructure/           # Lease & Block Data
│   └── all_bsee_blocks.csv             # Block information
│
├── operations/               # Well Operations
│   ├── cut_casings.csv                 # Casing operations
│   ├── ST_BP_and_tree_height.csv       # Surface equipment
│   ├── well_activity_bop_tests.csv     # BOP testing
│   ├── well_activity_open_hole.csv     # Open hole activities
│   ├── well_activity_remarks.csv       # Activity notes
│   └── well_activity_summary.csv       # Activity summaries
│
├── production/               # Production Data
│   └── production.csv                   # Historical production
│
└── wells/                    # Well Information
    ├── well_data.csv                    # Well metadata
    ├── well_directional_surveys.csv     # Directional data
    └── well_tubulars.csv                # Tubular specifications
```

---

## 📁 Data Access Patterns

### By Module

```python
# BSEE Data
from worldenergydata.modules.bsee.analysis import bsee_analysis

# Access current data
data_path = "data/modules/bsee/current/"

# Load completions
completions = pd.read_csv(f"{data_path}/completions/completion_summary.csv")

# Load production
production = pd.read_csv(f"{data_path}/production/production.csv")

# Load well data
wells = pd.read_csv(f"{data_path}/wells/well_data.csv")
```

### By Data Type

| Data Type | Primary Location | Use Case |
|-----------|-----------------|----------|
| **Well Metadata** | `wells/well_data.csv` | Basic well information, location, operator |
| **Production** | `production/production.csv` | Historical production volumes |
| **Completions** | `completions/*.csv` | Completion design, perforations |
| **Directional** | `wells/well_directional_surveys.csv` | Well trajectory data |
| **Geology** | `geology/*.csv` | Formation tops, HC intervals |
| **Operations** | `operations/*.csv` | Well activities, BOP tests |

---

## 🎯 Data Organization Principles

### Active Data Philosophy
1. **Current Data**: Only the most recent, processed data in `current/`
2. **Organized by Category**: Logical grouping (completions, geology, operations, etc.)
3. **CSV Format**: Standard, accessible format for analysis
4. **No Duplicates**: Single source of truth

### Archive Strategy
1. **Historical Data**: Store in `paleowells/` or external archives
2. **Raw Downloads**: Keep in `zip/` for reference
3. **Binaries**: Executables in `bin/`
4. **No Backups in Repo**: Use git for version control

---

## 📈 Data Quality Metrics

### BSEE Current Data Quality

| Metric | Value | Status |
|--------|-------|--------|
| **File Count** | 16 | ✅ Complete |
| **Size** | 4.2 MB | ✅ Reasonable |
| **Organization** | 6 categories | ✅ Well-structured |
| **Documentation** | README + Data Dictionary | ✅ Documented |
| **Format** | CSV | ✅ Standard |
| **Duplicates** | 0 | ✅ Clean |

---

## 🔄 Data Update Workflow

### Typical Update Process

```bash
# 1. Download new data
cd data/modules/bsee/zip/
wget [BSEE_DATA_URL]

# 2. Process and organize
python scripts/bsee_migration/process_new_data.py

# 3. Update current directory
# Move processed files to data/modules/bsee/current/

# 4. Archive old data (if needed)
mv data/modules/bsee/current/old_data.csv data/modules/bsee/archive/

# 5. Update documentation
# Update README.md and DATA_DICTIONARY.md

# 6. Commit changes
git add data/modules/bsee/current/
git commit -m "data: update BSEE data [date]"
```

---

## 🗄️ Storage Recommendations

### Git LFS Candidates
Consider using Git Large File Storage for:

| Module | Size | Reason |
|--------|------|--------|
| SODIR | 156 MB | Large compressed archives |
| Posters | 135 MB | Binary image files |
| LNGC | 43 MB | Large CSV files |

### Implementation:
```bash
# Install Git LFS
git lfs install

# Track large files
git lfs track "data/modules/sodir_zip_data/**"
git lfs track "data/modules/posters/**"
git lfs track "data/modules/lngc/**"

# Commit .gitattributes
git add .gitattributes
git commit -m "chore: configure Git LFS for large data files"
```

---

## 🔍 Data Discovery Guide

### Finding Specific Data

| Want to find... | Look in... | File name pattern |
|-----------------|-----------|-------------------|
| **Well production history** | `bsee/current/production/` | `production.csv` |
| **Well locations** | `bsee/current/wells/` | `well_data.csv` |
| **Completion design** | `bsee/current/completions/` | `completion_*.csv` |
| **Formation tops** | `bsee/current/geology/` | `geology_markers.csv` |
| **Directional surveys** | `bsee/current/wells/` | `well_directional_surveys.csv` |
| **BOP test records** | `bsee/current/operations/` | `well_activity_bop_tests.csv` |
| **Block information** | `bsee/current/infrastructure/` | `all_bsee_blocks.csv` |
| **Norwegian data** | `sodir_zip_data/` | Various `.zip` files |
| **Wind farm data** | `wind/` | Various `.csv` files |
| **LNG vessel specs** | `lngc/` | Various `.csv` files |

---

## 📚 Supporting Documentation

### Key Documents
- **[DATA_DICTIONARY.md](../bsee/DATA_DICTIONARY.md)** - Field definitions for BSEE data
- **[README.md](../bsee/README.md)** - BSEE module overview
- **[DATA_INVENTORY_ANALYSIS.md](DATA_INVENTORY_ANALYSIS.md)** - Detailed inventory and cleanup analysis

### Code References
- **Engine:** `src/worldenergydata/engine.py`
- **BSEE Analysis:** `src/worldenergydata/modules/bsee/analysis/`
- **Financial Analysis:** `src/worldenergydata/modules/bsee/analysis/financial/`
- **Data Loaders:** `src/worldenergydata/modules/bsee/analysis/financial/data_loader.py`

---

## 🚀 Quick Start with Data

### Loading BSEE Data

```python
import pandas as pd
from pathlib import Path

# Set base path
data_path = Path("data/modules/bsee/current")

# Load well data
wells = pd.read_csv(data_path / "wells" / "well_data.csv")
print(f"Loaded {len(wells)} wells")

# Load production
production = pd.read_csv(data_path / "production" / "production.csv")
print(f"Loaded {len(production)} production records")

# Load completions
completions = pd.read_csv(data_path / "completions" / "completion_summary.csv")
print(f"Loaded {len(completions)} completion records")
```

### Using the Engine

```python
from worldenergydata.engine import Engine

# Initialize engine with config
engine = Engine(config_file="config.yaml")

# Run analysis
results = engine.run_analysis()
```

---

## 💡 Best Practices

### Data Management
1. ✅ Keep only current/active data in repository
2. ✅ Use descriptive directory names
3. ✅ Document data sources and update dates
4. ✅ Use CSV format for tabular data
5. ✅ Compress large files (zip, tar.gz)
6. ❌ Don't commit backup directories
7. ❌ Don't commit raw/unprocessed downloads
8. ❌ Don't commit temporary analysis files

### File Naming
```
# Good
well_data_2025.csv
production_monthly_summary.csv
completion_perforations.csv

# Avoid
data.csv
temp_backup_copy_final_v2.csv
```

---

## 🎓 Learning Resources

### Understanding the Data
1. **BSEE Website:** [https://www.bsee.gov/](https://www.bsee.gov/)
2. **SODIR Portal:** [https://www.sodir.no/](https://www.sodir.no/)
3. **Data Dictionary:** See `data/modules/bsee/DATA_DICTIONARY.md`

### Analysis Examples
- Check `docs/analysis-guides/` for tutorials
- See `docs/examples/` for code examples
- Review tests in `tests/modules/` for usage patterns

---

**Generated:** 2025-10-02
**Maintainer:** WorldEnergyData Team
**Next Review:** After data cleanup

---

## Machine-Readable Data Catalog

A machine-readable catalog of all datasets is available at:
- **YAML**: `data/catalog/data-catalog.yml`
- **JSON**: Generate with `python scripts/generate_data_catalog.py --format json`

Regenerate after adding new data:
```bash
python scripts/generate_data_catalog.py
```
