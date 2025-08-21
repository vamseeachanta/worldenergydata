# Prompt Summary

> Module: bsee/analysis
> Feature: Roy Scripts Implementation
> Created: 2025-08-21
> Type: Enhanced

## Original User Request

The user requested implementation of three critical Roy BSEE analysis scripts with the following requirements:

### Core Requirements
1. **Enhanced Drilling & Completion Days Analysis**
   - Convert `extract_drilling_and_completion_days.py` to class format
   - Implement binary WAR file support using pickle
   - Create enhanced configuration with proper routing
   - Verify results against reference outputs

2. **Multi-Year Lease Matrix Generation**
   - Transform `build_month_matrix_by_lease.py` to class structure
   - Process OGORA zip files from historical production directory
   - Generate production matrices with enhanced naming

3. **Development Financials Analysis**
   - Refactor `Build_Development_Financials_V20.py` to modular class
   - Integrate with production and drilling data
   - Calculate NPV, MIRR, and comprehensive financial metrics

### Technical Constraints
- All scripts must use '_enhanced' suffix
- Must integrate with existing `custom_router.py`
- Binary files from `data/modules/bsee/bin/war/`
- OGORA files from `data/modules/bsee/zip/historical_production_yearly/`
- Reference outputs in `docs/modules/bsee/data/SME_Roy_attachments/2025-08-20/`

### Validation Requirements
- Row count must match reference outputs
- First 5 rows of data must be validated
- All financial calculations must match reference NPV/MIRR
- Complete end-to-end workflow verification

## Key Decisions Made

1. **Architecture Pattern**: Full framework integration with class-based design
2. **Module Organization**: Enhanced modular structure under bsee/analysis module
3. **Data Processing**: Binary file support for improved performance
4. **Testing Strategy**: Comprehensive unit, integration, and end-to-end tests
5. **Configuration Management**: YAML-based routing with enhanced flags

## Implementation Approach

The implementation follows the enhanced Agent OS pattern with:
- Modular class architecture for each script
- Centralized routing through custom_router
- Comprehensive test coverage with automated verification
- Performance optimization through binary file processing
- Maintainable code structure with proper error handling