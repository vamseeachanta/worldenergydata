# WorldEnergyData Repository - Data Inventory & Cleanup Analysis

**Generated:** 2025-10-02
**Total Files Analyzed:** 2,997
**Total Data Size:** 2.1 GB

## Executive Summary

This repository contains energy data from multiple sources including BSEE (Bureau of Safety and Environmental Enforcement), SODIR (Norwegian Petroleum Directorate), wind energy, LNG carriers, and drilling rigs.

**Critical Finding:** There are **4 duplicate BSEE backup directories** consuming **1.5 GB** (70% of total data) that can be safely deleted.

---

## Data Inventory Map

### 1. BSEE (Bureau of Safety and Environmental Enforcement) Data
**Location:** `data/modules/bsee/`
**Size:** 264 MB (current) + 1.5 GB (backups)
**Status:** ✅ Active, ⚠️ Has duplicates

#### Current Active Data Structure:
```
data/modules/bsee/
├── current/                          # 4.2 MB - ACTIVE DATA
│   ├── completions/
│   │   ├── completion_perforations.csv
│   │   ├── completion_properties.csv
│   │   └── completion_summary.csv
│   ├── geology/
│   │   ├── geology_markers.csv
│   │   └── hydrocarbon_bearing_interval.csv
│   ├── infrastructure/
│   │   └── all_bsee_blocks.csv
│   ├── operations/
│   │   ├── cut_casings.csv
│   │   ├── ST_BP_and_tree_height.csv
│   │   ├── well_activity_bop_tests.csv
│   │   ├── well_activity_open_hole.csv
│   │   ├── well_activity_remarks.csv
│   │   └── well_activity_summary.csv
│   ├── production/
│   │   └── production.csv
│   └── wells/
│       ├── well_data.csv
│       ├── well_directional_surveys.csv
│       └── well_tubulars.csv
├── bin/                              # Binary/executable files
├── zip/                              # Compressed archives
├── paleowells/                       # Historical well data
├── raw/                              # Empty (0 bytes)
├── archive/                          # Empty (512 bytes)
├── analysis_data/                    # Empty
├── README.md                         # Documentation
└── DATA_DICTIONARY.md                # Data field definitions
```

#### BSEE Data Categories:
1. **Completions Data** - Well completion information, perforations, properties
2. **Geology Data** - Geological markers, hydrocarbon-bearing intervals
3. **Infrastructure Data** - Block information, lease areas
4. **Operations Data** - Well activities, BOP tests, casing operations
5. **Production Data** - Historical production records
6. **Wells Data** - Well information, directional surveys, tubulars

---

### 2. SODIR (Norwegian Petroleum Directorate) Data
**Location:** `data/modules/sodir_zip_data/`
**Size:** 156 MB
**Status:** ✅ Active

#### Content:
- Zipped data files from Norwegian offshore fields
- Exploration and production data
- Well information for Norwegian Continental Shelf

---

### 3. Posters & Visualizations
**Location:** `data/modules/posters/`
**Size:** 135 MB
**Status:** ✅ Active

#### Content:
- Energy field maps and visualizations
- Infographics and presentation materials
- Technical diagrams

---

### 4. LNG Carrier (LNGC) Data
**Location:** `data/modules/lngc/`
**Size:** 43 MB
**Status:** ✅ Active

#### Content:
- LNG carrier vessel specifications
- Transportation and shipping data
- Fleet information

---

### 5. Drilling Rigs Data
**Location:** `data/modules/drilling_rigs/`
**Size:** 15 MB
**Status:** ✅ Active

#### Subdirectories:
```
data/modules/drilling_rigs/
└── offshore/               # Offshore drilling rig information
```

---

### 6. Wind Energy Data
**Location:** `data/modules/wind/`
**Size:** 7.1 MB
**Status:** ✅ Active

#### Content:
- Wind farm data
- Turbine specifications
- Production statistics

---

### 7. Equipment Data
**Location:** `data/modules/equipment/`
**Size:** 300 KB
**Status:** ✅ Active

