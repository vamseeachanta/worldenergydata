# Phase 2 Tier 1 - Test Coverage Expansion Plan

> **Status**: In Progress
> **Date**: 2026-01-14
> **Current Coverage**: 15.97% (13 tests passing)
> **Target Coverage**: 85%
> **Gap**: +69.03 percentage points

## Executive Summary

The worldenergydata project has clean pytest collection (974 tests, 0 errors) but very low test coverage (15.97%). This document provides a prioritized, strategic plan to expand test coverage to 85% by targeting the highest-impact modules with lowest coverage.

**Key Finding**: 4 modules have 0% coverage (517 lines untested), and 42 modules have <25% coverage. Strategic testing of these low-coverage modules will have the highest ROI.

## Coverage Baseline Analysis

### By Coverage Level

| Coverage Range | Module Count | Total Lines | Criticality |
|---|---|---|---|
| 0% coverage | 4 modules | 517 lines | **CRITICAL** |
| <10% coverage | 9 modules | ~1,200 lines | **HIGH** |
| 10-25% coverage | 29 modules | ~4,500 lines | **HIGH** |
| 25-50% coverage | 20 modules | ~2,500 lines | MEDIUM |
| 50%+ coverage | 7 modules | ~1,200 lines | STANDARD |

### Total Codebase

- **Total modules**: 69 unique Python files
- **Total lines**: 8,557 (not counting tests)
- **Currently covered**: 1,640 lines (15.97%)
- **Untested**: 6,917 lines (84.03%)

## Strategic Prioritization

The following prioritization considers:

1. **Criticality to Product**: Core data processing, economic analysis, HSE integration
2. **Coverage Gaps**: Modules with lowest coverage have highest ROI
3. **Complexity**: More complex modules require more thorough tests
4. **Dependencies**: Some modules are prerequisites for others

---

## PRIORITY 1: Critical Validation Framework (0% Coverage)

**Modules**: 4 files, 517 lines
- `validators/data_validator.py` - 123 lines, 0% coverage
- `worldenergydata/validation/base.py` - 142 lines, 0% coverage
- `worldenergydata/validation/schemas.py` - 250 lines, 0% coverage
- `worldenergydata/__main__.py` - 2 lines, 0% coverage

**Criticality**: **CRITICAL** - These modules validate all incoming data before processing

**ROI**: **VERY HIGH** - Small effort (simple functions), large impact (prevents bugs downstream)

**Test Strategy**:
1. Unit tests for each validator class
2. Test valid input acceptance
3. Test invalid input rejection with appropriate error messages
4. Test edge cases (empty, null, boundary values)
5. Integration tests with real BSEE data samples

**Estimated Effort**: 3-4 hours
**Coverage Impact**: +517 lines → +6% coverage

**Files to Create**:
- `tests/unit/test_validators_data_validator.py`
- `tests/unit/test_validation_base.py`
- `tests/unit/test_validation_schemas.py`

---

## PRIORITY 2: HSE Data Integration (8.5-22.4% Coverage)

**Modules**: 6 files, ~450 lines
- `modules/hse/importers/bsee_incidents_importer.py` - 76 lines, 11.8% coverage
- `modules/hse/importers/bsee_penalties_importer.py` - 82 lines, 11.0% coverage
- `modules/hse/importers/bsee_statistics_importer.py` - 106 lines, 8.5% coverage
- `modules/hse/importers/base_importer.py` - 85 lines, 22.4% coverage

**Criticality**: **CRITICAL** - HSE data integration is a key product differentiator

**Product Context**: According to DEC-003, HSE data integration provides unique competitive advantage vs. commercial tools (Aries $15K+/seat, PHDWin $20K+/seat)

**Test Strategy**:
1. Unit tests for each importer class
2. Test incident data parsing (injuries, spills, equipment failures)
3. Test penalty/violation tracking
4. Test statistical aggregation (incident rates by operator/field)
5. Integration tests with real BSEE HSE databases
6. Test safety risk scoring calculations

**Test Fixtures Required**:
- Sample BSEE incident records (CSV format)
- Penalty/violation records
- Statistical data

