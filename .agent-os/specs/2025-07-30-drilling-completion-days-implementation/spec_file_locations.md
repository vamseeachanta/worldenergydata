# Spec File Locations

This document lists all files created for this spec to help team members navigate the documentation.

> Spec: Drilling and Completion Days Integration
> Created: 2025-07-30
> Last Updated: 2025-07-30

## Core Documentation

## Generated Files

### Test Files
- **Main Test File:** `tests/modules/bsee/analysis/drilling_completion_days_test.py`
  - Contains: Primary test implementation for the framework integration
  - Path: `tests/modules/bsee/analysis/drilling_completion_days_test.py`

### Configuration Files
- **YAML Configuration:** `tests/modules/bsee/analysis/drilling_completion_days_config.yml`
  - Contains: Configuration for binary file paths, basename settings, and analysis parameters
  - Path: `tests/modules/bsee/analysis/drilling_completion_days_config.yml`
  
### Implementation Scripts
- **Framework Wrapper Class:** `src/worldenergydata/modules/bsee/analysis/custom_scripts/Roy/july/drilling_and_completion_days.py`
  - Contains: DrillingCompletionDaysFramework wrapper class for engine integration
  - Path: `src/worldenergydata/modules/bsee/analysis/custom_scripts/Roy/july/drilling_and_completion_days.py`


### Enhanced Files
- **Custom Router:** `src/worldenergydata/modules/bsee/custom_router.py`
  - Contains: Enhanced routing logic for drilling completion days analysis
  - Path: `src/worldenergydata/modules/bsee/custom_router.py`

### Output Files
- **Excel Analysis Report:** `tests\modules\bsee\analysis\results\drilling_and_completion_days_by_api_2025-07-31.xlsx`
  - Contains: Drilling and completion days analysis by API well number
  - Path: Configured output directory with standardized filename

## Getting Started

1. **Start Here:** Read `spec.md` for complete requirements and context
2. **Implementation:** Review `tasks.md` for step-by-step development plan  
3. **Technical Details:** Check `sub-specs/technical-spec.md` for implementation approach
4. **Testing:** Reference `sub-specs/tests.md` for comprehensive test strategy
5. **Generated Files:** Check the Generated Files section above for actual implementation and output file locations