#### Subdirectories:
```
data/modules/equipment/
└── manifold/               # Manifold equipment specifications
```

---

### 8. Oil Price Data
**Location:** `data/modules/oil_price/`
**Size:** 88 KB
**Status:** ✅ Active

#### Content:
- Historical oil price data
- Market pricing information

---

## 🚨 DUPLICATE DATA ANALYSIS

### Critical Issue: Multiple BSEE Backups

**Problem:** Four backup directories exist with identical or near-identical content:

| Directory | Size | Created | Status |
|-----------|------|---------|--------|
| `bsee.backup` | 369 MB | Unknown | ❌ Duplicate |
| `bsee.backup_20250821_055915` | 369 MB | 2025-08-21 05:59:15 | ❌ Duplicate |
| `bsee.backup_20250821_064214` | 369 MB | 2025-08-21 06:42:14 | ❌ Duplicate |
| `bsee.backup_20250821_064447` | 369 MB | 2025-08-21 06:44:47 | ❌ Duplicate |
| **TOTAL BACKUPS** | **1.476 GB** | - | **🗑️ CAN DELETE** |

### Verification Results:
- All four backup directories appear to be identical
- The `diff` command found no differences between backup directories
- Current active data in `data/modules/bsee/current/` is organized and up-to-date

### Backup Directory Structure (All Identical):
```
bsee.backup*/
├── analysis_data/
│   ├── combined_data_for_analysis/    # 16 CSV files
│   └── financial_analysis/
├── legacy/
│   ├── data_for_analysis/             # 16 CSV files (duplicates)
│   ├── online_raw_well_data/          # 200+ CSV files
│   ├── jack_by_block/                 # Jack field data
│   ├── julia_by_block/                # Julia field data
│   └── various legacy CSV files
├── bin/                                # Binary files
└── zip/                                # Compressed archives
```

---

## 📊 Data Organization Quality Assessment

### ✅ Well-Organized Modules:
1. **BSEE Current** - Clean categorical structure (completions, geology, operations, production, wells)
2. **SODIR** - Compressed archives
3. **Wind** - Single purpose directory
4. **Oil Price** - Lightweight, focused data

### ⚠️ Areas for Improvement:
1. **BSEE Backups** - Multiple redundant copies (CLEANUP NEEDED)
2. **BSEE Legacy** - Large legacy data in backups (should be archived separately if needed)
3. **Empty Directories** - `bsee/raw/` and `bsee/archive/` are empty

---

## 🧹 CLEANUP RECOMMENDATIONS

### Priority 1: Delete Duplicate BSEE Backups (Recovers 1.5 GB)

**Recommended Actions:**

1. **Verify Current Data Integrity**
   ```bash
   # Ensure current data is complete
   ls -lh data/modules/bsee/current/*/*
   ```

2. **Delete Duplicate Backups**
   ```bash
   # Remove all backup directories
   rm -rf data/modules/bsee.backup
   rm -rf data/modules/bsee.backup_20250821_055915
   rm -rf data/modules/bsee.backup_20250821_064214
   rm -rf data/modules/bsee.backup_20250821_064447
   ```

3. **If Legacy Data is Needed**
   Create a single compressed archive:
   ```bash
   # Keep ONE backup if needed
   cd data/modules
   tar -czf bsee_legacy_archive_20250821.tar.gz bsee.backup_20250821_055915/legacy/
   # Then delete all backup directories
   ```

### Priority 2: Remove Empty Directories

```bash
# Remove empty directories
rmdir data/modules/bsee/raw
rmdir data/modules/bsee/analysis_data
```

### Priority 3: Git LFS for Large Files (Optional)

Consider using Git Large File Storage (LFS) for:
- `sodir_zip_data/` (156 MB)
- `posters/` (135 MB)
- `lngc/` (43 MB)

---

## 📁 Cleaned Repository Structure (After Cleanup)