**Estimated Effort**: 6-8 hours
**Coverage Impact**: +400+ lines → +5% coverage

**Files to Create**:
- `tests/unit/test_hse_incidents_importer.py`
- `tests/unit/test_hse_penalties_importer.py`
- `tests/unit/test_hse_statistics_importer.py`
- `tests/integration/test_hse_integration.py`
- `tests/fixtures/hse_incident_data.csv`
- `tests/fixtures/hse_penalty_data.csv`

---

## PRIORITY 3: Core BSEE Analysis Modules (7.3-13.3% Coverage)

**Modules**: 3 files, ~834 lines
- `modules/bsee/analysis/well_api12.py` - 454 lines, 7.3% coverage
- `modules/bsee/analysis/well_rig_days.py` - 102 lines, 8.8% coverage
- `modules/bsee/analysis/production_api.py` - 278 lines, 13.3% coverage

**Criticality**: **CRITICAL** - Core production analysis functionality

**Test Strategy**:
1. Unit tests for well decline curve calculations
2. Test API production data extraction
3. Test rig days computation
4. Test production forecasting with various well types
5. Integration tests with real GOM well data (Anchor, Julia, Jack, St. Malo fields)
6. Test error handling for missing/corrupted data

**Test Fixtures Required**:
- Real BSEE well production data
- API well information
- Historical decline curves
- Field-specific well data

**Estimated Effort**: 10-12 hours (complex calculations)
**Coverage Impact**: +700+ lines → +8% coverage

**Files to Create**:
- `tests/unit/test_well_api12_analysis.py`
- `tests/unit/test_well_rig_days.py`
- `tests/unit/test_production_api_analysis.py`
- `tests/integration/test_production_analysis_integration.py`
- `tests/fixtures/well_production_data.csv`
- `tests/fixtures/api_well_data.csv`

---

## PRIORITY 4: Data Processing Pipeline (9-11% Coverage)

**Modules**: 6 files, ~1,500 lines
- `modules/bsee/data/enhanced/data_refresh_chunked.py` - 228 lines, 11.0% coverage
- `modules/bsee/data/refresh/data_refresh_enhanced.py` - 218 lines, 10.5% coverage
- `modules/bsee/data/cache/chunk_manager.py` - 331 lines, 10.3% coverage
- `modules/bsee/data/processors/in_memory.py` - 253 lines, 11.5% coverage
- `modules/bsee/reports/comprehensive/data_loader_enhanced.py` - 318 lines, 9.4% coverage
- `modules/bsee/data/_from_zip/production_data.py` - 112 lines, 16.1% coverage

**Criticality**: **HIGH** - Data pipeline is essential for all downstream analysis

**Test Strategy**:
1. Unit tests for data loading from various sources (ZIP, BIN, CSV)
2. Test chunking and cache management
3. Test data refresh and update mechanisms
4. Test in-memory vs. disk-based processing
5. Integration tests with real data files
6. Performance tests for large datasets

**Test Fixtures Required**:
- Sample BSEE ZIP files with production data
- BIN format files
- Large dataset samples for performance testing

**Estimated Effort**: 12-15 hours
**Coverage Impact**: +1,200+ lines → +14% coverage

**Files to Create**:
- `tests/unit/test_data_refresh_chunked.py`
- `tests/unit/test_chunk_manager.py`
- `tests/unit/test_in_memory_processor.py`
- `tests/integration/test_data_pipeline_integration.py`
- `tests/performance/test_data_pipeline_performance.py`

---

## PRIORITY 5: NPV Economic Analysis (12.9% Coverage)

**Modules**: 1 file, 101 lines
- `analysis/lower_tertiary/npv.py` - 101 lines, 12.9% coverage

**Criticality**: **CRITICAL** - Economic evaluation is core product feature

**Test Strategy**:
1. Unit tests for NPV calculations with various discount rates
2. Test production decline curves for economic projections
3. Test cost/revenue scenarios
4. Test sensitivity analysis
5. Compare against industry standard calculations (API RP 2D, SPE PRMS)
6. Test edge cases (no production, flat production, rapid decline)

