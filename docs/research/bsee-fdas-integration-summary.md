# BSEE → FDAS Integration Summary
**Quick Reference for Data Changes**

## Overview

Roy's FDAS code requires specific data structures. This document outlines the minimal changes needed to accommodate FDAS integration while preserving existing BSEE data integrity.

## Required BSEE File Changes

### 1. Add Development System Classification

**File:** `data/modules/bsee/current/wells/well_data.csv`

**New Column:** `DEV_SYSTEM`

**Values:**
- `dry` - Water depth < 500 ft
- `subsea15` - Water depth 500-6000 ft
- `subsea20` - Water depth > 6000 ft
- `unknown` - No water depth data

**Implementation:**
```python
# Add to well_data processing pipeline
def classify_dev_system(water_depth):
    if pd.isna(water_depth):
        return 'unknown'
    if water_depth < 500:
        return 'dry'
    elif water_depth <= 6000:
        return 'subsea15'
    else:
        return 'subsea20'
```

**Impact:** Low - Additive change, no existing columns modified

---

### 2. Create Lease Mapping File

**New File:** `data/modules/bsee/current/leases/lease_mapping.csv`

**Required Columns:**
```csv
LEASE_NUMBER,LEASE_NAME,DEV_NAME,DEV_SYSTEM,WATER_DEPTH
G09868,Mississippi Canyon 941,Anchor,subsea20,7500
G09964,Green Canyon 19,Julia,subsea15,7000
G32306,Walker Ridge 758,Jack,subsea15,7000
G32635,Walker Ridge 678,St. Malo,subsea15,6800
```

**Source:** Can be auto-generated from:
- `well_data.csv` (API → LEASE_NUMBER)
- `all_bsee_blocks.csv` (LEASE_NUMBER → LEASE_NAME)
- Complex ID mapping (DEV_NAME)

**Implementation:**
```python
# Pseudo-code for generation
lease_mapping = (
    well_data
    .merge(blocks, on='LEASE_NUMBER')
    .merge(complex_mapping, on='COMPLEX_ID')
    .groupby('LEASE_NUMBER')
    .agg({
        'LEASE_NAME': 'first',
        'DEV_NAME': 'first',
        'WATER_DEPTH': 'max'
    })
)
lease_mapping['DEV_SYSTEM'] = lease_mapping['WATER_DEPTH'].apply(classify_dev_system)
```

**Impact:** Low - New file, no dependencies

---

### 3. Enhance Production Data

**File:** `data/modules/bsee/current/production/production.csv`

**Changes Needed:**

| Current Column | FDAS Equivalent | Action |
|----------------|-----------------|--------|
| `OIL_PROD` | `MONTHLY_OIL_VOLUME` | Rename or add alias |
| `WATER_PROD` | `MONTHLY_WATER_VOLUME` | Rename or add alias |
| (missing) | `DEV_NAME` | Add via lease mapping join |
| (missing) | `LEASE_NAME` | Add via lease mapping join |

**Implementation:**
```python
# Add DEV_NAME and LEASE_NAME to production data
production = pd.read_csv('production.csv')
lease_map = pd.read_csv('lease_mapping.csv')

production = production.merge(
    lease_map[['LEASE_NUMBER', 'LEASE_NAME', 'DEV_NAME']],
    on='LEASE_NUMBER',
    how='left'
)

# Add column aliases
production['MONTHLY_OIL_VOLUME'] = production['OIL_PROD']
production['MONTHLY_WATER_VOLUME'] = production['WATER_PROD']
```

**Impact:** Medium - Requires pipeline update, but backwards compatible

---

### 4. Completion Activity Detection

**File:** `data/modules/bsee/current/operations/well_activity_remarks.csv`

**Changes Needed:**

**Add Column:** `ACTIVITY_TYPE` (optional, improves performance)

**Values:**
- `drilling` - Drilling-related remark
- `completion` - Completion activity detected
- `testing` - Well testing or production
- `other` - Generic remark

**Completion Keywords to Detect:**
```python
COMPLETION_KEYWORDS = [
    'log', 'logging', 'core', 'coring', 'rft', 'mdt',
    'run completion', 'install completion', 'frac', 'perforate', 'perf',
    'test', 'well test', 'flow test', 'cleanup', 'pack', 'packer',
    'acid', 'stimulation', 'liner hanger', 'toe'
]
```

**Mud Weight Extraction:**
```python
# Extract from remarks: "15.2 ppg mud" → 15.2
import re

def extract_mud_weight(remark_text):
    pattern = r'(\d{1,2}(?:\.\d+)?)\s*ppg'
    matches = re.findall(pattern, str(remark_text), re.IGNORECASE)
    return max(float(m) for m in matches) if matches else None
```

**Impact:** Low - Optional enhancement, existing data unchanged

---

### 5. Create Financial Assumptions File

**New File:** `data/modules/fdas/config/default_assumptions.xlsx`

**Required Structure:**