**Expected Size Reduction:** 1.5 GB → ~600 MB (72% reduction)

```
data/
└── modules/
    ├── bsee/                    # 264 MB - BSEE data
    │   ├── current/             # 4.2 MB - Active organized data
    │   ├── bin/
    │   ├── zip/
    │   ├── paleowells/
    │   ├── README.md
    │   └── DATA_DICTIONARY.md
    ├── sodir_zip_data/          # 156 MB - Norwegian data
    ├── posters/                 # 135 MB - Visualizations
    ├── lngc/                    # 43 MB - LNG carriers
    ├── drilling_rigs/           # 15 MB - Rig data
    ├── wind/                    # 7.1 MB - Wind energy
    ├── equipment/               # 300 KB - Equipment specs
    └── oil_price/               # 88 KB - Price data
```

---

## 🔍 Data Quality Notes

### BSEE Data Quality:
- ✅ Well-structured CSV files
- ✅ Categorical organization
- ✅ Data dictionary available
- ✅ Documentation present

### File Format Distribution:
- **CSV files:** ~2,900 files (98%)
- **Excel files:** ~20 files
- **ZIP archives:** ~50 files
- **Documentation:** README.md, DATA_DICTIONARY.md

---

## 🎯 Implementation Steps

### Step 1: Pre-Cleanup Verification
```bash
# Check git status
git status

# Verify current BSEE data completeness
find data/modules/bsee/current -type f | wc -l  # Should be 16 files

# Optional: Create final backup before cleanup
tar -czf worldenergydata_full_backup_$(date +%Y%m%d).tar.gz data/
```

### Step 2: Execute Cleanup
```bash
# Delete duplicate backups
rm -rf data/modules/bsee.backup*

# Remove empty directories
find data/modules/bsee -type d -empty -delete

# Update .gitignore to prevent future backup commits
echo "data/modules/*.backup*" >> .gitignore
```

### Step 3: Post-Cleanup Verification
```bash
# Check new size
du -sh data/

# Verify BSEE data integrity
ls -lh data/modules/bsee/current/*/*

# Git status and commit
git add .
git commit -m "chore: remove duplicate BSEE backup directories (1.5GB cleanup)"
```

---

## 📋 Data Access Patterns

Based on the code structure, data is accessed via:

1. **Engine Pattern:** `src/worldenergydata/engine.py`
2. **Module-Specific Loaders:**
   - `src/worldenergydata/modules/bsee/analysis/bsee_analysis.py`
   - `src/worldenergydata/modules/bsee/analysis/financial/data_loader.py`

3. **Expected Data Paths:**
   - Current data: `data/modules/bsee/current/`
   - Historical: `data/modules/bsee/paleowells/`
   - Analysis outputs: User-specified in YAML configs

---

## ✅ Cleanup Safety Checklist

Before executing cleanup:

- [ ] Verify current BSEE data is complete (16 files in `current/`)
- [ ] Confirm no code references backup directories
- [ ] Check if any analysis scripts use legacy data
- [ ] Create full backup if needed (optional)
- [ ] Test data loading after cleanup
- [ ] Update documentation

---

## 📞 Questions for Stakeholders

1. **Legacy Data:** Is there any value in preserving the legacy data from backups?
2. **Historical Analysis:** Are the backup timestamps (Aug 21, 2025) significant?
3. **Raw Data Folder:** Why is `bsee/raw/` empty? Should it be populated?
4. **Archive Strategy:** What's the long-term archival strategy for historical data?

---

## 🎉 Expected Benefits After Cleanup

1. **Storage:** Reduce repository size by 72% (1.5 GB → 600 MB)
2. **Performance:** Faster git operations and cloning
3. **Clarity:** Cleaner directory structure
4. **Maintenance:** Easier to understand data organization
5. **Cost:** Reduced storage costs for hosting/backup

---

**Report Generated By:** Claude Code Data Inventory Analysis
**Last Updated:** 2025-10-02
**Next Review:** After cleanup execution
