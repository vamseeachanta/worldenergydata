# Spec File Locations

This document lists all files created for this spec to help team members navigate the documentation.

> Spec: Drilling and Completion Days Integration
> Created: 2025-07-30
> Last Updated: 2025-07-30

## Core Documentation

### Main Spec File
- **Spec Requirements:** `spec.md`
  - Contains: User prompt, overview, user stories, scope, and deliverables
  - Path: `.agent-os/specs/2025-07-30-drilling-completion-days-integration/spec.md`

### Task Management
- **Implementation Tasks:** `tasks.md`
  - Contains: Breakdown of implementation tasks with TDD approach
  - Path: `.agent-os/specs/2025-07-30-drilling-completion-days-integration/tasks.md`

## Sub-Specifications

### Technical Details
- **Technical Specification:** `sub-specs/technical-spec.md`
  - Contains: Technical requirements, approach options, dependencies
  - Path: `.agent-os/specs/2025-07-30-drilling-completion-days-integration/sub-specs/technical-spec.md`

### Testing Strategy
- **Tests Specification:** `sub-specs/tests.md`
  - Contains: Test coverage, unit tests, integration tests, mocking requirements
  - Path: `.agent-os/specs/2025-07-30-drilling-completion-days-integration/sub-specs/tests.md`

## Quick Navigation

```
.agent-os/specs/2025-07-30-drilling-completion-days-integration/
├── spec.md                          # Main requirements document
├── tasks.md                         # Implementation task breakdown
├── spec_file_locations.md           # This file - navigation guide
└── sub-specs/
    ├── technical-spec.md            # Technical implementation details
    └── tests.md                     # Test coverage specifications

Generated Implementation Files:
tests/modules/bsee/analysis/
├── drilling_completion_days_test.py         # Main test file
├── drilling_completion_days_config.yml      # Test configuration
└── leases.csv                              # Existing lease data (no changes)

src/worldenergydata/modules/bsee/
├── analysis/
│   └── drilling_completion_days.py         # New framework wrapper class
└── custom_router.py                        # Enhanced with new routing logic

output/drilling_completion_days/
└── drilling_and_completion_days_by_api.xlsx # Generated Excel analysis
```

## Generated Files

### Test Files
- **Main Test File:** `tests/modules/bsee/analysis/drilling_completion_days_test.py`
  - Contains: Primary test implementation for the framework integration
  - Path: `tests/modules/bsee/analysis/drilling_completion_days_test.py`

### Implementation Scripts
- **Framework Wrapper Class:** `src/worldenergydata/modules/bsee/analysis/drilling_completion_days.py`
  - Contains: DrillingCompletionDaysFramework wrapper class for engine integration
  - Path: `src/worldenergydata/modules/bsee/analysis/drilling_completion_days.py`

### Configuration Files
- **YAML Configuration:** `tests/modules/bsee/analysis/drilling_completion_days_config.yml`
  - Contains: Configuration for binary file paths, basename settings, and analysis parameters
  - Path: `tests/modules/bsee/analysis/drilling_completion_days_config.yml`

### Enhanced Files
- **Custom Router:** `src/worldenergydata/modules/bsee/custom_router.py`
  - Contains: Enhanced routing logic for drilling completion days analysis
  - Path: `src/worldenergydata/modules/bsee/custom_router.py`

### Output Files
- **Excel Analysis Report:** `tests\modules\bsee\analysis\results\drilling_and_completion_days_by_api.xlsx`
  - Contains: Drilling and completion days analysis by API well number
  - Path: Configured output directory with standardized filename

## Getting Started

1. **Start Here:** Read `spec.md` for complete requirements and context
2. **Implementation:** Review `tasks.md` for step-by-step development plan  
3. **Technical Details:** Check `sub-specs/technical-spec.md` for implementation approach
4. **Testing:** Reference `sub-specs/tests.md` for comprehensive test strategy
5. **Generated Files:** Check the Generated Files section above for actual implementation and output file locations