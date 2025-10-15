# FDAS Quick Reference Card
**One-Page Summary for Team Members**

## What Is FDAS?

Financial analysis system for deepwater field development:
- **NPV/MIRR calculations** (Excel-compatible)
- **Monthly cashflow modeling**
- **Development economics** (CAPEX, OPEX, revenue)

## Location
📂 `/home/vamsee/Downloads/FDAS_V30/`

## Core Files (4 scripts, 1,749 lines)

| File | Purpose | Key Functions |
|------|---------|---------------|
| `generate_financial_summary.py` | Financial engine | NPV, MIRR, cashflow |
| `build_multi_year_lease_matrix1.py` | Production data | Monthly pivots |
| `ogora_to_chronological.py` | Chronological analysis | Long-form production |
| `extract_drilling_completion_days.py` | D&C timeline | Activity detection |

## Integration Plan: 6 Weeks

```
Week 1-2: Core Module + NPV/MIRR port
Week 3-4: BSEE Adapter + Production
Week 5:   Cashflow Engine
Week 6:   Testing + Validation
```

## BSEE Changes Required

### Must Have ✅
1. **Add `DEV_SYSTEM` column** → `well_data.csv`
   - Values: `dry`, `subsea15`, `subsea20`
   - Logic: Water depth classification

2. **Create `lease_mapping.csv`**
   - Columns: LEASE_NUMBER, LEASE_NAME, DEV_NAME, DEV_SYSTEM

3. **Enhance `production.csv`**
   - Add: `DEV_NAME`, `LEASE_NAME`
   - Alias: `MONTHLY_OIL_VOLUME`, `MONTHLY_WATER_VOLUME`

### Nice to Have ⭐
4. **Activity classification** → `well_activity_remarks.csv`
5. **Assumptions file** → `default_assumptions.xlsx`

## Key Financial Formulas

### MIRR (Excel-compatible)
```python
# Monthly MIRR
fv_positive = Σ(positive_cf × (1+r)^(n-t))
pv_negative = Σ(negative_cf / (1+r)^t)
mirr_monthly = (fv_positive / -pv_negative)^(1/n) - 1

# Annualize
mirr_annual = (1 + mirr_monthly)^12 - 1
```

### NPV
```python
npv = Σ(cashflow[t] / (1+r)^t)
```

## Development System Classification

| Water Depth | Dev System | Example |
|-------------|-----------|---------|
| < 500 ft | `dry` | Platform |
| 500-6000 ft | `subsea15` | Julia, Jack |
| > 6000 ft | `subsea20` | Anchor |

## Example Output

```
Project: Anchor
NPV: $2.5B
MIRR: 18.5% (annual)
Payback: 4.2 years
Total Oil: 250 MMbbls
CAPEX: $4.5B
OPEX: $1.2B
Revenue: $18.7B
```

## Validation Criteria

✅ NPV matches golden baseline (±1%)
✅ MIRR matches golden baseline (±0.1%)
✅ Test coverage > 90%
✅ Single field analysis < 10 seconds

## Field Examples

| Field | Complex ID | Lease | Water Depth | Dev System |
|-------|-----------|-------|-------------|------------|
| Anchor | 603214001 | G09868 | 7,500 ft | subsea20 |
| Julia | 603214011 | G09964 | 7,000 ft | subsea15 |
| Jack | 603214096 | G32306 | 7,000 ft | subsea15 |
| St. Malo | 603214097 | G32635 | 6,800 ft | subsea15 |

## Input Files

### Required
- `leases.xlsx` - Lease mapping
- `lease_assumptions.xlsx` - Dev system parameters
- `chronological_lease_analysis.xlsx` - Monthly production
- `drilling_and_completion_days.xlsx` - D&C timeline
- `wti_monthly.xlsx` - Price deck

### Optional
- OGORA files (historical data)
- WAR files (well activity reports)

## Assumptions Parameters

| Parameter | Dry | Subsea15 | Subsea20 |
|-----------|-----|----------|----------|
| Host CAPEX (MM) | 0 | 300 | 450 |
| SURF per well (MM) | 0 | 8 | 12 |
| MODU rate (MM/day) | 0.6 | 0.8 | 1.0 |
| Royalty rate | 12.5% | 18.8% | 18.8% |
| Variable OPEX ($/bbl) | 8 | 12 | 15 |
| Fixed OPEX (MM/yr) | 10 | 25 | 40 |
| Discount rate | 10% | 10% | 10% |

## Key Code Snippets

### Load Production Data
```python
from worldenergydata.modules.fdas import ProductionDataLoader

loader = ProductionDataLoader()
prod = loader.load_bsee_production('production.csv')
```

### Run Analysis
```python
from worldenergydata.modules.fdas import FDASAnalyzer

analyzer = FDASAnalyzer(config='config.yaml')
results = analyzer.analyze_field('Anchor')
```

### Generate Report
```python
results.to_excel('anchor_financial_summary.xlsx')
```

## Testing Commands

```bash
# Run unit tests
pytest tests/modules/fdas/test_financial.py

# Run integration tests
pytest tests/integration/fdas/test_bsee_integration.py

# Validate against golden baseline
pytest tests/validation/test_golden_baseline.py

# Run all FDAS tests
pytest tests/ -k fdas
```

## Common Issues & Solutions

### Issue: NPV mismatch with Excel
**Solution:** Ensure cashflows trimmed to first/last non-zero

### Issue: Missing DEV_NAME
**Solution:** Check lease_mapping.csv has all leases

### Issue: Completion days = 0
**Solution:** Verify activity remarks have completion keywords

### Issue: MIRR returns NaN
**Solution:** Ensure both positive and negative cashflows exist

## Module Structure

```
src/worldenergydata/modules/fdas/
├── core/
│   ├── financial.py      # NPV/MIRR engine
│   ├── cashflow.py       # Monthly modeling
│   └── assumptions.py    # Config management
├── data/
│   ├── production.py     # Production processing
│   ├── drilling.py       # D&C timeline
│   └── pricing.py        # Price deck
├── adapters/
│   ├── bsee.py          # BSEE → FDAS
│   └── ogora.py         # OGORA → FDAS
└── reports/
    └── excel.py         # Report generation
```

## Performance Targets

| Metric | Target | Current (V30) |
|--------|--------|---------------|
| Single field | < 10s | ~30s |
| Memory | < 500MB | ~500MB |
| 10-year production | < 15s | ~45s |
| Test coverage | > 90% | 0% |

## Risk Matrix

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| BSEE incompatibility | 🔴 High | 🟡 Medium | Comprehensive adapter |
| Calculation errors | 🔴 High | 🟢 Low | Golden baseline validation |
| Performance | 🟡 Medium | 🟢 Low | Profiling + optimization |
| Missing data | 🟡 Medium | 🟡 Medium | Graceful degradation |

## Success Metrics

✅ **Functional**
- All major fields analyzed without errors
- NPV/MIRR within 1% of golden baseline

✅ **Quality**
- 90%+ test coverage
- Full type hints
- Comprehensive docs

✅ **Performance**
- Single field < 10 seconds
- Memory < 500MB

## Contact & Resources

**Technical Lead:** TBD
**Data Team:** TBD

**Documentation:**
- Implementation Plan: `fdas-implementation-plan.md`
- BSEE Integration: `bsee-fdas-integration-summary.md`
- Code Comparison: `fdas-code-comparison.md`
- Executive Summary: `fdas-executive-summary.md`

**Source Code:** `/home/vamsee/Downloads/FDAS_V30/`

---

**Last Updated:** 2025-10-03
**Version:** 1.0
**Status:** Ready for Review

