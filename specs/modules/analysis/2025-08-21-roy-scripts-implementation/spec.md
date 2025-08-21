# Spec Requirements Document

> Module: bsee/analysis
> Spec: Roy Scripts Implementation
> Created: 2025-08-21
> Status: Planning
> Type: Enhanced

## Module Context

This specification is part of the **bsee/analysis** module within the WorldEnergyData framework. It extends the existing BSEE analysis capabilities by providing enhanced, class-based implementations of critical analysis scripts with comprehensive testing and validation.

### Module Dependencies
- `worldenergydata.modules.bsee.custom_router`
- `worldenergydata.modules.bsee.analysis.custom_scripts`
- Binary WAR data files in `data/modules/bsee/bin/war/`
- OGORA production files in `data/modules/bsee/zip/historical_production_yearly/`

## User Prompt

> This spec was initiated based on the following user request:

```
Implement tests for three scripts from 'docs\modules\bsee\data\SME_Roy_attachments\2025-08-20' 
and verify results with reference results from same folder.

1. Enhanced drilling & completion days analysis with binary file support
2. Multi-year lease matrix generation from OGORA files  
3. Comprehensive financial analysis with NPV/MIRR calculations

All implementations must use '_enhanced' suffix and integrate with custom_router.py
```

## Overview

Transform three critical BSEE analysis scripts into a modular, class-based architecture with enhanced testing capabilities. The implementation provides binary file processing for improved performance, comprehensive validation against reference outputs, and seamless integration with the existing WorldEnergyData framework through the custom router pattern.

## User Stories

### Story 1: Enhanced Drilling Analysis Workflow

**As a** petroleum engineer analyzing well performance  
**I want to** process drilling and completion data using optimized binary files  
**So that** I can generate accurate drilling timelines 60% faster than text processing

**Acceptance Criteria:**
- Binary WAR files load successfully using pickle
- Drilling days calculation matches reference within 0.1%
- Completion segmentation handles gaps correctly
- Output Excel structure matches reference format
- Processing time < 30 seconds for 100 wells

### Story 2: Production Matrix Generation

**As a** production analyst reviewing field performance  
**I want to** generate multi-year production matrices from OGORA files  
**So that** I can analyze production trends across multiple leases and time periods

**Acceptance Criteria:**
- OGORA zip files process without extraction to temp
- BBL/day calculations aggregate correctly by month
- Sheet names match lease groupings
- Column headers follow YYYY-MM format
- All reference leases appear in output

### Story 3: Financial Analysis Integration

**As a** financial analyst evaluating project economics  
**I want to** calculate comprehensive financial metrics using integrated data  
**So that** I can make informed investment decisions with validated NPV/MIRR

**Acceptance Criteria:**
- NPV calculations match reference within $1000
- MIRR calculations use correct monthly rates
- Tax calculations apply corporate rate correctly
- All summary sheets generate properly
- Executive summary formatting preserved

## Module Components

### Core Classes

#### 1. ExtractDrillingCompletionEnhanced
- **Location**: `custom_scripts/Roy/august/extract_drilling_and_completion_days_enhanced.py`
- **Purpose**: Binary-optimized drilling and completion analysis
- **Integration**: Routes through `drilling_completion_enhanced` flag

#### 2. BuildMonthMatrixEnhanced  
- **Location**: `custom_scripts/Roy/august/build_month_matrix_by_lease_enhanced.py`
- **Purpose**: OGORA-based production matrix generation
- **Integration**: Routes through `month_matrix_enhanced` flag

#### 3. BuildDevelopmentFinancialsEnhanced
- **Location**: `custom_scripts/Roy/august/build_development_financials_enhanced.py`
- **Purpose**: Comprehensive financial analysis and reporting
- **Integration**: Routes through `financials_enhanced` flag

### Configuration Structure

```yaml
# Module-specific configuration
meta:
  library: worldenergydata
  module: bsee/analysis
  feature: enhanced_testing
  
basename: bsee_custom

# Enhanced routing flags
drilling_completion_enhanced:
  flag: true
  filepath:
    leases: tests/modules/bsee/analysis/leases_enhanced.xlsx
    war_files:
      main: data/modules/bsee/bin/war/mv_war_main.bin
      boreholes: data/modules/bsee/bin/war/mv_war_boreholes_view.bin
    output: results/drilling_and_completion_days_by_api_enhanced.xlsx
```

## Spec Scope

### In Scope
1. **Class-Based Refactoring** - Convert all three scripts to modular classes
2. **Binary File Processing** - Implement pickle-based WAR file reading
3. **Router Integration** - Extend custom_router with enhanced flags
4. **Automated Validation** - Compare outputs with reference data
5. **Performance Optimization** - Achieve 60%+ speed improvement
6. **Comprehensive Testing** - Unit, integration, and end-to-end tests

### Out of Scope
- Core algorithm modifications
- New calculation methodologies  
- Database integration
- Web API development
- Real-time data streaming
- GUI implementation

## Expected Deliverables

### Code Deliverables
1. Three enhanced analysis classes with full documentation
2. Extended custom_router.py with new routing conditions
3. Enhanced configuration files for each analysis type
4. Comprehensive test suite with 80%+ coverage

### Validation Deliverables
1. Output files matching reference row counts exactly
2. First 5 rows validated against reference data
3. Financial calculations within tolerance limits
4. Performance benchmarks documented

### Documentation Deliverables
1. API documentation for all public methods
2. Configuration parameter descriptions
3. Test execution reports
4. Implementation guide

## Success Criteria

### Functional Criteria
- All three scripts execute without errors
- Outputs match reference data structure
- Router integration works seamlessly
- Tests pass consistently

### Performance Criteria
- Drilling analysis: < 30 seconds
- Matrix generation: < 60 seconds  
- Financial analysis: < 120 seconds
- Memory usage: < 2GB peak

### Quality Criteria
- Code coverage: > 80%
- Zero critical bugs
- Clean code with proper error handling
- Comprehensive logging

## Spec Documentation

- Prompt Summary: @specs/modules/analysis/2025-08-21-enhanced-bsee-testing/prompt_summary.md
- Executive Summary: @specs/modules/analysis/2025-08-21-enhanced-bsee-testing/executive_summary.md
- Tasks: @specs/modules/analysis/2025-08-21-enhanced-bsee-testing/tasks.md
- Technical Specification: @specs/modules/analysis/2025-08-21-enhanced-bsee-testing/sub-specs/technical-spec.md
- API Specification: @specs/modules/analysis/2025-08-21-enhanced-bsee-testing/sub-specs/api-spec.md
- Database Schema: N/A (file-based processing)
- Tests Specification: @specs/modules/analysis/2025-08-21-enhanced-bsee-testing/sub-specs/tests.md