**Test Fixtures Required**:
- Well production data with economic parameters
- Cost and revenue scenarios
- Known NPV calculation results (from commercial software validation)

**Estimated Effort**: 5-6 hours
**Coverage Impact**: +90+ lines → +1% coverage

**Files to Create**:
- `tests/unit/test_lower_tertiary_npv.py`
- `tests/fixtures/npv_test_scenarios.csv`

---

## PRIORITY 6: Comprehensive Reporting System (9-27% Coverage)

**Modules**: 6 files, ~1,500 lines
- `modules/bsee/reports/comprehensive/templates/compliance_template.py` - 456 lines, 27.9% coverage
- `modules/bsee/reports/comprehensive/controller_enhanced.py` - 249 lines, 29.3% coverage
- `modules/bsee/reports/comprehensive/templates/loaders.py` - 181 lines, 27.1% coverage
- `modules/bsee/reports/comprehensive/aggregators/lease_aggregator_enhanced.py` - 232 lines, 9.1% coverage
- `modules/bsee/reports/comprehensive/aggregators/field_aggregator_enhanced.py` - 164 lines, 11.6% coverage
- `modules/bsee/reports/comprehensive/aggregators/block_aggregator_enhanced.py` - 141 lines, 13.5% coverage

**Criticality**: **HIGH** - Report generation is user-facing feature

**Test Strategy**:
1. Unit tests for each aggregator (lease, field, block)
2. Test template rendering with various data scenarios
3. Test HTML report generation (ensure interactive plots per standards)
4. Test CSV export functionality
5. Integration tests with comprehensive real data
6. Visual regression tests for reports

**Test Fixtures Required**:
- Aggregated lease/field/block data
- Expected report outputs for comparison
- Sample HTML reports

**Estimated Effort**: 10-12 hours
**Coverage Impact**: +900+ lines → +11% coverage

**Files to Create**:
- `tests/unit/test_report_aggregators.py`
- `tests/unit/test_compliance_template.py`
- `tests/integration/test_report_generation.py`
- `tests/fixtures/aggregated_data_samples/`

---

## Test Organization Structure

```
tests/
├── unit/
│   ├── test_validators_data_validator.py
│   ├── test_validation_base.py
│   ├── test_validation_schemas.py
│   ├── test_hse_incidents_importer.py
│   ├── test_hse_penalties_importer.py
│   ├── test_hse_statistics_importer.py
│   ├── test_well_api12_analysis.py
│   ├── test_well_rig_days.py
│   ├── test_production_api_analysis.py
│   ├── test_data_refresh_chunked.py
│   ├── test_chunk_manager.py
│   ├── test_in_memory_processor.py
│   ├── test_lower_tertiary_npv.py
│   └── test_report_aggregators.py
│
├── integration/
│   ├── test_hse_integration.py
│   ├── test_production_analysis_integration.py
│   ├── test_data_pipeline_integration.py
│   └── test_report_generation.py
│
├── performance/
│   └── test_data_pipeline_performance.py
│
├── fixtures/
│   ├── hse_incident_data.csv
│   ├── hse_penalty_data.csv
│   ├── well_production_data.csv
│   ├── api_well_data.csv
│   ├── npv_test_scenarios.csv
│   └── aggregated_data_samples/
│       ├── lease_aggregated.json
│       ├── field_aggregated.json
│       └── block_aggregated.json
│
└── conftest.py  # Already exists with performance tracking
```

---

## Test Data Requirements

### Priority 1: Must-Have Fixtures (needed for all tests)

1. **BSEE Well Data**
   - Well identifier (API12, lease, block)
   - Production data (oil, gas, water)
   - Rig days
   - Directional survey data

2. **HSE Incident Data**
   - Incident type (injury, spill, environmental violation)
   - Severity level
   - Operator name
   - Field/block location
   - Date

3. **Economic Data**
   - Oil/gas prices (historical)
   - Operating costs
   - Capital costs
   - Discount rates

### Priority 2: Optional Fixtures (enhance realism)