Sheet 1: Development System Assumptions
```
DEV_SYSTEM | DRY | SUBSEA15 | SUBSEA20
-----------|-----|----------|----------
HOST_CAPEX_MM | 0 | 300 | 450
SURF_PER_WELL_MM | 0 | 8 | 12
MODU_LOADED_DAYRATE_MM | 0.6 | 0.8 | 1.0
DRY_TREE_RIG_RATE_MM | 0.5 | 0.5 | 0.5
ROYALTY_RATE | 0.125 | 0.188 | 0.188
VARIABLE_OPEX_$/BBL | 8 | 12 | 15
FIXED_OPEX_MM_PER_YEAR | 10 | 25 | 40
DISCOUNT_RATE_ANNUAL | 0.10 | 0.10 | 0.10
WTI_BASE_$/BBL | 75 | 75 | 75
INJECTORS_PER_PRODUCER | 0.2 | 0.2 | 0.2
HOST_PREFO_MONTHS | 0 | 12 | 18
BOOSTER_PUMP_15K_MM | 0 | 30 | 0
BOOSTER_PUMP_20K_MM | 0 | 0 | 45
BOOSTER_PUMP_TRIGGER_PRODUCERS | 99 | 8 | 6
WATER_INJECTION_PUMP_MM | 0 | 15 | 20
WATER_INJECTION_TRIGGER_PRODUCERS | 99 | 10 | 8
WATER_INJECTION_FACILITY_COST_MM | 0 | 25 | 35
DRY_WELL_SYSTEM_PER_PRODUCER_USD | 1000000 | 0 | 0
```

**Source:** Port from FDAS `lease_assumptions.xlsx`

**Impact:** None - New file for FDAS module only

---

## Data Mapping Reference

### BSEE Field → FDAS Input Mapping

| FDAS Input File | BSEE Source | Transformation |
|----------------|-------------|----------------|
| `leases.xlsx` | `lease_mapping.csv` + `well_data.csv` | Aggregate by lease |
| `chronological_lease_analysis.xlsx` | `production.csv` | Add DEV_NAME, LEASE_NAME columns |
| `drilling_and_completion_days.xlsx` | `well_activity_summary.csv` + `well_activity_remarks.csv` | Calculate D&C timeline |
| `wti_monthly.xlsx` | External price deck | No BSEE source |
| `lease_assumptions.xlsx` | `default_assumptions.xlsx` | User configuration |

---

## Migration Checklist

### Phase 1: Additive Changes (Week 1)
- [ ] Add `DEV_SYSTEM` column to `well_data.csv`
- [ ] Create `lease_mapping.csv` file
- [ ] Create `default_assumptions.xlsx` template

### Phase 2: Production Enhancement (Week 2)
- [ ] Add `DEV_NAME` to `production.csv`
- [ ] Add `LEASE_NAME` to `production.csv`
- [ ] Create column aliases (`MONTHLY_OIL_VOLUME`, etc.)

### Phase 3: Completion Detection (Week 2-3)
- [ ] Add `ACTIVITY_TYPE` to `well_activity_remarks.csv`
- [ ] Implement keyword-based classification
- [ ] Add mud weight extraction

### Phase 4: Validation (Week 3-4)
- [ ] Test FDAS module with BSEE data
- [ ] Compare against golden baseline
- [ ] Document discrepancies

---

## Backward Compatibility

**All changes are backward compatible:**

1. **Additive columns** - Existing code ignores new columns
2. **New files** - Only used by FDAS module
3. **Column aliases** - Original columns preserved
4. **Optional enhancements** - FDAS works without them

**No breaking changes to existing BSEE consumers**

---

## Example: Anchor Field Data Flow

```
BSEE Input Files:
├── well_data.csv
│   └── API 608054011700, LEASE G09868, WATER_DEPTH 7500
│       → DEV_SYSTEM = 'subsea20' ✓
│
├── lease_mapping.csv (generated)
│   └── G09868 → 'Anchor', 'subsea20' ✓
│
├── production.csv
│   └── API 608054011700, MONTH 2024-01, OIL_PROD 50000
│       + DEV_NAME = 'Anchor' ✓
│       + LEASE_NAME = 'Mississippi Canyon 941' ✓
│
├── well_activity_summary.csv
│   └── API 608054011700, SPUD_DATE 2023-05-01, TD_DATE 2023-08-15
│       → DRILLING_DAYS = 106 ✓
│
└── well_activity_remarks.csv
    └── API 608054011700, REMARK "Ran 13-3/8\" casing, 16.5 ppg mud"
        → ACTIVITY_TYPE = 'drilling' ✓
        → MAX_MUD_WEIGHT = 16.5 ppg ✓

FDAS Output:
└── financial_project_summary.xlsx
    └── Anchor: NPV=$2.5B, MIRR=18.5%, IRR=22.3%
```

---

## Performance Considerations

**Storage Impact:**
- New columns: ~1MB per 100K wells
- Lease mapping file: ~100KB
- Assumptions file: ~50KB

**Total Additional Storage:** < 5MB

**Processing Impact:**
- Development system classification: +0.1s per 100K wells
- Lease mapping join: +0.5s per 1M production records
- Completion detection: +2s per 100K remarks

**Total Additional Processing:** < 5 seconds for typical dataset

---

## Questions & Troubleshooting

### Q: What if WATER_DEPTH is missing?
A: Use `DEV_SYSTEM = 'unknown'` and require manual classification or default to `subsea15` assumptions.

### Q: How to handle multiple leases per API?
A: Use primary lease (first alphabetically) or lease with most production.

### Q: Missing completion remarks?
A: Fall back to TD_DATE + estimated completion days (30-90 days based on DEV_SYSTEM).

### Q: WTI price deck source?
A: User-provided or use EIA historical data with configurable price deck.

---

**For detailed implementation, see:** `docs/research/fdas-implementation-plan.md`
