# Spec File Locations

This document lists all files created for this spec to help team members navigate the documentation.

> Spec: Drilling Days Comparison Test
> Created: 2025-07-29
> Last Updated: 2025-07-29

## Core Documentation

### Main Spec File
- **Spec Requirements:** `spec.md`
  - Contains: User prompt, overview, user stories, scope, and deliverables
  - Path: `.agent-os/specs/2025-07-29-drilling-days-comparison/spec.md`

### Task Management
- **Implementation Tasks:** `tasks.md`
  - Contains: Breakdown of implementation tasks with TDD approach
  - Path: `.agent-os/specs/2025-07-29-drilling-days-comparison/tasks.md`

## Sub-Specifications

### Technical Details
- **Technical Specification:** `sub-specs/technical-spec.md`
  - Contains: Technical requirements, approach options, dependencies
  - Path: `.agent-os/specs/2025-07-29-drilling-days-comparison/sub-specs/technical-spec.md`

### Testing Strategy
- **Tests Specification:** `sub-specs/tests.md`
  - Contains: Test coverage, unit tests, integration tests, mocking requirements
  - Path: `.agent-os/specs/2025-07-29-drilling-days-comparison/sub-specs/tests.md`

## Quick Navigation

```
.agent-os/specs/2025-07-29-drilling-days-comparison/
├── spec.md                          # Main requirements document
├── tasks.md                         # Implementation task breakdown
├── spec_file_locations.md           # This file - navigation guide
└── sub-specs/
    ├── technical-spec.md            # Technical implementation details
    └── tests.md                     # Test coverage specifications

Generated Implementation Files:
tests/modules/bsee/analysis/
├── drilling_days_comparison_test.py              # Main test file
├── drilling_days_comparison_config.yml           # Test configuration
└── output/                                       # Test output files

src/worldenergydata/modules/bsee/analysis/
└── comparison/                                   # Comparison framework
    ├── data_loader.py                           # Data loading classes
    ├── analyzer.py                              # Comparison analysis engine
    └── report_generator.py                      # Markdown report generation

output/drilling_days_comparison/
└── comparison_report.md                         # Generated comparison report
```

## Generated Files

### Test Files
- **Main Test File:** `tests/modules/bsee/analysis/drilling_days_comparison_test.py`
  - Contains: Primary test implementation for drilling days comparison functionality
  - Path: `tests/modules/bsee/analysis/drilling_days_comparison_test.py`

### Implementation Scripts
- **Data Loader:** `src/worldenergydata/modules/bsee/analysis/comparison/data_loader.py`
  - Contains: ComparisonDataLoader class for loading Excel and CSV outputs
  - Path: `src/worldenergydata/modules/bsee/analysis/comparison/data_loader.py`

- **Comparison Analyzer:** `src/worldenergydata/modules/bsee/analysis/comparison/analyzer.py`
  - Contains: ComparisonAnalyzer class for data comparison and analysis
  - Path: `src/worldenergydata/modules/bsee/analysis/comparison/analyzer.py`

- **Report Generator:** `src/worldenergydata/modules/bsee/analysis/comparison/report_generator.py`
  - Contains: MarkdownReportGenerator class for creating comparison reports
  - Path: `src/worldenergydata/modules/bsee/analysis/comparison/report_generator.py`

### Configuration Files
- **Test Configuration:** `tests/modules/bsee/analysis/drilling_days_comparison_config.yml`
  - Contains: Test parameters and configuration settings for comparison tests
  - Path: `tests/modules/bsee/analysis/drilling_days_comparison_config.yml`

### Output Files
- **Comparison Report:** `output/drilling_days_comparison/comparison_report.md`
  - Contains: Generated markdown comparison table with analysis results
  - Path: `output/drilling_days_comparison/comparison_report.md`

- **Test Data Output:** `tests/modules/bsee/analysis/output/comparison_test_results.md`
  - Contains: Test-generated comparison results for validation
  - Path: `tests/modules/bsee/analysis/output/comparison_test_results.md`

## Getting Started

1. **Start Here:** Read `spec.md` for complete requirements and context
2. **Implementation:** Review `tasks.md` for step-by-step development plan
3. **Technical Details:** Check `sub-specs/technical-spec.md` for implementation approach
4. **Testing:** Reference `sub-specs/tests.md` for comprehensive test strategy
5. **Generated Files:** Check the Generated Files section above for actual implementation and output file locations