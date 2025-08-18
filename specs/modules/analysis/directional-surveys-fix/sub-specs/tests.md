# Tests Specification

This is the tests coverage details for the spec detailed in @specs/modules/analysis/directional-surveys-fix/spec.md

> Created: 2025-07-28
> Version: 1.0.0

## Test Coverage

### Integration Tests

**Existing Test File**
- `tests/modules/bsee/analysis/query_api_01_wells_directional_survey_test.py` - Must pass without errors after fixes
- Test uses YAML config with API12 well 608124000400 for St. Malo field analysis
- Validates complete end-to-end directional surveys processing workflow

### Unit Tests

**WellAPI12.prepare_well_paths**
- Test method handles directional surveys DataFrame correctly
- Test proper initialization of output data structures
- Test API12 extraction and iteration logic
- Test error handling for missing or invalid survey data

**WellAPI12.process_survey_xyz**
- Test survey coordinate calculations produce expected XYZ results
- Test handling of duplicate survey points (by MD)
- Test mathematical calculations for dogleg severity and minimum curvature
- Test DataFrame structure and column creation

**WellAPI12.add_relative_WH_positions**
- Test wellhead position adjustment calculations
- Test proper DataFrame filtering by API12
- Test coordinate system transformation to relative positions

**WellAPI12.plot_field_wells**
- Test matplotlib figure creation and 3D plotting
- Test proper data access from well path dictionary
- Test legend and axis labeling functionality
- Test file saving functionality

### Data Structure Tests

**Data Flow Validation**
- Test that well_data parameter structure matches expected format
- Test that output_data_api12_df is properly initialized before method calls
- Test that survey XYZ data is correctly stored in output structures
- Test JSON serialization of well path data for database storage

### Error Handling Tests

**Attribute Reference Tests**
- Test all attribute references resolve correctly (no AttributeError)
- Test proper DataFrame column access
- Test handling of missing or empty data scenarios

**Mathematical Edge Cases**
- Test handling of zero or very small dogleg angles
- Test azimuth wraparound calculations (0-360 degrees)
- Test inclination angle boundary conditions

## Mocking Requirements

**File System Dependencies**
- Mock result folder creation and file saving operations in plot_field_wells
- Mock PNG file writing for well path visualization

**Configuration Dependencies**  
- Mock cfg parameter structure for field nickname and analysis settings
- Mock result folder paths for output file generation

**Data Dependencies**
- Mock directional surveys DataFrame with realistic BSEE survey data structure
- Mock well_data parameter with proper API12 DataFrame structure
- Mock GIS coordinate reference data (field_x_ref, field_y_ref values)