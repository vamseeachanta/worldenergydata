# Spec Requirements Document

> Spec: Directional Surveys Processing Fix
> Created: 2025-07-28
> Status: Planning

## Original User Prompt

"to finish directional surveys task, that implement methods prepare_well_paths, process_survey_xyz, add_relative_WH_positions, plot_field_wells in 'src\worldenergydata\modules\bsee\analysis\well_api12.py' refer test:'tests\modules\bsee\analysis\query_api_01_wells_directional_survey_test.py' and legacy documents 'src\worldenergydata\common\legacy\ong_fd_components.py' , 'consolidation_backup\docs\modules\bsee\_legacy\code\ong_field_development\cfg\bsee_data_manager.py' , 'docs\modules\bsee\_legacy\code\ong_field_development\sql\bsee.directional_surveys_data_by_api10.sql' . Imp Note: there are errors in methods prepare_well_paths, process_survey_xyz, add_relative_WH_positions, plot_field_wells , refer legacy document 'ong_fd_components.py' and study hard how the data (parameters) is being passed from method to method."

## Overview

Fix critical errors in the directional surveys processing methods (prepare_well_paths, process_survey_xyz, add_relative_WH_positions, plot_field_wells) in the WellAPI12 class to ensure proper data flow and parameter passing between methods, following the proven patterns from the legacy ONGFDComponents implementation.

## User Stories

### Fix Directional Surveys Data Processing

As a data analyst, I want the directional surveys processing to work correctly, so that I can generate accurate well path visualizations and XYZ coordinates for analysis.

The current implementation has critical errors in data parameter passing between methods. The prepare_well_paths method calls process_survey_xyz and add_relative_WH_positions, but the data structures and attribute references are inconsistent with how they're used in other parts of the class, causing runtime failures.

### Ensure Consistent Data Flow Pattern

As a developer, I want the directional surveys methods to follow the same data flow patterns as the working legacy implementation, so that the well path data is correctly processed and stored for downstream analysis.

The legacy ONGFDComponents.prepare_well_paths method demonstrates the correct approach where well data attributes are properly initialized and survey XYZ coordinates are correctly calculated and stored in output data structures.

## Spec Scope

1. **Fix prepare_well_paths method** - Correct data structure initialization and API12 data handling to match legacy patterns
2. **Fix process_survey_xyz method** - Ensure proper survey data processing with correct mathematical calculations for well path coordinates
3. **Fix add_relative_WH_positions method** - Correct wellhead position adjustment using proper data structure references
4. **Fix plot_field_wells method** - Resolve attribute reference errors and ensure proper data access for field visualization
5. **Integrate with existing test** - Ensure fixes work with the existing query_api_01_wells_directional_survey_test.py test

## Out of Scope

- Modifying the core mathematical algorithms for XYZ coordinate calculations (these are correct in the legacy code)
- Changing the test structure or YAML configuration file
- Adding new visualization features beyond fixing the existing plot functionality
- Modifying the underlying data loading mechanisms for directional surveys

## Expected Deliverable

1. **Working directional surveys processing** - All four methods execute without errors and produce correct well path data
2. **Consistent data structures** - All methods use consistent attribute references that match the class's data model
3. **Successful test execution** - The existing test query_api_01_wells_directional_survey_test.py runs successfully with the API12 well 608124000400

## Spec Documentation

- Tasks: @specs/modules/analysis/directional-surveys-fix/tasks.md
- Technical Specification: @specs/modules/analysis/directional-surveys-fix/sub-specs/technical-spec.md
- Tests Specification: @specs/modules/analysis/directional-surveys-fix/sub-specs/tests.md