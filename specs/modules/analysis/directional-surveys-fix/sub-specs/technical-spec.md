# Technical Specification

This is the technical specification for the spec detailed in @specs/modules/analysis/directional-surveys-fix/spec.md

> Created: 2025-07-28
> Version: 1.0.0

## Technical Requirements

### Data Structure Consistency Issues
- Fix attribute references in `prepare_well_paths` method: `self.output_data_well_df` should be `self.output_data_api12_df`
- Correct initialization of instance variables to match legacy implementation pattern
- Ensure proper data structure setup before processing directional surveys data

### Method Parameter Flow Issues
- Fix parameter passing between `prepare_well_paths` → `process_survey_xyz` → `add_relative_WH_positions`
- Correct the well data dictionary structure passed to `prepare_well_paths` method
- Ensure API12 survey data is properly extracted from the directional surveys DataFrame

### Mathematical Processing Requirements
- Maintain existing survey XYZ coordinate calculation algorithms (these are correct)
- Preserve the minimum curvature method implementation for well path calculations
- Keep existing azimuth and inclination angle conversion logic

### Visualization Integration Requirements
- Fix attribute references in `plot_field_wells` for accessing well path data
- Ensure proper data structure access for matplotlib 3D plotting
- Maintain existing plot formatting and legend functionality

## Approach Options

**Option A:** Complete rewrite using modern pandas patterns
- Pros: Clean, modern code structure, better performance
- Cons: High risk of breaking existing functionality, extensive testing required

**Option B:** Minimal fixes following legacy patterns (Selected)
- Pros: Low risk, maintains proven functionality, quick implementation
- Cons: Preserves some older coding patterns, less modern structure

**Rationale:** The legacy ONGFDComponents implementation works correctly and has been proven in production. The current WellAPI12 implementation has the right algorithms but wrong data structure references. A minimal fix approach reduces risk while ensuring functionality.

## Implementation Details

### Data Flow Pattern (from legacy analysis)
1. `prepare_well_paths` receives directional_surveys DataFrame and well_data dictionary
2. Method extracts unique API12 values from surveys and processes each well individually
3. For each API12: extract survey data → calculate az/inc → call `process_survey_xyz` → call `add_relative_WH_positions`
4. Results stored in `self.output_data_well_path` dictionary and XYZ data added to well DataFrame

### Key Fixes Required
1. **Line 398**: Change `well_data.copy()` to `well_data['merged_api12_df'].copy()` or similar based on actual data structure
2. **Line 451**: Fix `self.output_data_well_df` reference - should be `self.output_data_api12_df`
3. **Line 609**: Correct API12 DataFrame filtering to use proper attribute
4. **Line 625, 635**: Fix attribute references in `plot_field_wells` method

### Data Structure Dependencies
- Requires proper initialization of `self.output_data_api12_df` before calling `prepare_well_paths`
- Needs `well_data` parameter to contain the merged API12 DataFrame with well information
- Depends on proper GIS coordinate conversion (SURF_x_rel, SURF_y_rel) being completed first

## External Dependencies

No new external dependencies required. All necessary libraries are already imported:
- pandas for DataFrame operations
- numpy for mathematical calculations  
- matplotlib for 3D plotting functionality
- json for data serialization