1. Real BSEE CSV/ZIP files
2. Historical decline curves
3. Pre-calculated validation reference values

---

## Execution Strategy

### Phase 1: Foundation (Week 1)
- Create test fixture CSV files (all test data needed)
- Create test directory structure
- Write Priority 1 tests (validation framework)
- Expected coverage: 15.97% → 22%

### Phase 2: Core Processing (Week 2)
- Write Priority 2 tests (HSE data integration)
- Write Priority 3 tests (BSEE analysis)
- Expected coverage: 22% → 35%

### Phase 3: Pipeline & Economics (Week 3)
- Write Priority 4 tests (data processing pipeline)
- Write Priority 5 tests (NPV analysis)
- Expected coverage: 35% → 50%

### Phase 4: Reporting (Week 4)
- Write Priority 6 tests (comprehensive reporting)
- Refactor/optimize any fragile tests
- Expected coverage: 50% → 65%

### Phase 5: Coverage Optimization (Week 5)
- Identify remaining coverage gaps
- Add targeted tests for edge cases
- Performance optimization tests
- Expected coverage: 65% → 80%+

---

## Success Metrics

### Coverage Targets by Phase

| Phase | Target | Effort |
|---|---|---|
| Phase 1 (Foundation) | 22% | 4-5 hours |
| Phase 2 (Core Processing) | 35% | 14-16 hours |
| Phase 3 (Pipeline & Economics) | 50% | 17-21 hours |
| Phase 4 (Reporting) | 65% | 10-12 hours |
| Phase 5 (Optimization) | 80%+ | 10-15 hours |

**Total Estimated Effort**: 55-69 hours (~1.5 weeks of full-time work)

### Quality Metrics

- **Test Success Rate**: 100% (no flaky tests)
- **Coverage Types**: Line coverage, branch coverage, function coverage
- **Performance**: Test suite completes in <5 minutes
- **Documentation**: Every test file has clear docstrings

---

## Risk Mitigation

### Risk 1: Missing Test Fixtures/Data
**Mitigation**: Create synthetic test data matching BSEE CSV schemas before writing tests

### Risk 2: Complex Calculations Hard to Test
**Mitigation**: Compare against known reference values from industry standards (API RP 2D, PHDWin output)

### Risk 3: Integration Tests Too Slow
**Mitigation**: Use small sample datasets, mock external APIs, run integration tests separately

### Risk 4: Flaky Tests from Timing/Randomness
**Mitigation**: Use deterministic test data, set explicit random seeds, mock time-dependent functions

---

## Dependencies & Prerequisites

- [x] pytest collection clean (974 tests, 0 errors)
- [x] Coverage baseline established (15.97%)
- [x] conftest.py with performance tracking configured
- [ ] Test fixture CSV files created
- [ ] Test directory structure established
- [ ] Reference values for validation tests identified

---

## Next Steps

1. **Create Test Fixtures** (Priority 1)
   - Design BSEE CSV schema matching actual files
   - Generate sample CSV files for each module type
   - Validate fixture data matches module requirements

2. **Implement Priority 1 Tests** (Validation Framework)
   - Create tests for data_validator.py
   - Create tests for validation/base.py and schemas.py
   - Run and verify 100% coverage for Priority 1

3. **Iterate Through Priorities**
   - Follow Phase 1-5 execution strategy
   - Run coverage after each priority group
   - Document any blocked tests or issues

4. **Monitor Progress**
   - Track coverage percentage weekly
   - Identify emerging patterns in untested code
   - Adjust priorities based on coverage ROI

---

## References

- **Product Mission**: `../.agent-os/product/mission.md`
- **HSE Integration Decision**: `../.agent-os/product/decisions.md` (DEC-003)
- **Technical Standards**: `../.agent-os/product/tech-stack.md`
- **Testing Standards**: `../docs/modules/standards/TESTING_FRAMEWORK_STANDARDS.md`

---

**Document Version**: 1.0.0
**Last Updated**: 2026-01-14
**Created By**: Claude Code Agent (Continuation Session)
**Status**: Ready for Implementation
